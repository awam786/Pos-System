from __future__ import annotations

import io
import uuid
from math import ceil

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, or_, select

from app.config import settings
from app.dependencies import CurrentUser, DbSession
from app.models import Product, ProductCode
from app.permissions import Permission
from app.schemas.product import (
    ProductCodeCreate,
    ProductCodeResponse,
    ProductCreate,
    ProductListResponse,
    ProductLookupResponse,
    ProductResponse,
    ProductUpdate,
)
from app.services.permissions import require_permission
from app.services.products import (
    add_product_code,
    archive_product,
    create_product,
    get_product_for_shop,
    parse_uuid,
    remove_product_code,
    update_product,
)


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


ALLOWED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
}


def serialize_code(code: ProductCode) -> ProductCodeResponse:
    return ProductCodeResponse(
        id=str(code.id),
        code=code.code,
        code_type=code.code_type,
        is_primary=code.is_primary,
        active=code.active,
    )


def serialize_product(product: Product) -> ProductResponse:
    active_codes = [
        serialize_code(code)
        for code in product.codes
        if code.active
    ]

    return ProductResponse(
        id=str(product.id),
        name=product.name,
        sku=product.sku,
        category_id=(
            str(product.category_id)
            if product.category_id
            else None
        ),
        brand_id=(
            str(product.brand_id)
            if product.brand_id
            else None
        ),
        supplier_id=(
            str(product.supplier_id)
            if product.supplier_id
            else None
        ),
        unit=product.unit,
        purchase_price=product.purchase_price,
        selling_price=product.selling_price,
        wholesale_price=product.wholesale_price,
        minimum_price=product.minimum_price,
        stock_quantity=product.stock_quantity,
        minimum_stock=product.minimum_stock,
        maximum_stock=product.maximum_stock,
        description=product.description,
        active=product.active,
        has_image=product.image_data is not None,
        image_content_type=product.image_content_type,
        codes=active_codes,
    )


async def load_product(
    db: DbSession,
    shop_id: uuid.UUID,
    product_id: str,
) -> Product:
    product_uuid = parse_uuid(product_id, "product_id")

    return await get_product_for_shop(
        db,
        shop_id,
        product_uuid,
    )


