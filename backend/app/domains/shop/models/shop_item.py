from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils.models.base import Base


class ShopItemBase(SQLModel):
    name: str = Field(max_length=100)
    description: str = Field(max_length=2000)
    point_cost: int = Field(ge=1)
    stock: Optional[int] = Field(default=None, ge=0)
    is_active: bool = Field(default=True)
    photo_key: Optional[str] = Field(default=None, max_length=500)


class ShopItem(Base, ShopItemBase, table=True):
    __tablename__ = "shop_items"
