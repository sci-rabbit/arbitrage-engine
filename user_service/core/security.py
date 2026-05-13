from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
from jose import JWTError, jwt

from core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


#//JWT
def create_token(
    subject: str | int,
    token_type: Literal["access", "refresh", "verify", "reset"],
    extra_claims: dict | None = None,
) -> str:
    if token_type == "access":
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt.access_token_expire_minutes
        )
    elif token_type == "refresh":
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.jwt.refresh_token_expire_days
        )
    elif token_type == "verify":
        expire = datetime.now(timezone.utc) + timedelta(
            hours=settings.jwt.verify_token_expire_hours
        )
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            hours=settings.jwt.reset_token_expire_hours
        )

    payload = {"sub": str(subject), "type": token_type, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt.secret_key, algorithm=settings.jwt.algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt.secret_key, algorithms=[settings.jwt.algorithm])