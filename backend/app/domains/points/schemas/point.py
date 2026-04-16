import datetime
import uuid

from sqlmodel import Field, SQLModel


class PointAwardCreate(SQLModel):
    participant_id: uuid.UUID
    amount: int = Field(description="Non-zero integer delta. Negative values spend points.")
    reason: str = Field(max_length=120)
    reference_id: uuid.UUID | None = None
    idempotency_key: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=300)


class PointTransactionRead(SQLModel):
    id: uuid.UUID
    participant_id: uuid.UUID
    amount: int
    reason: str
    reference_id: uuid.UUID | None = None
    idempotency_key: str | None = None
    note: str | None = None
    resulting_balance: int
    awarded_by_user_id: uuid.UUID | None = None
    created_at: datetime.datetime


class PointAwardRead(SQLModel):
    transaction: PointTransactionRead
    resulting_balance: int


class PointMeRead(SQLModel):
    participant_id: uuid.UUID
    balance: int
    recent_transactions: list[PointTransactionRead]


class PointLeaderboardEntry(SQLModel):
    rank: int
    participant_id: uuid.UUID
    display_name: str
    points: int


class PointLeaderboardPageRead(SQLModel):
    total_ranked: int
    skip: int
    limit: int
    entries: list[PointLeaderboardEntry]


class PointLeaderboardMeRead(SQLModel):
    participant_id: uuid.UUID
    rank: int | None = None
    total_ranked: int
    points: int


class PointTransactionsPageRead(SQLModel):
    total: int
    skip: int
    limit: int
    transactions: list[PointTransactionRead]
