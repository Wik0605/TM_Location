from datetime import datetime
from typing import Optional
from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field

from app.models.base import utcnow


class AnalyticsEvent(SQLModel, table=True):
    __tablename__ = "analytics_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = Field(max_length=40, index=True)
    session_id: Optional[str] = Field(default=None, max_length=36, index=True)

    depart_lat: Optional[float] = None
    depart_lon: Optional[float] = None
    arrivee_lat: Optional[float] = None
    arrivee_lon: Optional[float] = None
    depart_nom: Optional[str] = Field(default=None, max_length=120)
    arrivee_nom: Optional[str] = Field(default=None, max_length=120)
    distance_km: Optional[float] = None

    voiture_id: Optional[int] = Field(default=None, foreign_key="voitures.id")
    type_location_id: Optional[int] = Field(default=None, foreign_key="types_location.id")
    prix: Optional[float] = None

    referer_host: Optional[str] = Field(default=None, max_length=120)
    hour_local: Optional[int] = None

    location_id: Optional[int] = Field(default=None, foreign_key="locations.id")

    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime, default=utcnow, nullable=False, index=True),
    )


class EventIn(SQLModel):
    event_type: str = Field(min_length=1, max_length=40)
    session_id: Optional[str] = Field(default=None, max_length=36)
    depart_lat: Optional[float] = None
    depart_lon: Optional[float] = None
    arrivee_lat: Optional[float] = None
    arrivee_lon: Optional[float] = None
    depart_nom: Optional[str] = None
    arrivee_nom: Optional[str] = None
    distance_km: Optional[float] = None
    voiture_id: Optional[int] = None
    type_location_id: Optional[int] = None
    prix: Optional[float] = None
    referer_host: Optional[str] = None
    hour_local: Optional[int] = None
