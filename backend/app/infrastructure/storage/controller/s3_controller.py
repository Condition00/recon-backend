import re
import uuid

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import ROLE_ADMIN, ROLE_PARTNER, User
from app.domains.participants.crud import get_participant_by_user_id
from app.infrastructure.storage.schemas.s3_schemas import (
    PresignedReadResponse,
    PresignedUploadResponse,
    StorageObjectScope,
)
from app.infrastructure.storage.service.s3_service import (
    ALLOWED_CONTENT_TYPES, ALLOWED_EXTENSIONS, get_r2_service,
)
from app.partners.crud import get_partner_by_id, get_partner_by_user_id

_UUID_SEGMENT = r"[0-9a-fA-F\-]{36}"
_FILENAME_SEGMENT = r"[0-9a-f]{32}\.[A-Za-z0-9]+"
_PARTICIPANT_KEY_RE = re.compile(rf"^participants/(?P<user_id>{_UUID_SEGMENT})/(?P<filename>{_FILENAME_SEGMENT})$")
_PARTNER_KEY_RE = re.compile(rf"^partners/(?P<partner_id>{_UUID_SEGMENT})/(?P<filename>{_FILENAME_SEGMENT})$")
_ADMIN_KEY_RE = re.compile(rf"^admin/(?P<user_id>{_UUID_SEGMENT})/(?P<filename>{_FILENAME_SEGMENT})$")
_LEGACY_ASSET_KEY_RE = re.compile(rf"^assets/(?P<user_id>{_UUID_SEGMENT})/(?P<filename>{_FILENAME_SEGMENT})$")
_PUBLIC_KEY_RE = re.compile(r"^public/[A-Za-z0-9][A-Za-z0-9/_-]*\.[A-Za-z0-9]+$")


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


def _forbidden(detail: str = "You do not have access to this file.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def get_upload_url(
    db: AsyncSession,
    current_user: User,
    filename: str,
    content_type: str,
    scope: StorageObjectScope,
) -> PresignedUploadResponse:
    _validate_content_type(content_type)
    ext = _validate_extension(filename)
    file_key = await _build_file_key(db, current_user=current_user, ext=ext, scope=scope)
    url = get_r2_service().generate_upload_url(file_key, content_type)
    return PresignedUploadResponse(upload_url=url, file_key=file_key)


async def get_read_url(db: AsyncSession, current_user: User, file_key: str
    ) -> PresignedReadResponse:
    await _authorize_read(db, current_user=current_user, file_key=file_key)
    url = get_r2_service().generate_read_url(file_key)
    return PresignedReadResponse(read_url=url, file_key=file_key)


async def _build_file_key(
    db: AsyncSession, *, current_user: User, ext: str, scope: StorageObjectScope
) -> str:
    object_name = f"{uuid.uuid4().hex}.{ext}"

    if scope == StorageObjectScope.participant_private:
        return f"participants/{current_user.id}/{object_name}"

    if scope == StorageObjectScope.partner_private:
        partner = await get_partner_by_user_id(db, current_user.id)
        if not partner or current_user.role is None or current_user.role.name != ROLE_PARTNER:
            raise _forbidden("Only approved partner accounts can upload partner assets.")
        return f"partners/{partner.id}/{object_name}"

    if scope == StorageObjectScope.public:
        if current_user.role is None or current_user.role.name != ROLE_ADMIN:
            raise _forbidden("Only admins can upload public assets.")
        return f"public/{object_name}"

    if scope == StorageObjectScope.admin_private:
        if current_user.role is None or current_user.role.name != ROLE_ADMIN:
            raise _forbidden("Only admins can upload admin assets.")
        return f"admin/{current_user.id}/{object_name}"

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage scope.")


async def _authorize_read(db: AsyncSession, *, current_user: User, file_key: str) -> None:
    if _PUBLIC_KEY_RE.match(file_key):
        return

    participant_match = _PARTICIPANT_KEY_RE.match(file_key)
    if participant_match:
        owner_user_id = uuid.UUID(participant_match.group("user_id"))
        if current_user.id == owner_user_id or _is_admin(current_user):
            return

        participant = await get_participant_by_user_id(db, owner_user_id)
        if participant and participant.profile_photo_file_key == file_key and participant.talent_visible:
            return
        raise _forbidden()

    legacy_match = _LEGACY_ASSET_KEY_RE.match(file_key)
    if legacy_match:
        owner_user_id = uuid.UUID(legacy_match.group("user_id"))
        if current_user.id == owner_user_id or _is_admin(current_user):
            return
        raise _forbidden()

    partner_match = _PARTNER_KEY_RE.match(file_key)
    if partner_match:
        partner_id = uuid.UUID(partner_match.group("partner_id"))
        if _is_admin(current_user):
            return

        partner = await get_partner_by_id(db, partner_id)
        if partner and partner.user_id == current_user.id:
            return
        raise _forbidden()

    admin_match = _ADMIN_KEY_RE.match(file_key)
    if admin_match:
        owner_user_id = uuid.UUID(admin_match.group("user_id"))
        if _is_admin(current_user) and current_user.id == owner_user_id:
            return
        raise _forbidden()

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file key.")


def _is_admin(current_user: User) -> bool:
    return current_user.role is not None and current_user.role.name == ROLE_ADMIN
