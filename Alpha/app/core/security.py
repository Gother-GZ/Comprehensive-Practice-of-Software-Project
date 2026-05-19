import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if _is_bcrypt_hash(password_hash):
        return _verify_bcrypt_hash(password, password_hash)
    return pwd_context.verify(password, password_hash)


def hash_token(token: str) -> str:
    return pwd_context.hash(token)


def verify_token_hash(token: str, token_hash: str) -> bool:
    if _is_bcrypt_hash(token_hash):
        return _verify_bcrypt_hash(token, token_hash)
    return pwd_context.verify(token, token_hash)


def create_access_token(subject: str, role: str) -> tuple[str, int]:
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.jwt_access_expire_minutes)
    expires_at = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
    return token, settings.jwt_access_expire_minutes * 60


def create_refresh_token(subject: str) -> tuple[str, str, str]:
    token_id = uuid4().hex
    secret = secrets.token_urlsafe(32)
    raw_token = f"{token_id}.{secret}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=get_settings().jwt_refresh_expire_days)
    return raw_token, token_id, expires_at.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_refresh_token(raw_token: str) -> tuple[str, str]:
    parts = raw_token.split(".", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("invalid refresh token")
    return parts[0], parts[1]


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("invalid access token") from exc
    if payload.get("type") != "access":
        raise ValueError("invalid access token type")
    return payload


def make_trace_id() -> str:
    return sha256(uuid4().hex.encode("utf-8")).hexdigest()[:24]


def _is_bcrypt_hash(value: str) -> bool:
    return value.startswith("$2a$") or value.startswith("$2b$") or value.startswith("$2y$")


def _verify_bcrypt_hash(raw_value: str, hashed_value: str) -> bool:
    try:
        return bcrypt.checkpw(raw_value.encode("utf-8"), hashed_value.encode("utf-8"))
    except ValueError:
        return False
