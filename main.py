import csv
import hashlib
import io
import json
import math
import os
import pickle
import unicodedata
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user
from database import Base, engine, ensure_schema_compatibility, get_db
from models import BankConnection, BankCustomer, BankImportedTransaction, Transaction, User
import salt_edge


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
MODEL_PATH = BASE_DIR / "model.pkl"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_TRANSACTIONS_PER_UPLOAD = 5_000

Base.metadata.create_all(bind=engine)
ensure_schema_compatibility()
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
    def normalize_header(header):
        header = (header or "").strip().lower().replace("_", " ")
        header = header.replace("ł", "l")
        return "".join(char for char in unicodedata.normalize("NFKD", header) if not unicodedata.combining(char))

    description_columns = (
        "description", "merchant", "merchant name", "name", "details", "transaction details",
        "transaction", "memo", "narrative", "narration", "payee", "particulars",
        "szczegoly transakcji", "nazwa nadawcy", "nazwa odbiorcy",
    )
    amount_columns = ("amount", "transaction amount", "value", "sum", "kwota operacji", "kwota w walucie rachunku")
    date_columns = ("date", "transaction date", "posting date", "booking date", "time", "data transakcji", "data ksiegowania")
    currency_columns = ("currency", "currency code", "waluta operacji", "waluta rachunku")

    # Some bank exports put report criteria above the actual CSV header.
    parsed_rows = list(csv.reader(io.StringIO(decoded), dialect=dialect))
    header_row_index = next((index for index, row in enumerate(parsed_rows[:20])
                             if any(normalize_header(cell) in description_columns for cell in row)
                             and any(normalize_header(cell) in amount_columns for cell in row)), None)
    if header_row_index is None:
        raise HTTPException(status_code=400, detail="CSV must include a header row")
    csv_lines = decoded.splitlines(keepends=True)
    reader = csv.DictReader(io.StringIO("".join(csv_lines[header_row_index:])), dialect=dialect)
    normalized_headers = [normalize_header(header) for header in reader.fieldnames]
    reader.fieldnames = normalized_headers
    if not any(name in normalized_headers for name in description_columns):
        raise HTTPException(status_code=400, detail="CSV needs a description, merchant, transaction details, memo, or payee column")
    if not any(name in normalized_headers for name in amount_columns):
        raise HTTPException(status_code=400, detail="CSV needs an amount, transaction amount, value, or sum column")

    transactions = []
    try:
        for row_number, row in enumerate(reader, start=2):
            if row_number > MAX_TRANSACTIONS_PER_UPLOAD + 1:
                raise HTTPException(status_code=413, detail="CSV may contain at most 5,000 transactions")
            row = {normalize_header(key): (value.strip() if value else "") for key, value in row.items() if key}
            description = next((row[name] for name in description_columns if row.get(name)), "")
            amount_text = next((row[name] for name in amount_columns if row.get(name)), "")
            date = next((row[name] for name in date_columns if row.get(name)), "Unknown")
            currency = next((row[name].upper() for name in currency_columns if row.get(name)), None)
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
                currency=currency[:3] if currency else None,
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


def get_bank_customer(db: Session, user: User):
    return db.query(BankCustomer).filter(BankCustomer.user_id == user.id).first()


def require_bank_customer(db: Session, user: User):
    customer = get_bank_customer(db, user)
    if customer is None:
        raise HTTPException(status_code=400, detail="No bank connection has been started for this account")
    return customer