@router.get(
    "",
    response_model=ProductListResponse,
)
async def list_products(
    db: DbSession,
    current_user: CurrentUser,
    search: str | None = None,
    category_id: str | None = None,
    brand_id: str | None = None,
    active_only: bool = True,
    low_stock_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    query = select(Product).where(
        Product.shop_id == current_user.shop_id,
    )

    if active_only:
        query = query.where(Product.active.is_(True))

    if search:
        term = f"%{search.strip()}%"

        query = query.where(
            or_(
                Product.name.ilike(term),
                Product.sku.ilike(term),
                Product.id.cast(str).ilike(term),
            )
        )

    if category_id:
        query = query.where(
            Product.category_id == parse_uuid(
                category_id,
                "category_id",
            )
        )

    if brand_id:
        query = query.where(
            Product.brand_id == parse_uuid(
                brand_id,
                "brand_id",
            )
        )

    if low_stock_only:
        query = query.where(
            Product.stock_quantity <= Product.minimum_stock
        )

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = int(count_result.scalar_one())

    offset = (page - 1) * page_size

    query = (
        query
        .order_by(Product.name.asc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    products = result.scalars().all()

    return ProductListResponse(
        items=[serialize_product(product) for product in products],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_product(
    payload: ProductCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.MANAGE_PRODUCTS)

    product = await create_product(
        db,
        current_user.shop_id,
        payload,
    )

    return serialize_product(product)


@router.get(
    "/lookup/code/{code}",
    response_model=ProductLookupResponse,
)
async def lookup_product_by_code(
    code: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Exact barcode lookup.

    The code is treated as a string so leading zeros are preserved.
    No barcode symbology is restricted here; scanner values are looked up
    exactly as received after trimming surrounding whitespace.
    """

    normalized_code = code.strip()

    if not normalized_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Barcode cannot be empty.",
        )

    result = await db.execute(
        select(ProductCode, Product)
        .join(
            Product,
            Product.id == ProductCode.product_id,
        )
        .where(
            ProductCode.shop_id == current_user.shop_id,
            ProductCode.code == normalized_code,
            ProductCode.active.is_(True),
            Product.active.is_(True),
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "No active product was found for this barcode.",
                "code": normalized_code,
                "create_product_suggestion": True,
            },
        )

    product_code, product = row

    return ProductLookupResponse(
        product_id=str(product.id),
        product_name=product.name,
        code=product_code.code,
        code_type=product_code.code_type,
        selling_price=product.selling_price,
        stock_quantity=product.stock_quantity,
        active=product.active,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
async def get_product(
    product_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    product = await load_product(
        db,
        current_user.shop_id,
        product_id,
    )

    return serialize_product(product)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
)
async def edit_product(
    product_id: str,
    payload: ProductUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.MANAGE_PRODUCTS)

    product_uuid = parse_uuid(product_id, "product_id")

    product = await update_product(
        db,
        current_user.shop_id,
        product_uuid,
        payload,
    )

    return serialize_product(product)


@router.post(
    "/{product_id}/codes",
    response_model=ProductCodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_code(
    product_id: str,
    payload: ProductCodeCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.MANAGE_BARCODES)

    product_uuid = parse_uuid(product_id, "product_id")

    product_code = await add_product_code(
        db,
        current_user.shop_id,
        product_uuid,
        payload.code,
        payload.code_type,
        payload.is_primary,
    )

    return serialize_code(product_code)


@router.delete(
    "/{product_id}/codes/{code_id}",
)
async def deactivate_code(
    product_id: str,
    code_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.MANAGE_BARCODES)

    product_uuid = parse_uuid(product_id, "product_id")
    code_uuid = parse_uuid(code_id, "code_id")

    await remove_product_code(
        db,
        current_user.shop_id,
        product_uuid,
        code_uuid,
    )

    return {
        "success": True,
        "message": "Barcode deactivated successfully.",
    }


@router.post(
    "/{product_id}/image",
    response_model=ProductResponse,
)
async def upload_product_image(
    product_id: str,
    db: DbSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    require_permission(current_user, Permission.MANAGE_PRODUCTS)

    product = await load_product(
        db,
        current_user.shop_id,
        product_id,
    )

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product image must be PNG, JPEG, or WEBP.",
        )

    maximum_bytes = settings.max_upload_size_mb * 1024 * 1024
    data = await file.read()

    if len(data) > maximum_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Image exceeds the {settings.max_upload_size_mb} MB "
                "upload limit."
            ),
        )

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty.",
        )

    try:
        image = Image.open(io.BytesIO(data))
        image.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid image.",
        )

    product.image_data = data
    product.image_content_type = file.content_type

    await db.commit()
    await db.refresh(product)

    return serialize_product(product)


@router.get(
    "/{product_id}/image",
    include_in_schema=False,
)
async def get_product_image(
    product_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    product = await load_product(
        db,
        current_user.shop_id,
        product_id,
    )

    if not product.image_data or not product.image_content_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product image has not been uploaded.",
        )

    return Response(
        content=product.image_data,
        media_type=product.image_content_type,
        headers={
            "Cache-Control": "no-cache",
        },
    )


@router.delete(
    "/{product_id}/image",
    response_model=ProductResponse,
)
async def remove_product_image(
    product_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.MANAGE_PRODUCTS)

    product = await load_product(
        db,
        current_user.shop_id,
        product_id,
    )

    product.image_data = None
    product.image_content_type = None

    await db.commit()
    await db.refresh(product)

    return serialize_product(product)


@router.post(
    "/{product_id}/archive",
    response_model=ProductResponse,
)
async def archive_existing_product(
    product_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.MANAGE_PRODUCTS)

    product_uuid = parse_uuid(product_id, "product_id")

    product = await archive_product(
        db,
        current_user.shop_id,
        product_uuid,
    )

    return serialize_product(product)
