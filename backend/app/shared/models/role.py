from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.models.base import Base

ROLE_ADMIN = "admin"
ROLE_PARTICIPANT = "participant"
ROLE_APPLICANT = "applicant"
ROLE_PARTNER = "partner"
DEFAULT_ROLE_NAMES = (ROLE_ADMIN, ROLE_PARTICIPANT, ROLE_APPLICANT, ROLE_PARTNER)


class RoleBase(SQLModel):
    name: str = Field(max_length=50, unique=True, index=True)
    description: Optional[str] = Field(default=None, max_length=255)


class Role(Base, RoleBase, table=True):
    __tablename__ = "roles"

    users: list["User"] = Relationship(back_populates="role")


from app.models.user import User  # noqa: E402, F401
