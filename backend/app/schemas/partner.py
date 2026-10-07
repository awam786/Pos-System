from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=2000)
    opening_balance: Decimal = Field(default=Decimal("0"), ge=0)
    active: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Supplier name cannot be empty.")
        return value


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=2000)
    active: bool | None = None


class SupplierResponse(BaseModel):
    id: str
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    opening_balance: Decimal
    active: bool


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=2000)
    credit_limit: Decimal = Field(default=Decimal("0"), ge=0)
    opening_balance: Decimal = Field(default=Decimal("0"), ge=0)
    active: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Customer name cannot be empty.")
        return value


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=2000)
    credit_limit: Decimal | None = Field(default=None, ge=0)
    active: bool | None = None


class CustomerResponse(BaseModel):
    id: str
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    credit_limit: Decimal
    opening_balance: Decimal
    active: bool


class PartnerPaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    payment_method: str = Field(default="cash", min_length=1, max_length=30)
    reference: str | None = Field(default=None, max_length=150)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("payment_method")
    @classmethod
    def clean_payment_method(cls, value: str) -> str:
        value = value.strip().lower()

        allowed = {
            "cash",
            "bank_transfer",
            "card",
            "other",
        }

        if value not in allowed:
            raise ValueError(
                "Payment method must be cash, bank_transfer, card, or other."
            )

        return value


class PartnerPaymentResponse(BaseModel):
    id: str
    partner_id: str
    amount: Decimal
    payment_method: str
    reference: str | None = None
    notes: str | None = None
