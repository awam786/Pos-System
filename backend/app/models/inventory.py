from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import CashMovementType, StockMovementType


class StockMovement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stock_movements"

    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    movement_type: Mapped[StockMovementType] = mapped_column(
        String(40),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
    )

    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
    )

    reference_type: Mapped[str | None] = mapped_column(
        String(50),
    )

    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
    )

    __table_args__ = (
        Index(
            "ix_stock_movements_shop_product_created",
            "shop_id",
            "product_id",
            "created_at",
        ),
    )


class Expense(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "expenses"

    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    payment_method: Mapped[str] = mapped_column(
        String(30),
        default="cash",
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
    )

    reference: Mapped[str | None] = mapped_column(
        String(150),
    )


class CashRegister(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cash_registers"

    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    opened_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    closed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=0,
        nullable=False,
    )

    expected_closing_balance: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )

    actual_closing_balance: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )

    difference: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )

    is_open: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
    )


class CashMovement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cash_movements"

    cash_register_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_registers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    movement_type: Mapped[CashMovementType] = mapped_column(
        String(30),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
    )

    description: Mapped[str | None] = mapped_column(
        Text,
    )


class HeldSale(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "held_sales"

    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
    )

    reference: Mapped[str | None] = mapped_column(
        String(100),
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
    )


class HeldSaleItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "held_sale_items"

    held_sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("held_sales.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    discount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=0,
        nullable=False,
    )
