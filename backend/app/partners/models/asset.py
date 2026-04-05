import uuid
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.utils.models.base import Base


class AssetType(str, Enum):
    logo = "logo"
    banner = "banner"
    social_post = "social_post"
    video = "video"
    document = "document"
    other = "other"


class PartnerAssetBase(SQLModel):
    file_key: str = Field(max_length=500)
    asset_type: AssetType
    label: str = Field(max_length=300)


class PartnerAsset(Base, PartnerAssetBase, table=True):
    __tablename__ = "partner_assets"

    partner_id: uuid.UUID = Field(foreign_key="partners.id", index=True)
    uploaded_by: uuid.UUID = Field(foreign_key="users.id")

    partner: Optional["Partner"] = Relationship(back_populates="assets")


from app.partners.models.partner import Partner  # noqa: E402, F401
