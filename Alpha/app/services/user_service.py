from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from uuid import uuid4

from app.common.exceptions import conflict, not_found
from app.core.security import hash_password, utc_now_iso
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def list_users(self, page: int, page_size: int, role: str | None, status: str | None, keyword: str | None):
        stmt = select(User)
        if role:
            stmt = stmt.where(User.role == role)
        if status:
            stmt = stmt.where(User.status == status)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(or_(User.username.like(like), User.display_name.like(like)))
        total = len(self.db.scalars(stmt).all())
        items = self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def create_user(self, payload: UserCreate) -> User:
        if self.db.scalar(select(User).where(User.username == payload.username)):
            raise conflict("username already exists")
        now = utc_now_iso()
        user = User(
            user_id=uuid4().hex,
            username=payload.username,
            password_hash=hash_password(payload.password),
            display_name=payload.display_name,
            role=payload.role.value,
            status=payload.status.value,
            created_at=now,
            updated_at=now,
            last_login_at=None,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user_id: str, payload: UserUpdate) -> User:
        user = self.db.get(User, user_id)
        if not user:
            raise not_found("user not found")
        if payload.display_name is not None:
            user.display_name = payload.display_name
        if payload.role is not None:
            user.role = payload.role.value
        if payload.status is not None:
            user.status = payload.status.value
        if payload.password:
            user.password_hash = hash_password(payload.password)
        user.updated_at = utc_now_iso()
        self.db.commit()
        self.db.refresh(user)
        return user

