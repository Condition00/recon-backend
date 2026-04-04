from pydantic import BaseModel


class PresignedUploadResponse(BaseModel):
    upload_url: str
    file_key: str


class PresignedReadResponse(BaseModel):
    read_url: str
    file_key: str
