import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class ShopItemCreate(SQLModel):
    name: str
    description: str
    point_cost: int
    stock: Optional[int] = None
    photo_key: Optional[str] = None


class ShopItemUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    point_cost: Optional[int] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None
    photo_key: Optional[str] = None


class ShopItemRead(SQLModel):
    id: uuid.UUID
    name: str
    description: str
    point_cost: int
    stock: Optional[int]
    remaining_stock: Optional[int]
    is_active: bool
    photo_key: Optional[str]
    created_at: datetime
    updated_at: datetime
