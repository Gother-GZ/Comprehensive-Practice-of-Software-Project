from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.common.response import success_response
from app.db.session import get_db
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return success_response(data=UserOut.model_validate(current_user).model_dump())


@router.get("")
def list_users(
    page: int = 1,
    page_size: int = 20,
    role: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = UserService(db).list_users(page=page, page_size=page_size, role=role, status=status, keyword=keyword)
    data["items"] = [UserOut.model_validate(item).model_dump() for item in data["items"]]
    return success_response(data=data)


@router.post("")
def create_user(payload: UserCreate, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    user = UserService(db).create_user(payload)
    return success_response(data=UserOut.model_validate(user).model_dump())


@router.patch("/{user_id}")
def update_user(user_id: str, payload: UserUpdate, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    user = UserService(db).update_user(user_id, payload)
    return success_response(data=UserOut.model_validate(user).model_dump())
