from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=80,
    )

    full_name: str = Field(
        min_length=1,
        max_length=150,
    )

    email: EmailStr | None = None

    password: str = Field(
        min_length=6,
        max_length=200,
    )

    role: str = Field(
        default="cashier",
        min_length=1,
        max_length=30,
    )


class UserUpdate(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )

    email: EmailStr | None = None

    role: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )

    active: bool | None = None


class PasswordChange(BaseModel):
    current_password: str = Field(
        min_length=1,
        max_length=200,
    )

    new_password: str = Field(
        min_length=6,
        max_length=200,
    )

    @model_validator(mode="after")
    def passwords_must_differ(self) -> "PasswordChange":
        if self.current_password == self.new_password:
            raise ValueError(
                "New password must be different from the current password."
            )

        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shop_id: uuid.UUID
    username: str
    full_name: str
    email: str | None
    role: str
    status: str
    is_super_admin: bool


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
