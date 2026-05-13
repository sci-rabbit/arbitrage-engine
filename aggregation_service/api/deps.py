from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def require_access(token: str = Depends(oauth2_scheme)) -> None:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt.secret_key, algorithms=[settings.jwt.algorithm])
        if payload.get("type") != "access":
            raise credentials_exception
        if not payload.get("has_access"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access required")
    except JWTError:
        raise credentials_exception
