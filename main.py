from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from auth import create_access_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import UploadFile, File
from models import User, Transaction
import csv
import io
from database import Base, engine, get_db

Base.metadata.create_all(bind=engine)
app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.post("/register")
def register(email: str, password: str, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_password = pwd_context.hash(password)

    new_user = User(email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"id": new_user.id, "email": new_user.email}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me")
def get_me(current_user: str = Depends(get_current_user)):
    return {"logged_in_as": current_user}

@app.post("/upload")
def upload_transactions(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    # find the logged in user in the database
    user = db.query(User).filter(User.email == current_user).first()

    # read the uploaded file
    contents = file.file.read()
    decoded = contents.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))

    transactions_added = 0
    for row in reader:
        transaction = Transaction(
            user_id=user.id,
            date=row["date"],
            description=row["description"],
            amount=float(row["amount"]),
            category="Uncategorized"
        )
        db.add(transaction)
        transactions_added += 1

    db.commit()
    return {"message": f"{transactions_added} transactions uploaded successfully"}
    
    @app.get("/transactions")
def get_transactions(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    user = db.query(User).filter(User.email == current_user).first()
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    return transactions 