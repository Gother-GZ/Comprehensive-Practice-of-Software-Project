from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums import UserRole, UserStatus
from app.core.config import get_settings
from app.core.security import hash_password, utc_now_iso
from app.db.migrations import run_migrations
from app.db.session import Base, engine
from app.models import user, vsp, event, integration  # noqa: F401
from app.models.user import User


def initialize_database() -> None:
    settings = get_settings()
    settings.sqlite_file_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    _ensure_default_admin()


def _ensure_default_admin() -> None:
    settings = get_settings()
    if not settings.default_admin_username or not settings.default_admin_password:
        return

    from app.db.session import SessionLocal

    with SessionLocal() as db:
        exists = db.scalar(select(User).where(User.username == settings.default_admin_username))
        if exists:
            return
        now = utc_now_iso()
        admin = User(
            user_id="bootstrap-admin",
            username=settings.default_admin_username,
            password_hash=hash_password(settings.default_admin_password),
            display_name=settings.default_admin_display_name,
            role=UserRole.ADMIN.value,
            status=UserStatus.ACTIVE.value,
            created_at=now,
            updated_at=now,
            last_login_at=None,
        )
        db.add(admin)
        db.commit()
