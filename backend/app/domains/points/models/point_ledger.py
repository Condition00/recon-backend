import uuid

from sqlmodel import Field, SQLModel

from app.utils.models.base import Base


class PointLedgerBase(SQLModel):
    participant_id: uuid.UUID = Field(foreign_key="participants.id", index=True)
    amount: int = Field(description="Signed point delta. Positive=earn, negative=spend")
    reason: str = Field(max_length=120, index=True)
    reference_id: uuid.UUID | None = Field(default=None, index=True)
    idempotency_key: str = Field(max_length=100, unique=True, index=True)
    note: str | None = Field(default=None, max_length=300)
    resulting_balance: int = Field(description="Participant balance immediately after this entry.")


class PointLedger(Base, PointLedgerBase, table=True):
    __tablename__ = "point_ledger"

    awarded_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)
