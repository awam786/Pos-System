from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    parent_id: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: str | None = None
    active: bool | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    parent_id: str | None = None
    active: bool


class BrandCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    active: bool | None = None


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    active: bool
