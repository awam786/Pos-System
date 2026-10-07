from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.dependencies import CurrentUser, DbSession
from app.models import Role, User, UserStatus
from app.schemas.user import (
    PasswordChange,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.security import hash_password, verify_password


router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
)


def ensure_user_management_access(user: User) -> None:
    if user.is_super_admin:
        return

    if user.role != Role.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner permission required.",
        )


@router.get(
    "",
    response_model=UserListResponse,
)
async def list_users(
    current_user: CurrentUser,
    db: DbSession,
) -> UserListResponse:
    ensure_user_management_access(current_user)

    count_result = await db.execute(
        select(func.count(User.id)).where(
            User.shop_id == current_user.shop_id
        )
    )

    total = int(count_result.scalar_one())

    result = await db.execute(
        select(User)
        .where(User.shop_id == current_user.shop_id)
        .order_by(User.full_name.asc())
    )

    users = result.scalars().all()

    return UserListResponse(
        items=[
            UserResponse.model_validate(user)
            for user in users
        ],
        total=total,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    payload: UserCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    ensure_user_management_access(current_user)

    try:
        role = Role(payload.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Use owner, manager, or cashier.",
        )

    if role == Role.OWNER and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the system administrator can create another Owner.",
        )

    username = payload.username.strip().lower()

    existing = await db.execute(
        select(User).where(
            User.shop_id == current_user.shop_id,
            User.username == username,
        )
    )

    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username already exists.",
        )

    user = User(
        shop_id=current_user.shop_id,
        username=username,
        full_name=payload.full_name.strip(),
        email=str(payload.email) if payload.email else None,
        password_hash=hash_password(payload.password),
        role=role,
        status=UserStatus.ACTIVE,
        is_super_admin=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    ensure_user_management_access(current_user)

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.shop_id == current_user.shop_id,
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.id == current_user.id and payload.active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()

    if payload.email is not None:
        user.email = str(payload.email)

    if payload.role is not None:
        try:
            new_role = Role(payload.role.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role.",
            )

        if (
            new_role == Role.OWNER
            and not current_user.is_super_admin
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the system administrator can assign Owner role.",
            )

        user.role = new_role

    if payload.active is not None:
        user.status = (
            UserStatus.ACTIVE
            if payload.active
            else UserStatus.INACTIVE
        )

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/me/password",
)
async def change_my_password(
    payload: PasswordChange,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, str]:
    if not verify_password(
        payload.current_password,
        current_user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    current_user.password_hash = hash_password(
        payload.new_password
    )

    await db.commit()

    return {
        "message": "Password changed successfully."
    }


@router.post(
    "/{user_id}/reset-password",
)
async def reset_user_password(
    user_id: uuid.UUID,
    payload: dict[str, str],
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, str]:
    ensure_user_management_access(current_user)

    new_password = str(payload.get("new_password", ""))

    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must contain at least 6 characters.",
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.shop_id == current_user.shop_id,
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    user.password_hash = hash_password(new_password)

    await db.commit()

    return {
        "message": "Password reset successfully."
    }
