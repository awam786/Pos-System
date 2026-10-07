from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    UserSummary,
)
from app.services.auth import authenticate_user, issue_token, mark_user_login


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=LoginResponse,
)
async def login(
    payload: LoginRequest,
    db: DbSession,
) -> LoginResponse:
    user = await authenticate_user(
        db=db,
        username=payload.username,
        password=payload.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await mark_user_login(
        db=db,
        user=user,
    )

    await db.commit()

    token = issue_token(user)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserSummary.model_validate(user),
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
async def current_user(
    user: CurrentUser,
) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(user)


@router.post(
    "/logout",
    response_model=LogoutResponse,
)
async def logout(
    user: CurrentUser,
) -> LogoutResponse:
    # JWT access tokens are stateless. The frontend removes the token.
    # Server-side token revocation can be added later if required.
    return LogoutResponse()
