import uuid
from datetime import datetime

from sqlmodel import SQLModel

from app.partners.models.asset import AssetType


class PartnerAssetCreate(SQLModel):
    file_key: str
    asset_type: AssetType
    label: str


class PartnerAssetRead(SQLModel):
    id: uuid.UUID
    file_key: str
    asset_type: AssetType
    label: str
    uploaded_by: uuid.UUID
    created_at: datetime
