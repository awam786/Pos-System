from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserStatus
from app.security import create_access_token, verify_password


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> User | None:
    result = await db.execute(
        select(User).where(
            User.username == username.strip(),
            User.status == UserStatus.ACTIVE,
        )
    )

    users = result.scalars().all()

    for user in users:
        if verify_password(password, user.password_hash):
            return user

    return None


def issue_token(user: User) -> str:
    return create_access_token(
        subject=str(user.id),
        shop_id=str(user.shop_id),
        role=user.role.value,
    )


async def mark_user_login(
    db: AsyncSession,
    user: User,
) -> None:
    # The model intentionally uses the common timestamp field as the
    # account activity timestamp until a dedicated login-history model
    # is introduced in the audit/session layer.
    user.updated_at = datetime.now(timezone.utc)

    await db.flush()


async def get_user_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> User | None:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    return result.scalar_one_or_none()
