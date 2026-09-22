from datetime import datetime
from typing import Optional
from sqlalchemy import Column, DateTime, Text
from sqlmodel import SQLModel, Field, Relationship

from app.models.base import utcnow
from app.models.voiture import Voiture, TypeLocation


class Location(SQLModel, table=True):
    __tablename__ = "locations"

    id: Optional[int] = Field(default=None, primary_key=True)
    voiture_id: int = Field(foreign_key="voitures.id")
    type_location_id: Optional[int] = Field(default=None, foreign_key="types_location.id")

    client_nom: str = Field(max_length=100)
    client_telephone: str = Field(max_length=20)
    client_email: Optional[str] = Field(default=None, max_length=100)

    date_debut: datetime = Field(sa_column=Column(DateTime, nullable=False))
    date_fin: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    duree_minutes: Optional[int] = None
    prix_total: float
    statut: str = Field(default="confirmée", max_length=20)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    itineraire_distance_km: Optional[float] = None
    itineraire_depart: Optional[str] = Field(default=None, max_length=255)
    itineraire_arrivee: Optional[str] = Field(default=None, max_length=255)
    depart_coords: Optional[str] = Field(default=None, max_length=50)
    arrivee_coords: Optional[str] = Field(default=None, max_length=50)
    itineraire_etapes: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    itineraire_source: Optional[str] = Field(default=None, max_length=20)

    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime, default=utcnow, nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False),
    )

    voiture: Voiture = Relationship(back_populates="locations")
    type_location: Optional[TypeLocation] = Relationship(back_populates="locations")


class LocationCreate(SQLModel):
    voiture_id: int
    type_location_id: Optional[int] = None
    client_nom: str = Field(min_length=2, max_length=100)
    client_telephone: str = Field(min_length=8, max_length=20)
    client_email: Optional[str] = None
    date_debut: datetime
    date_fin: Optional[datetime] = None
    notes: Optional[str] = None


class LocationRead(LocationCreate):
    id: int
    prix_total: float
    statut: str
    created_at: datetime
    updated_at: datetime
