# app/auth.py
from fastapi import Request, HTTPException
from itsdangerous import URLSafeSerializer
from starlette.middleware.sessions import SessionMiddleware
import bcrypt

SECRET_KEY = "super-secret-key"  # Change this in production
serializer = URLSafeSerializer(SECRET_KEY)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_session(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})

def read_session(session_token: str):
    try:
        data = serializer.loads(session_token)
        return data.get("user_id")
    except Exception:
        return None
