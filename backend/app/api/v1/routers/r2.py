"""R2 router — presigned URL endpoints for resume uploads."""

from fastapi import APIRouter, Depends, Query
from sqlmodel import SQLModel

from app.api.deps import get_current_user, require_roles
from app.controllers import r2_controller
from app.models.role import ROLE_ADMIN, ROLE_APPLICANT
from app.models.user import User


class PresignedUploadResponse(SQLModel):
    upload_url: str
    file_key: str


class PresignedReadResponse(SQLModel):
    read_url: str
    file_key: str


router = APIRouter(prefix="/r2", tags=["r2"])


@router.get("/upload-url", response_model=PresignedUploadResponse)
async def get_upload_url(
    filename: str = Query(..., min_length=1, max_length=255),
    content_type: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_roles(ROLE_APPLICANT)),
):
    """Get a presigned URL to upload a resume directly to R2."""
    return r2_controller.get_resume_upload_url(current_user, filename, content_type)


@router.get("/read-url", response_model=PresignedReadResponse)
async def get_read_url(
    file_key: str = Query(..., min_length=1),
    _: User = Depends(require_roles(ROLE_ADMIN)),
):
    """Get a presigned URL to read/download a resume from R2 (admin only)."""
    return r2_controller.get_resume_read_url(file_key)
