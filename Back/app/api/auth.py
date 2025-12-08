from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets

# ===== КОНФИГ =====
SECRET_KEY = secrets.token_urlsafe(32)  # или "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# ===== МОДЕЛИ =====
class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    email: str
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# ===== БАЗА В ПАМЯТИ =====
fake_db = {
    "test@test.com": {
        "email": "test@test.com",
        "username": "testuser",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # password = "password"
    }
}

# ===== ИНИЦИАЛИЗАЦИЯ =====
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(tags=["auth"])

# ===== УТИЛИТЫ =====
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def hash_password(password):
    return pwd_context.hash(password)

def create_token(data: dict):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

# ===== ЭНДПОИНТЫ =====
@router.post("/auth/register")
def register(user: UserRegister):
    if user.email in fake_db:
        raise HTTPException(400, "Email already exists")
    
    fake_db[user.email] = {
        "email": user.email,
        "username": user.username,
        "hashed_password": hash_password(user.password)
    }
    
    token = create_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/auth/login")
def login(user: UserLogin):
    db_user = fake_db.get(user.email)
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(401, "Wrong email or password")
    
    token = create_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/auth/me")
def get_me(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email not in fake_db:
            raise HTTPException(401, "Invalid token")
        return fake_db[email]
    except JWTError:
        raise HTTPException(401, "Invalid token")