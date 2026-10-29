from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field


def utcnow() -> datetime:
    return datetime.utcnow()


class TimestampMixin(SQLModel):
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime, default=utcnow, nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False),
    )
