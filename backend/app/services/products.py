from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Brand, Category, Product, ProductCode, Supplier
from app.schemas.product import ProductCreate, ProductUpdate


def parse_uuid(
    value: str | None,
    field_name: str,
) -> uuid.UUID | None:
    if value is None:
        return None

    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {field_name}.",
        )


async def validate_related_records(
    db: AsyncSession,
    shop_id: uuid.UUID,
    category_id: uuid.UUID | None,
    brand_id: uuid.UUID | None,
    supplier_id: uuid.UUID | None,
) -> None:
    if category_id is not None:
        result = await db.execute(
            select(Category).where(
                Category.id == category_id,
                Category.shop_id == shop_id,
                Category.active.is_(True),
            )
        )

        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )

    if brand_id is not None:
        result = await db.execute(
            select(Brand).where(
                Brand.id == brand_id,
                Brand.shop_id == shop_id,
                Brand.active.is_(True),
            )
        )

        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand not found.",
            )

    if supplier_id is not None:
        result = await db.execute(
            select(Supplier).where(
                Supplier.id == supplier_id,
                Supplier.shop_id == shop_id,
            )
        )

        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found.",
            )


async def validate_codes_are_unique(
    db: AsyncSession,
    shop_id: uuid.UUID,
    codes: list[str],
    exclude_product_id: uuid.UUID | None = None,
) -> None:
    normalized_codes = [code.strip() for code in codes]

    if len(normalized_codes) != len(set(normalized_codes)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The same barcode cannot be added more than once.",
        )

    if not normalized_codes:
        return

    result = await db.execute(
        select(ProductCode).where(
            ProductCode.shop_id == shop_id,
            ProductCode.code.in_(normalized_codes),
            ProductCode.active.is_(True),
        )
    )

    existing_codes = result.scalars().all()

    for existing in existing_codes:
        if (
            exclude_product_id is None
            or existing.product_id != exclude_product_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Barcode '{existing.code}' is already assigned "
                    "to another product."
                ),
            )


async def get_product_for_shop(
    db: AsyncSession,
    shop_id: uuid.UUID,
    product_id: uuid.UUID,
) -> Product:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.shop_id == shop_id,
        )
    )

    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return product


async def create_product(
    db: AsyncSession,
    shop_id: uuid.UUID,
    payload: ProductCreate,
) -> Product:
    category_id = parse_uuid(payload.category_id, "category_id")
    brand_id = parse_uuid(payload.brand_id, "brand_id")
    supplier_id = parse_uuid(payload.supplier_id, "supplier_id")

    await validate_related_records(
        db,
        shop_id,
        category_id,
        brand_id,
        supplier_id,
    )

    requested_codes = [
        item.code.strip()
        for item in payload.codes
    ]

    await validate_codes_are_unique(
        db,
        shop_id,
        requested_codes,
    )

    if payload.sku:
        sku_result = await db.execute(
            select(Product).where(
                Product.shop_id == shop_id,
                Product.sku == payload.sku,
            )
        )

        if sku_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A product with this SKU already exists.",
            )

    product = Product(
        shop_id=shop_id,
        category_id=category_id,
        brand_id=brand_id,
        supplier_id=supplier_id,
        name=payload.name.strip(),
        sku=payload.sku,
        unit=payload.unit.strip(),
        purchase_price=payload.purchase_price,
        selling_price=payload.selling_price,
        wholesale_price=payload.wholesale_price,
        minimum_price=payload.minimum_price,
        stock_quantity=payload.stock_quantity,
        minimum_stock=payload.minimum_stock,
        maximum_stock=payload.maximum_stock,
        description=payload.description,
        active=payload.active,
    )

    db.add(product)
    await db.flush()

    primary_already_set = False

    for index, code_input in enumerate(payload.codes):
        requested_primary = code_input.is_primary

        if requested_primary and primary_already_set:
            requested_primary = False

        if requested_primary:
            primary_already_set = True

        code = ProductCode(
            shop_id=shop_id,
            product_id=product.id,
            code=code_input.code.strip(),
            code_type=(
                code_input.code_type.strip()
                if code_input.code_type
                else None
            ),
            is_primary=requested_primary,
            active=True,
        )

        db.add(code)

    if payload.codes and not primary_already_set:
        first_code_result = await db.execute(
            select(ProductCode).where(
                ProductCode.product_id == product.id,
            ).order_by(ProductCode.created_at.asc())
        )

        first_code = first_code_result.scalars().first()

        if first_code is not None:
            first_code.is_primary = True

    await db.commit()
    await db.refresh(product)

    return product


