from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.dependencies import CurrentUser, DbSession
from app.models import Brand, Category
from app.permissions import Permission
from app.schemas.catalog import (
    BrandCreate,
    BrandResponse,
    BrandUpdate,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from app.services.permissions import require_permission


router = APIRouter(
    prefix="/catalog",
    tags=["Catalog"],
)


def parse_uuid(value: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {field_name}.",
        )


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
)
async def list_categories(
    db: DbSession,
    current_user: CurrentUser,
    include_inactive: bool = False,
):
    query = select(Category).where(
        Category.shop_id == current_user.shop_id,
    )

    if not include_inactive:
        query = query.where(Category.active.is_(True))

    query = query.order_by(Category.name.asc())

    result = await db.execute(query)
    categories = result.scalars().all()

    return [
        CategoryResponse(
            id=str(category.id),
            name=category.name,
            parent_id=(
                str(category.parent_id)
                if category.parent_id
                else None
            ),
            active=category.active,
        )
        for category in categories
    ]


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    payload: CategoryCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.MANAGE_PRODUCTS)

    name = payload.name.strip()

    duplicate = await db.execute(
        select(Category).where(
            Category.shop_id == current_user.shop_id,
            Category.name == name,
        )
    )

    if duplicate.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists.",
        )

    parent_id = None

    if payload.parent_id:
        parent_id = parse_uuid(payload.parent_id, "parent_id")

        parent_result = await db.execute(
            select(Category).where(
                Category.id == parent_id,
                Category.shop_id == current_user.shop_id,
                Category.active.is_(True),
            )
        )

        if parent_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent category not found.",
            )

    category = Category(
        shop_id=current_user.shop_id,
        name=name,
        parent_id=parent_id,
        active=True,
    )

    db.add(category)
    await db.commit()
    await db.refresh(category)

    return CategoryResponse(
        id=str(category.id),
        name=category.name,
        parent_id=str(category.parent_id)
        if category.parent_id
        else None,
        active=category.active,
    )


@router.patch(
    "/categories/{category_id}",
    response_model=CategoryResponse,
)
async def update_category(
    category_id: str,
    payload: CategoryUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.MANAGE_PRODUCTS)

    category_uuid = parse_uuid(category_id, "category_id")

    result = await db.execute(
        select(Category).where(
            Category.id == category_uuid,
            Category.shop_id == current_user.shop_id,
        )
    )

    category = result.scalar_one_or_none()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    if payload.name is not None:
        name = payload.name.strip()

        duplicate = await db.execute(
            select(Category).where(
                Category.shop_id == current_user.shop_id,
                Category.name == name,
                Category.id != category.id,
            )
        )

        if duplicate.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A category with this name already exists.",
            )

        category.name = name

    if payload.parent_id is not None:
        if payload.parent_id == "":
            category.parent_id = None
        else:
            parent_id = parse_uuid(payload.parent_id, "parent_id")

            if parent_id == category.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A category cannot be its own parent.",
                )

            parent_result = await db.execute(
                select(Category).where(
                    Category.id == parent_id,
                    Category.shop_id == current_user.shop_id,
                    Category.active.is_(True),
                )
            )

            if parent_result.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent category not found.",
                )

            category.parent_id = parent_id

    if payload.active is not None:
        category.active = payload.active

    await db.commit()
    await db.refresh(category)

    return CategoryResponse(
        id=str(category.id),
        name=category.name,
        parent_id=str(category.parent_id)
        if category.parent_id
        else None,
        active=category.active,
    )


@router.get(
    "/brands",
    response_model=list[BrandResponse],
)
async def list_brands(
    db: DbSession,
    current_user: CurrentUser,
    include_inactive: bool = False,
):
    query = select(Brand).where(
        Brand.shop_id == current_user.shop_id,
    )

    if not include_inactive:
        query = query.where(Brand.active.is_(True))

    query = query.order_by(Brand.name.asc())

    result = await db.execute(query)
    brands = result.scalars().all()

    return [
        BrandResponse(
            id=str(brand.id),
            name=brand.name,
            active=brand.active,
        )
        for brand in brands
    ]


@router.post(
    "/brands",
    response_model=BrandResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_brand(
    payload: BrandCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.MANAGE_PRODUCTS)

    name = payload.name.strip()

    duplicate = await db.execute(
        select(Brand).where(
            Brand.shop_id == current_user.shop_id,
            Brand.name == name,
        )
    )

    if duplicate.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A brand with this name already exists.",
        )

    brand = Brand(
        shop_id=current_user.shop_id,
        name=name,
        active=True,
    )

    db.add(brand)
    await db.commit()
    await db.refresh(brand)

    return BrandResponse(
        id=str(brand.id),
        name=brand.name,
        active=brand.active,
    )


@router.patch(
    "/brands/{brand_id}",
    response_model=BrandResponse,
)
async def update_brand(
    brand_id: str,
    payload: BrandUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.MANAGE_PRODUCTS)

    brand_uuid = parse_uuid(brand_id, "brand_id")

    result = await db.execute(
        select(Brand).where(
            Brand.id == brand_uuid,
            Brand.shop_id == current_user.shop_id,
        )
    )

    brand = result.scalar_one_or_none()

    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found.",
        )

    if payload.name is not None:
        name = payload.name.strip()

        duplicate = await db.execute(
            select(Brand).where(
                Brand.shop_id == current_user.shop_id,
                Brand.name == name,
                Brand.id != brand.id,
            )
        )

        if duplicate.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A brand with this name already exists.",
            )

        brand.name = name

    if payload.active is not None:
        brand.active = payload.active

    await db.commit()
    await db.refresh(brand)

    return BrandResponse(
        id=str(brand.id),
        name=brand.name,
        active=brand.active,
    )
