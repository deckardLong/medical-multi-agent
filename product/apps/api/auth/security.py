from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt
from product.config import ProductEnv

env = ProductEnv()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)

def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=env.jwt_expire_minutes)
    payload = {
        "sub": user_id,
        "exp": expire
    }
    return jwt.encode(payload, env.jwt_secret, algorithm="HS256")

def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, env.jwt_secret, algorithms=["HS256"])
    return payload["sub"]