"""R2 controller — generates presigned URLs for resume uploads."""

import re
import uuid

from fastapi import HTTPException, status

from app.models.user import User
from app.services.r2_service import ALLOWED_CONTENT_TYPES, ALLOWED_EXTENSIONS, get_r2_service

# file_key must match: resumes/{uuid}/{hex}.{ext}
_FILE_KEY_RE = re.compile(
    r"^resumes/[0-9a-f\-]{36}/[0-9a-f]{32}\.\w+$"
)


def _validate_content_type(content_type: str) -> None:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )


def _validate_extension(filename: str) -> str:
    """Extract and validate the file extension. Returns the sanitised extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


def get_resume_upload_url(user: User, filename: str, content_type: str) -> dict:
    """Return a presigned PUT URL scoped to the user's resume path."""
    _validate_content_type(content_type)
    ext = _validate_extension(filename)

    file_key = f"resumes/{user.id}/{uuid.uuid4().hex}.{ext}"

    upload_url = get_r2_service().generate_upload_url(file_key, content_type)
    return {"upload_url": upload_url, "file_key": file_key}


def get_resume_read_url(file_key: str) -> dict:
    """Return a presigned GET URL for the given file key."""
    if not _FILE_KEY_RE.match(file_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file key.",
        )

    read_url = get_r2_service().generate_read_url(file_key)
    return {"read_url": read_url, "file_key": file_key}
