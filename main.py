import csv
import io
import math
import pickle
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user
from database import Base, engine, get_db
from models import Transaction, User


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
MODEL_PATH = BASE_DIR / "model.pkl"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_TRANSACTIONS_PER_UPLOAD = 5_000

Base.metadata.create_all(bind=engine)
app = FastAPI(title="ExpenseIQ", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

with MODEL_PATH.open("rb") as model_file:
    model = pickle.load(model_file)


@app.get("/")
def homepage():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/register")
def register(email: str, password: str, db: Session = Depends(get_db)):
    email = email.strip().lower()
    if not email or len(email) > 320:
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="User already exists")
    new_user = User(email=email, hashed_password=pwd_context.hash(password))
    db.add(new_user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not create account")
    db.refresh(new_user)
    return {"id": new_user.id, "email": new_user.email}


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form_data.username.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_access_token(data={"sub": user.email}), "token_type": "bearer"}


@app.get("/me")
def get_me(current_user: str = Depends(get_current_user)):
    return {"logged_in_as": current_user}


@app.post("/upload")
async def upload_transactions(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    user = db.query(User).filter(User.email == current_user).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Account not found")
    if file.filename and Path(file.filename).suffix.lower() != ".csv":
        raise HTTPException(status_code=415, detail="Upload a CSV file")

    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CSV must be 5 MB or smaller")
    try:
        decoded = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must use UTF-8 encoding")
    if not decoded.strip():
        raise HTTPException(status_code=400, detail="CSV file is empty")

    try:
        dialect = csv.Sniffer().sniff(decoded[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(decoded), dialect=dialect)
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV must include a header row")
    normalized_headers = [header.strip().lower().replace("_", " ") if header else "" for header in reader.fieldnames]
    reader.fieldnames = normalized_headers
    description_columns = ("description", "merchant", "merchant name", "name", "details", "transaction details", "transaction", "memo", "narrative", "narration", "payee", "particulars")
    amount_columns = ("amount", "transaction amount", "value", "sum")
    date_columns = ("date", "transaction date", "posting date", "booking date", "time")
    if not any(name in normalized_headers for name in description_columns):
        raise HTTPException(status_code=400, detail="CSV needs a description, merchant, transaction, memo, or payee column")
    if not any(name in normalized_headers for name in amount_columns):
        raise HTTPException(status_code=400, detail="CSV needs an amount, transaction amount, value, or sum column")

    transactions = []
    try:
        for row_number, row in enumerate(reader, start=2):
            if row_number > MAX_TRANSACTIONS_PER_UPLOAD + 1:
                raise HTTPException(status_code=413, detail="CSV may contain at most 5,000 transactions")
            row = {key.strip().lower().replace("_", " "): (value.strip() if value else "") for key, value in row.items() if key}
            description = next((row[name] for name in description_columns if row.get(name)), "")
            amount_text = next((row[name] for name in amount_columns if row.get(name)), "")
            date = next((row[name] for name in date_columns if row.get(name)), "Unknown")
            if not description or not amount_text:
                raise HTTPException(status_code=400, detail=f"Row {row_number}: description and amount are required")
            amount_clean = amount_text.replace("$", "").replace("€", "").replace("£", "").replace("\u00a0", "").replace(" ", "")
            negative = amount_clean.startswith("(") and amount_clean.endswith(")")
            amount_clean = amount_clean.strip("()")
            if "," in amount_clean and "." in amount_clean:
                decimal_separator = "," if amount_clean.rfind(",") > amount_clean.rfind(".") else "."
                grouping_separator = "." if decimal_separator == "," else ","
                amount_clean = amount_clean.replace(grouping_separator, "").replace(decimal_separator, ".")
            elif "," in amount_clean and dialect.delimiter in (";", "\t", "|"):
                amount_clean = amount_clean.replace(",", ".")
            else:
                amount_clean = amount_clean.replace(",", "")
            try:
                amount = float(amount_clean)
                if negative:
                    amount = -amount
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Row {row_number}: amount must be numeric")
            if not math.isfinite(amount):
                raise HTTPException(status_code=400, detail=f"Row {row_number}: amount must be finite")
            category = model.predict([description])[0]
            transactions.append(Transaction(
                user_id=user.id,
                date=date[:100],
                description=description[:500],
                amount=amount,
                category=str(category)[:100],
            ))
    except csv.Error:
        raise HTTPException(status_code=400, detail="CSV format is invalid")

    if not transactions:
        raise HTTPException(status_code=400, detail="CSV has no transaction rows")
    db.add_all(transactions)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not save transactions")
    return {"message": f"{len(transactions)} transactions uploaded successfully"}


@app.get("/transactions")
def get_transactions(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    user = db.query(User).filter(User.email == current_user).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Account not found")
    return db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.id.desc()).all()