async def update_product(
    db: AsyncSession,
    shop_id: uuid.UUID,
    product_id: uuid.UUID,
    payload: ProductUpdate,
) -> Product:
    product = await get_product_for_shop(
        db,
        shop_id,
        product_id,
    )

    values = payload.model_dump(exclude_unset=True)

    category_id = (
        parse_uuid(payload.category_id, "category_id")
        if "category_id" in values
        else product.category_id
    )

    brand_id = (
        parse_uuid(payload.brand_id, "brand_id")
        if "brand_id" in values
        else product.brand_id
    )

    supplier_id = (
        parse_uuid(payload.supplier_id, "supplier_id")
        if "supplier_id" in values
        else product.supplier_id
    )

    await validate_related_records(
        db,
        shop_id,
        category_id,
        brand_id,
        supplier_id,
    )

    if "sku" in values and payload.sku:
        sku_result = await db.execute(
            select(Product).where(
                Product.shop_id == shop_id,
                Product.sku == payload.sku,
                Product.id != product.id,
            )
        )

        if sku_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A product with this SKU already exists.",
            )

    for field_name, value in values.items():
        if field_name == "name" and value is not None:
            value = value.strip()

        if field_name == "unit" and value is not None:
            value = value.strip()

        if field_name == "sku" and isinstance(value, str):
            value = value.strip() or None

        setattr(product, field_name, value)

    product.category_id = category_id
    product.brand_id = brand_id
    product.supplier_id = supplier_id

    if product.minimum_price is not None:
        if product.minimum_price > product.selling_price:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Minimum selling price cannot be greater than "
                    "selling price."
                ),
            )

    await db.commit()
    await db.refresh(product)

    return product


async def add_product_code(
    db: AsyncSession,
    shop_id: uuid.UUID,
    product_id: uuid.UUID,
    code: str,
    code_type: str | None,
    is_primary: bool,
) -> ProductCode:
    product = await get_product_for_shop(
        db,
        shop_id,
        product_id,
    )

    if not product.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add a barcode to an archived product.",
        )

    code = code.strip()

    await validate_codes_are_unique(
        db,
        shop_id,
        [code],
    )

    if is_primary:
        existing_primary_result = await db.execute(
            select(ProductCode).where(
                ProductCode.product_id == product.id,
                ProductCode.is_primary.is_(True),
                ProductCode.active.is_(True),
            )
        )

        for existing_primary in existing_primary_result.scalars().all():
            existing_primary.is_primary = False

    product_code = ProductCode(
        shop_id=shop_id,
        product_id=product.id,
        code=code,
        code_type=code_type.strip() if code_type else None,
        is_primary=is_primary,
        active=True,
    )

    db.add(product_code)
    await db.commit()
    await db.refresh(product_code)

    return product_code


async def remove_product_code(
    db: AsyncSession,
    shop_id: uuid.UUID,
    product_id: uuid.UUID,
    code_id: uuid.UUID,
) -> None:
    product = await get_product_for_shop(
        db,
        shop_id,
        product_id,
    )

    result = await db.execute(
        select(ProductCode).where(
            ProductCode.id == code_id,
            ProductCode.product_id == product.id,
            ProductCode.shop_id == shop_id,
            ProductCode.active.is_(True),
        )
    )

    product_code = result.scalar_one_or_none()

    if product_code is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product barcode not found.",
        )

    product_code.active = False

    if product_code.is_primary:
        product_code.is_primary = False

        replacement_result = await db.execute(
            select(ProductCode)
            .where(
                ProductCode.product_id == product.id,
                ProductCode.id != product_code.id,
                ProductCode.active.is_(True),
            )
            .order_by(ProductCode.created_at.asc())
            .limit(1)
        )

        replacement = replacement_result.scalar_one_or_none()

        if replacement is not None:
            replacement.is_primary = True

    await db.commit()


async def archive_product(
    db: AsyncSession,
    shop_id: uuid.UUID,
    product_id: uuid.UUID,
) -> Product:
    product = await get_product_for_shop(
        db,
        shop_id,
        product_id,
    )

    product.active = False

    await db.commit()
    await db.refresh(product)

    return product
