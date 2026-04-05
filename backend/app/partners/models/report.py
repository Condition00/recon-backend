import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON
from sqlmodel import Column, Field, Relationship, SQLModel

from app.utils.models.base import Base


class PartnerReportBase(SQLModel):
    report_type: str = Field(max_length=100)  # e.g. "post_event_roi", "survey_round_1"
    generated_at: datetime


class PartnerReport(Base, PartnerReportBase, table=True):
    __tablename__ = "partner_reports"

    partner_id: uuid.UUID = Field(foreign_key="partners.id", index=True)
    data: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    partner: Optional["Partner"] = Relationship(back_populates="reports")


from app.partners.models.partner import Partner  # noqa: E402, F401
