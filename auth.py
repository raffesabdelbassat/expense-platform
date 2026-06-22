from datetime import timedelta, datetime
from jose import jwt

secret_key = "Basset31142716302025"
ALGORITHM = "HS256"
access_token_expire_minutes = 60

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=access_token_expire_minutes)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt