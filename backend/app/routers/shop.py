from __future__ import annotations

import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select

from app.config import settings
from app.dependencies import CurrentUser, DbSession
from app.models import Shop
from app.permissions import Permission
from app.schemas.shop import ShopResponse, ShopUpdate
from app.services.permissions import require_permission


router = APIRouter(
    prefix="/shop",
    tags=["Shop"],
)


ALLOWED_LOGO_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
}


def serialize_shop(shop: Shop) -> ShopResponse:
    return ShopResponse(
        id=str(shop.id),
        name=shop.name,
        address=shop.address,
        phone=shop.phone,
        email=shop.email,
        currency=shop.currency,
        timezone=shop.timezone,
        receipt_width=shop.receipt_width,
        receipt_header=shop.receipt_header,
        receipt_footer=shop.receipt_footer,
        is_active=shop.is_active,
        has_logo=shop.logo_data is not None,
        logo_content_type=shop.logo_content_type,
    )


async def get_current_shop(
    db: DbSession,
    current_user: CurrentUser,
) -> Shop:
    result = await db.execute(
        select(Shop).where(
            Shop.id == current_user.shop_id,
            Shop.is_active.is_(True),
        )
    )

    shop = result.scalar_one_or_none()

    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found.",
        )

    return shop


@router.get(
    "",
    response_model=ShopResponse,
)
async def get_shop(
    db: DbSession,
    current_user: CurrentUser,
):
    shop = await get_current_shop(db, current_user)
    return serialize_shop(shop)


@router.patch(
    "",
    response_model=ShopResponse,
)
async def update_shop(
    payload: ShopUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.MANAGE_SHOP)

    shop = await get_current_shop(db, current_user)

    if payload.receipt_width is not None and payload.receipt_width not in (58, 80):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Receipt width must be either 58 or 80.",
        )

    values = payload.model_dump(exclude_unset=True)

    for field_name, value in values.items():
        if isinstance(value, str):
            value = value.strip()

        setattr(shop, field_name, value or None if field_name != "name" else value)

    if not shop.name or not shop.name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Shop name cannot be empty.",
        )

    if shop.currency:
        shop.currency = shop.currency.strip().upper()

    await db.commit()
    await db.refresh(shop)

    return serialize_shop(shop)


@router.post(
    "/logo",
    response_model=ShopResponse,
)
async def upload_shop_logo(
    db: DbSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    require_permission(current_user, Permission.MANAGE_SHOP)

    shop = await get_current_shop(db, current_user)

    if file.content_type not in ALLOWED_LOGO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logo must be PNG, JPEG, or WEBP.",
        )

    maximum_bytes = settings.max_upload_size_mb * 1024 * 1024
    data = await file.read()

    if len(data) > maximum_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Logo exceeds the {settings.max_upload_size_mb} MB "
                "upload limit."
            ),
        )

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded logo is empty.",
        )

    try:
        image = Image.open(io.BytesIO(data))
        image.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid image.",
        )

    shop.logo_data = data
    shop.logo_content_type = file.content_type

    await db.commit()
    await db.refresh(shop)

    return serialize_shop(shop)


@router.get(
    "/logo",
    include_in_schema=False,
)
async def get_shop_logo(
    db: DbSession,
    current_user: CurrentUser,
):
    shop = await get_current_shop(db, current_user)

    if not shop.logo_data or not shop.logo_content_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop logo has not been uploaded.",
        )

    return Response(
        content=shop.logo_data,
        media_type=shop.logo_content_type,
        headers={
            "Cache-Control": "no-cache",
        },
    )


@router.delete(
    "/logo",
    response_model=ShopResponse,
)
async def remove_shop_logo(
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.MANAGE_SHOP)

    shop = await get_current_shop(db, current_user)

    shop.logo_data = None
    shop.logo_content_type = None

    await db.commit()
    await db.refresh(shop)

    return serialize_shop(shop)
