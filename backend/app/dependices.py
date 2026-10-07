from __future__ import annotations

import uuid
from typing import Annotated, Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Role, User, UserStatus
from app.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: DbSession,
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        shop_id = payload.get("shop_id")

        if not subject or not shop_id:
            raise ValueError("Invalid token payload.")

        user_id = uuid.UUID(str(subject))
        parsed_shop_id = uuid.UUID(str(shop_id))

    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.shop_id == parsed_shop_id,
            User.status == UserStatus.ACTIVE,
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable:
    allowed_roles = set(roles)

    async def dependency(
        current_user: CurrentUser,
    ) -> User:
        if current_user.is_super_admin:
            return current_user

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return dependency


def require_owner(
    current_user: CurrentUser,
) -> User:
    if current_user.is_super_admin or current_user.role == Role.OWNER:
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Owner permission required.",
    )


def require_manager_or_owner(
    current_user: CurrentUser,
) -> User:
    if current_user.is_super_admin:
        return current_user

    if current_user.role in {
        Role.OWNER,
        Role.MANAGER,
    }:
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Manager or Owner permission required.",
    )


def require_any_authenticated_user(
    current_user: CurrentUser,
) -> User:
    return current_user
