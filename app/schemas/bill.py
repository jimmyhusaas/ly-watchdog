"""Pydantic schemas for bill endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bill_uid: str
    term: int
    session_period: int
    bill_no: str
    bill_name: str
    bill_org: str | None
    bill_proposer: str | None
    bill_cosignatory: str | None
    bill_status: str
    valid_from: datetime
    valid_to: datetime | None
    recorded_at: datetime
    superseded_at: datetime | None


class BillOrgStatRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bill_org: str | None
    count: int
