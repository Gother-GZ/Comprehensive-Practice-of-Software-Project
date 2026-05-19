from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums import UserStatus
from app.common.exceptions import forbidden, unauthorized
from app.core.security import create_access_token, create_refresh_token, decode_access_token, hash_token, parse_refresh_token, utc_now_iso, verify_password, verify_token_hash
from app.models.user import User, UserLoginAudit, UserRefreshToken


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def _create_login_audit(self, user_id: str | None, username: str, login_result: str, ip_address: str | None, user_agent: str | None, failure_reason: str | None = None) -> None:
        audit = UserLoginAudit(
            audit_id=utc_now_iso().replace(":", "").replace("-", "").replace(".", ""),
            user_id=user_id,
            username=username,
            login_result=login_result,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=utc_now_iso(),
        )
        self.db.add(audit)
        self.db.commit()

    def login(self, username: str, password: str, ip_address: str | None, user_agent: str | None) -> dict:
        user = self.db.scalar(select(User).where(User.username == username))
        if not user or not verify_password(password, user.password_hash):
            self._create_login_audit(None, username, "failure", ip_address, user_agent, "invalid credentials")
            raise unauthorized("invalid credentials", code=40001)
        if user.status == UserStatus.DISABLED.value:
            self._create_login_audit(user.user_id, username, "failure", ip_address, user_agent, "user disabled")
            raise forbidden("user disabled", code=41001)
        access_token, expires_in = create_access_token(user.user_id, user.role)
        refresh_token, token_id, expires_at = create_refresh_token(user.user_id)
        token_row = UserRefreshToken(
            token_id=token_id,
            user_id=user.user_id,
            token_hash=hash_token(refresh_token),
            issued_at=utc_now_iso(),
            expires_at=expires_at,
            revoked_at=None,
            created_at=utc_now_iso(),
        )
        user.last_login_at = utc_now_iso()
        user.updated_at = utc_now_iso()
        self.db.add(token_row)
        self.db.commit()
        self._create_login_audit(user.user_id, username, "success", ip_address, user_agent)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role,
                "status": user.status,
                "last_login_at": user.last_login_at,
            },
        }

    def refresh(self, refresh_token: str) -> dict:
        token_id, _ = parse_refresh_token(refresh_token)
        token_row = self.db.get(UserRefreshToken, token_id)
        if not token_row or token_row.revoked_at:
            raise unauthorized("invalid refresh token", code=40001)
        if not verify_token_hash(refresh_token, token_row.token_hash):
            raise unauthorized("invalid refresh token", code=40001)
        expires_at = datetime.fromisoformat(token_row.expires_at.replace("Z", "+00:00"))
        if expires_at < datetime.now(timezone.utc):
            raise unauthorized("refresh token expired", code=40001)
        user = self.db.get(User, token_row.user_id)
        if not user or user.status == UserStatus.DISABLED.value:
            raise forbidden("user disabled", code=41001)
        token_row.revoked_at = utc_now_iso()
        access_token, expires_in = create_access_token(user.user_id, user.role)
        new_refresh_token, new_token_id, new_expires_at = create_refresh_token(user.user_id)
        new_row = UserRefreshToken(
            token_id=new_token_id,
            user_id=user.user_id,
            token_hash=hash_token(new_refresh_token),
            issued_at=utc_now_iso(),
            expires_at=new_expires_at,
            revoked_at=None,
            created_at=utc_now_iso(),
        )
        self.db.add(new_row)
        self.db.commit()
        return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer", "expires_in": expires_in}

    def logout(self, refresh_token: str) -> dict:
        token_id, _ = parse_refresh_token(refresh_token)
        token_row = self.db.get(UserRefreshToken, token_id)
        if not token_row or token_row.revoked_at or not verify_token_hash(refresh_token, token_row.token_hash):
            raise unauthorized("invalid refresh token", code=40001)
        token_row.revoked_at = utc_now_iso()
        self.db.commit()
        return {"revoked": True}

    def get_current_user(self, access_token: str) -> User:
        payload = decode_access_token(access_token)
        user = self.db.get(User, payload.get("sub"))
        if not user:
            raise unauthorized("invalid access token", code=40001)
        if user.status == UserStatus.DISABLED.value:
            raise forbidden("user disabled", code=41001)
        return user

