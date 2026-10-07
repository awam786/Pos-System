from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Shop(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shops"

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    address: Mapped[str | None] = mapped_column(Text)

    phone: Mapped[str | None] = mapped_column(
        String(50),
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
    )

    logo_data: Mapped[bytes | None] = mapped_column(
        LargeBinary,
    )

    logo_content_type: Mapped[str | None] = mapped_column(
        String(100),
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        default="PKR",
        nullable=False,
    )

    timezone: Mapped[str] = mapped_column(
        String(80),
        default="Asia/Karachi",
        nullable=False,
    )

    receipt_width: Mapped[int] = mapped_column(
        Integer,
        default=80,
        nullable=False,
    )

    receipt_header: Mapped[str | None] = mapped_column(
        Text,
    )

    receipt_footer: Mapped[str | None] = mapped_column(
        Text,
        default="Thank you for shopping with us!",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="shop",
        cascade="all, delete-orphan",
    )
