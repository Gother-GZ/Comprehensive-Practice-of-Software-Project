from pydantic import BaseModel, ConfigDict

from app.common.enums import UserRole, UserStatus


class UserBase(BaseModel):
    username: str
    display_name: str
    role: UserRole
    status: UserStatus


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: UserRole | None = None
    status: UserStatus | None = None
    password: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    display_name: str
    role: str
    status: str
    created_at: str
    updated_at: str
    last_login_at: str | None = None

