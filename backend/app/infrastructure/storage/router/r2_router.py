from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.database import get_db
from app.domains.auth.models import ROLE_ADMIN, ROLE_PARTICIPANT, ROLE_PARTNER, User
from app.infrastructure.storage.controller import get_read_url, get_upload_url
from app.infrastructure.storage.schemas import (
    PresignedReadResponse,
    PresignedUploadResponse,
    StorageObjectScope,
)
from app.utils.deps import get_current_user, require_roles

router = APIRouter(prefix="/r2", tags=["storage"])


@router.get("/upload-url", response_model=PresignedUploadResponse)
async def request_upload_url(
    filename: str,
    content_type: str,
    scope: StorageObjectScope = StorageObjectScope.participant_private,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_PARTICIPANT, ROLE_PARTNER)),
):
    return await get_upload_url(db, current_user, filename, content_type, scope)


@router.get("/read-url", response_model=PresignedReadResponse)
async def request_read_url(
    file_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_read_url(db, current_user, file_key)