def sync_bank_connection(db: Session, user: User, provider_connection: dict):
    provider_connection_id = str(provider_connection.get("id", ""))
    if not provider_connection_id:
        raise HTTPException(status_code=502, detail="Salt Edge returned a connection without an ID")
    connection = db.query(BankConnection).filter(
        BankConnection.provider_connection_id == provider_connection_id,
        BankConnection.user_id == user.id,
    ).first()
    if connection is None:
        connection = BankConnection(
            user_id=user.id,
            provider_connection_id=provider_connection_id,
            provider_name=str(provider_connection.get("provider_name") or "Connected bank")[:200],
            status=str(provider_connection.get("status") or "active")[:40],
        )
        db.add(connection)
        db.flush()
    else:
        connection.provider_name = str(provider_connection.get("provider_name") or connection.provider_name)[:200]
        connection.status = str(provider_connection.get("status") or connection.status)[:40]

    imported = 0
    accounts = salt_edge.list_accounts(provider_connection_id)
    for account in accounts:
        account_id = account.get("id")
        if not account_id:
            continue
        currency = str(account.get("currency_code") or "")[:3].upper() or None
        for provider_transaction in salt_edge.list_transactions(provider_connection_id, account_id):
            description = str(provider_transaction.get("description") or provider_transaction.get("merchant") or "Bank transaction").strip()
            amount = provider_transaction.get("amount")
            try:
                amount = float(amount)
            except (TypeError, ValueError):
                continue
            made_on = str(provider_transaction.get("made_on") or provider_transaction.get("date") or "Unknown")
            external_id = provider_transaction.get("id")
            if external_id is None:
                fingerprint = json.dumps([account_id, made_on, description, amount], ensure_ascii=False, separators=(",", ":"))
                external_id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
            external_id = str(external_id)
            exists = db.query(BankImportedTransaction.id).filter_by(
                connection_id=connection.id,
                provider_transaction_id=external_id,
            ).first()
            if exists:
                continue
            category = str(model.predict([description])[0])
            transaction = Transaction(
                user_id=user.id,
                date=made_on[:100],
                description=description[:500],
                amount=amount,
                category=category[:100],
                currency=str(provider_transaction.get("currency_code") or currency or "")[:3].upper() or None,
            )
            db.add(transaction)
            db.flush()
            db.add(BankImportedTransaction(
                connection_id=connection.id,
                provider_transaction_id=external_id,
                transaction_id=transaction.id,
            ))
            imported += 1
    db.commit()
    return connection, imported


@app.get("/bank/connections")
def get_bank_connections(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    user = db.query(User).filter(User.email == current_user).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Account not found")
    connections = db.query(BankConnection).filter(BankConnection.user_id == user.id).order_by(BankConnection.id.desc()).all()
    return {
        "configured": salt_edge.configured(),
        "connections": [{"provider_name": item.provider_name, "status": item.status, "created_at": item.created_at} for item in connections],
    }


@app.post("/bank/connect")
def start_bank_connection(request: Request, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    user = db.query(User).filter(User.email == current_user).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Account not found")
    if not salt_edge.configured():
        raise HTTPException(status_code=503, detail="Bank linking is not configured yet. Add SALTEDGE_APP_ID and SALTEDGE_SECRET on the server.")
    customer = get_bank_customer(db, user)
    try:
        if customer is None:
            customer_id = salt_edge.create_lead(user.email)
            customer = BankCustomer(user_id=user.id, provider_customer_id=customer_id)
            db.add(customer)
            db.commit()
            db.refresh(customer)
        base_url = os.getenv("APP_BASE_URL", str(request.base_url).rstrip("/"))
        return_to = f"{base_url.rstrip('/')}/static/dashboard.html?bank_link_return=1"
        redirect_url = salt_edge.create_lead_session(customer.provider_customer_id, return_to)
    except salt_edge.SaltEdgeError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc))
    return {"redirect_url": redirect_url}


@app.post("/bank/complete")
def complete_bank_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    user = db.query(User).filter(User.email == current_user).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Account not found")
    customer = require_bank_customer(db, user)
    try:
        provider_connection = next((item for item in salt_edge.list_connections(customer.provider_customer_id)
                                    if str(item.get("id")) == connection_id), None)
        if provider_connection is None:
            pending = db.query(BankConnection).filter_by(
                user_id=user.id,
                provider_connection_id=connection_id,
            ).first()
            if pending is None:
                db.add(BankConnection(
                    user_id=user.id,
                    provider_connection_id=connection_id,
                    provider_name="Bank authorization",
                    status="pending",
                ))
                db.commit()
            return {"message": "Bank authorization succeeded. Initial account data is still loading; use Sync connected banks in a moment.", "imported": 0}
        connection, imported = sync_bank_connection(db, user, provider_connection)
    except salt_edge.SaltEdgeError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc))
    return {"message": f"Connected to {connection.provider_name}. Imported {imported} new transactions.", "imported": imported}


@app.post("/bank/sync")
def sync_bank_connections(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    user = db.query(User).filter(User.email == current_user).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Account not found")
    customer = require_bank_customer(db, user)
    try:
        provider_connections = salt_edge.list_connections(customer.provider_customer_id)
        imported = 0
        for provider_connection in provider_connections:
            _, count = sync_bank_connection(db, user, provider_connection)
            imported += count
    except salt_edge.SaltEdgeError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc))
    return {"message": f"Bank sync complete. Imported {imported} new transactions.", "imported": imported}
