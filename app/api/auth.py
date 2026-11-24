"""用户认证：手机号注册 / 登录（JWT）。

- 手机号（11位）+ 密码，无需短信服务商（毕设演示方案；
  后续如需真实短信验证码，仅需在注册/登录前加一步验证码校验）；
- 密码使用 PBKDF2-HMAC-SHA256 加盐哈希（标准库实现，无额外依赖）；
- 令牌为 JWT（HS256），前端存 localStorage 并带 Authorization: Bearer 头。
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import config
from .db import User, get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


# ---------------- 密码哈希（PBKDF2） ----------------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"pbkdf2${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, hexdigest = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return hmac.compare_digest(digest.hex(), hexdigest)


# ---------------- 令牌 ----------------

def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=config.TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm="HS256")


def _decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
        return int(payload["sub"])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录") from exc


# ---------------- 依赖 ----------------

def get_current_user(
    cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if cred is None:
        raise HTTPException(status_code=401, detail="请先登录")
    user = db.get(User, _decode_token(cred.credentials))
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def get_current_user_optional(
    cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if cred is None:
        return None
    try:
        return db.get(User, _decode_token(cred.credentials))
    except HTTPException:
        return None


# ---------------- 接口 ----------------

class AuthRequest(BaseModel):
    phone: str = Field(pattern=r"^1\d{10}$", description="11位手机号")
    password: str = Field(min_length=6, max_length=64)
    nickname: str = Field(default="", max_length=20)


def _user_dict(user: User) -> dict:
    return {"id": user.id, "phone": user.phone, "nickname": user.nickname}


@router.post("/register")
def register(req: AuthRequest, db: Session = Depends(get_db)) -> dict:
    if db.query(User).filter(User.phone == req.phone).first():
        raise HTTPException(status_code=400, detail="该手机号已注册")
    nickname = req.nickname.strip() or f"戏迷{req.phone[-4:]}"
    user = User(phone=req.phone, nickname=nickname, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    return {"token": create_token(user.id), "user": _user_dict(user)}


@router.post("/login")
def login(req: AuthRequest, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.phone == req.phone).first()
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="手机号或密码错误")
    return {"token": create_token(user.id), "user": _user_dict(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return _user_dict(user)
