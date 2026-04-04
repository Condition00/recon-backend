from fastapi import APIRouter, Depends

from app.domains.auth.models import ROLE_ADMIN, ROLE_PARTICIPANT, User
from app.infrastructure.storage.controller import get_read_url, get_upload_url
from app.infrastructure.storage.schemas import PresignedReadResponse, PresignedUploadResponse
from app.utils.deps import get_current_user, require_roles

router = APIRouter(prefix="/r2", tags=["storage"])


@router.get("/upload-url", response_model=PresignedUploadResponse)
def request_upload_url(
    filename: str,
    content_type: str,
    current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_PARTICIPANT)),
):
    return get_upload_url(current_user.id, filename, content_type)


@router.get("/read-url", response_model=PresignedReadResponse)
def request_read_url(
    file_key: str,
    _: User = Depends(get_current_user),
):
    return get_read_url(file_key)
