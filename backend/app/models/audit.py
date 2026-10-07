from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

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

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(100),
    )

    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
    )

    description: Mapped[str | None] = mapped_column(
        Text,
    )

    old_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
    )

    new_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(100),
    )

    __table_args__ = (
        Index(
            "ix_audit_logs_shop_created",
            "shop_id",
            "created_at",
        ),
        Index(
            "ix_audit_logs_shop_entity",
            "shop_id",
            "entity_type",
            "entity_id",
        ),
    )
