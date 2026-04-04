import datetime
import uuid
from typing import Any

from app.models.user import UserBase
from app.schemas.user import RoleRead


class UserProfile(UserBase):
    id: uuid.UUID
    created_at: datetime.datetime
    form_response: dict[str, Any] | None = None
    role: RoleRead | None = None
