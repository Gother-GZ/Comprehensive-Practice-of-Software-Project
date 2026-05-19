from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.common.response import success_response
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    data = service.login(
        username=payload.username,
        password=payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return success_response(data=data)


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    return success_response(data=AuthService(db).refresh(payload.refresh_token))


@router.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    return success_response(data=AuthService(db).logout(payload.refresh_token))

