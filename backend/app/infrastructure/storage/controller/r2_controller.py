import re
import uuid

from fastapi import HTTPException, status

from app.infrastructure.storage.service.r2_service import (
    ALLOWED_CONTENT_TYPES, ALLOWED_EXTENSIONS, get_r2_service,
)
from app.infrastructure.storage.schemas.r2_schemas import PresignedUploadResponse, PresignedReadResponse

_FILE_KEY_RE = re.compile(r"^assets/[0-9a-f\-]{36}/[0-9a-f]{32}\.\w+$")


def _validate_content_type(content_type: str) -> None:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )


def _validate_extension(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


def get_upload_url(user_id: uuid.UUID, filename: str, content_type: str) -> PresignedUploadResponse:
    _validate_content_type(content_type)
    ext = _validate_extension(filename)
    file_key = f"assets/{user_id}/{uuid.uuid4().hex}.{ext}"
    url = get_r2_service().generate_upload_url(file_key, content_type)
    return PresignedUploadResponse(upload_url=url, file_key=file_key)


def get_read_url(file_key: str) -> PresignedReadResponse:
    if not _FILE_KEY_RE.match(file_key):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file key.")
    url = get_r2_service().generate_read_url(file_key)
    return PresignedReadResponse(read_url=url, file_key=file_key)
