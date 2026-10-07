from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categories"

    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    parent: Mapped["Category | None"] = relationship(
        remote_side="Category.id",
        back_populates="children",
    )

    children: Mapped[list["Category"]] = relationship(
        back_populates="parent",
    )

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "name",
            name="uq_categories_shop_name",
        ),
    )


class Brand(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "brands"

    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "name",
            name="uq_brands_shop_name",
        ),
    )


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
    )

    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="SET NULL"),
    )

    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    sku: Mapped[str | None] = mapped_column(
        String(100),
    )

    unit: Mapped[str] = mapped_column(
        String(30),
        default="pcs",
        nullable=False,
    )

    purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=0,
        nullable=False,
    )

    selling_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=0,
        nullable=False,
    )

    wholesale_price: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )

    minimum_price: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )

    stock_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        default=0,
        nullable=False,
    )

    minimum_stock: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        default=0,
        nullable=False,
    )

    maximum_stock: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 3),
    )

    image_data: Mapped[bytes | None] = mapped_column(
        LargeBinary,
    )

    image_content_type: Mapped[str | None] = mapped_column(
        String(100),
    )

    description: Mapped[str | None] = mapped_column(
        Text,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    codes: Mapped[list["ProductCode"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_products_shop_name",
            "shop_id",
            "name",
        ),
        Index(
            "ix_products_shop_sku",
            "shop_id",
            "sku",
        ),
    )


class ProductCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_codes"

    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    code_type: Mapped[str | None] = mapped_column(
        String(40),
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    product: Mapped["Product"] = relationship(
        back_populates="codes",
    )

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "code",
            name="uq_product_codes_shop_code",
        ),
        Index(
            "ix_product_codes_product",
            "product_id",
        ),
    )
