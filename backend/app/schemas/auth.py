from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(
        min_length=1,
        max_length=80,
    )

    password: str = Field(
        min_length=1,
        max_length=200,
    )


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shop_id: uuid.UUID
    username: str
    full_name: str
    email: str | None
    role: str
    status: str
    is_super_admin: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary


class CurrentUserResponse(UserSummary):
    pass


class LogoutResponse(BaseModel):
    success: bool = True
    message: str = "Logged out successfully."
