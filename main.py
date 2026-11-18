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

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV must include a header row")
    normalized_headers = [header.strip().lower() if header else "" for header in reader.fieldnames]
    reader.fieldnames = normalized_headers
    if not any(name in normalized_headers for name in ("description", "merchant", "name", "details")):
        raise HTTPException(status_code=400, detail="CSV needs a description, merchant, name, or details column")
    if not any(name in normalized_headers for name in ("amount", "value", "sum")):
        raise HTTPException(status_code=400, detail="CSV needs an amount, value, or sum column")

    transactions = []
    try:
        for row_number, row in enumerate(reader, start=2):
            if row_number > MAX_TRANSACTIONS_PER_UPLOAD + 1:
                raise HTTPException(status_code=413, detail="CSV may contain at most 5,000 transactions")
            row = {key.strip().lower(): (value.strip() if value else "") for key, value in row.items() if key}
            description = row.get("description") or row.get("merchant") or row.get("name") or row.get("details")
            amount_text = row.get("amount") or row.get("value") or row.get("sum")
            date = row.get("date") or row.get("transaction date") or row.get("time") or "Unknown"
            if not description or not amount_text:
                raise HTTPException(status_code=400, detail=f"Row {row_number}: description and amount are required")
            try:
                amount = float(amount_text.replace("$", "").replace("€", "").replace("£", "").replace(",", ""))
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
