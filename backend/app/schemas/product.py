from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductCodeInput(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    code_type: str | None = Field(default=None, max_length=40)
    is_primary: bool = False

    @field_validator("code")
    @classmethod
    def preserve_code(cls, value: str) -> str:
        """
        Barcode values remain strings intentionally.

        This preserves leading zeros and supports arbitrary scanner symbologies.
        """
        value = value.strip()

        if not value:
            raise ValueError("Barcode cannot be empty.")

        return value


class ProductCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    code_type: str | None = None
    is_primary: bool
    active: bool


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str | None = Field(default=None, max_length=100)

    category_id: str | None = None
    brand_id: str | None = None
    supplier_id: str | None = None

    unit: str = Field(default="pcs", min_length=1, max_length=30)

    purchase_price: Decimal = Field(default=Decimal("0"), ge=0)
    selling_price: Decimal = Field(default=Decimal("0"), ge=0)
    wholesale_price: Decimal | None = Field(default=None, ge=0)
    minimum_price: Decimal | None = Field(default=None, ge=0)

    stock_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    minimum_stock: Decimal = Field(default=Decimal("0"), ge=0)
    maximum_stock: Decimal | None = Field(default=None, ge=0)

    description: str | None = Field(default=None, max_length=5000)
    active: bool = True

    codes: list[ProductCodeInput] = Field(default_factory=list)

    @field_validator("name", "unit")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Value cannot be empty.")

        return value

    @field_validator("sku")
    @classmethod
    def strip_sku(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    sku: str | None = Field(default=None, max_length=100)

    category_id: str | None = None
    brand_id: str | None = None
    supplier_id: str | None = None

    unit: str | None = Field(default=None, min_length=1, max_length=30)

    purchase_price: Decimal | None = Field(default=None, ge=0)
    selling_price: Decimal | None = Field(default=None, ge=0)
    wholesale_price: Decimal | None = Field(default=None, ge=0)
    minimum_price: Decimal | None = Field(default=None, ge=0)

    minimum_stock: Decimal | None = Field(default=None, ge=0)
    maximum_stock: Decimal | None = Field(default=None, ge=0)

    description: str | None = Field(default=None, max_length=5000)
    active: bool | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    sku: str | None = None

    category_id: str | None = None
    brand_id: str | None = None
    supplier_id: str | None = None

    unit: str

    purchase_price: Decimal
    selling_price: Decimal
    wholesale_price: Decimal | None = None
    minimum_price: Decimal | None = None

    stock_quantity: Decimal
    minimum_stock: Decimal
    maximum_stock: Decimal | None = None

    description: str | None = None
    active: bool

    has_image: bool = False
    image_content_type: str | None = None
    codes: list[ProductCodeResponse] = Field(default_factory=list)


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int


class ProductLookupResponse(BaseModel):
    product_id: str
    product_name: str
    code: str
    code_type: str | None = None
    selling_price: Decimal
    stock_quantity: Decimal
    active: bool


class ProductCodeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    code_type: str | None = Field(default=None, max_length=40)
    is_primary: bool = False

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Barcode cannot be empty.")

        return value
