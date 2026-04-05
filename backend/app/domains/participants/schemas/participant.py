import datetime
import uuid

from sqlmodel import SQLModel


class ParticipantCreate(SQLModel):
    display_name: str
    institution: str
    year: int
    linkedin_acc: str | None = None
    github_acc: str | None = None
    x_acc: str | None = None
    phone: str | None = None
    profile_photo_file_key: str | None = None
    talent_visible: bool = False
    talent_contact_shareable: bool = False


class ParticipantUpdate(SQLModel):
    display_name: str | None = None
    institution: str | None = None
    year: int | None = None
    linkedin_acc: str | None = None
    github_acc: str | None = None
    x_acc: str | None = None
    phone: str | None = None
    profile_photo_file_key: str | None = None


class ParticipantTalentVisibilityUpdate(SQLModel):
    talent_visible: bool
    talent_contact_shareable: bool = False


class ParticipantRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    institution: str
    year: int
    linkedin_acc: str | None = None
    github_acc: str | None = None
    x_acc: str | None = None
    phone: str | None = None
    profile_photo_file_key: str | None = None
    talent_visible: bool
    talent_contact_shareable: bool
    checked_in_at: datetime.datetime | None = None
    checked_in_by: uuid.UUID | None = None
    created_at: datetime.datetime
    can_edit: bool = False
    is_self: bool = False


class ParticipantCheckInRead(SQLModel):
    id: uuid.UUID
    checked_in_at: datetime.datetime
    checked_in_by: uuid.UUID
