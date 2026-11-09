from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.security import create_access_token, hash_password, verify_password
from ..db import get_db
from ..models import User
from ..schemas import AuthResponse, LoginRequest, RegisterRequest, UserOut
from .deps import current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="email already registered")
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, get_settings().app_secret_key)
    return AuthResponse(token=token, user=UserOut(id=user.id, email=user.email))


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid email or password")
    token = create_access_token(user.id, get_settings().app_secret_key)
    return AuthResponse(token=token, user=UserOut(id=user.id, email=user.email))


@router.post("/logout")
def logout():
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return UserOut(id=user.id, email=user.email)
