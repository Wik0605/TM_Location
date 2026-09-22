from datetime import datetime
from typing import Optional
from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field

from app.models.base import utcnow


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    google_id: Optional[str] = Field(default=None, max_length=100, unique=True, index=True)
    facebook_id: Optional[str] = Field(default=None, max_length=100, unique=True, index=True)
    email: str = Field(max_length=255, unique=True)
    name: str = Field(max_length=150)
    picture: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime, default=utcnow, nullable=False),
    )


class UserRead(SQLModel):
    id: int
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime
