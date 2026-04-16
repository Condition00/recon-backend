from enum import Enum

from pydantic import BaseModel


class StorageObjectScope(str, Enum):
    participant_private = "participant_private"
    partner_private = "partner_private"
    public = "public"
    admin_private = "admin_private"


class PresignedUploadResponse(BaseModel):
    upload_url: str
    file_key: str


class PresignedReadResponse(BaseModel):
    read_url: str
    file_key: str
