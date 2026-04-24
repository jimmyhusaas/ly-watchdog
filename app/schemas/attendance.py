"""Pydantic schemas for attendance endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class AttendanceRankRow(BaseModel):
    """One row in the attendance ranking response."""

    model_config = ConfigDict(from_attributes=True)

    legislator_uid: str
    legislator_name: str
    term: int
    session_period: int
    attended: int = Field(description="出席次數")
    absent: int = Field(description="缺席次數")
    leave: int = Field(description="請假或公假次數")
    total: int = Field(description="總會議次數")
    rate: float = Field(description="出席率 (0-100)")
