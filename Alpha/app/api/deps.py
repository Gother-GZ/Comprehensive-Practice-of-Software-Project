from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.common.enums import UserRole
from app.common.exceptions import forbidden, unauthorized
from app.db.session import get_db
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


def extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise unauthorized("missing bearer token", code=40001)
    return authorization.split(" ", 1)[1]


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    authorization = f"{credentials.scheme} {credentials.credentials}" if credentials else None
    token = extract_bearer(authorization)
    return AuthService(db).get_current_user(token)


def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN.value:
        raise forbidden("admin only")
    return current_user
