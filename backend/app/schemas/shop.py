from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ShopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    currency: str
    timezone: str
    receipt_width: int
    receipt_header: str | None = None
    receipt_footer: str | None = None
    is_active: bool
    has_logo: bool = False
    logo_content_type: str | None = None


class ShopUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    currency: str | None = Field(default=None, min_length=1, max_length=10)
    timezone: str | None = Field(default=None, min_length=1, max_length=80)
    receipt_width: int | None = None
    receipt_header: str | None = Field(default=None, max_length=5000)
    receipt_footer: str | None = Field(default=None, max_length=5000)

    def validate_receipt_width(self) -> None:
        if self.receipt_width is not None and self.receipt_width not in (58, 80):
            raise ValueError("Receipt width must be either 58 or 80.")
