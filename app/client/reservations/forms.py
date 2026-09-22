from datetime import date, datetime
from typing import Optional

from fastapi import Form
from pydantic import BaseModel, Field, field_validator


PHONE_REGEX = r"^[0-9+\s().-]{8,20}$"
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
NOM_PERSONNE_REGEX = r"^[A-Za-zÀ-ÿ\s'-]+$"


class LocationForm(BaseModel):
    type_location_id: Optional[int] = Field(None, gt=0)
    client_nom: str = Field(..., min_length=2, max_length=100, pattern=NOM_PERSONNE_REGEX)
    client_telephone: str = Field(..., pattern=PHONE_REGEX)
    client_email: Optional[str] = Field(None, pattern=EMAIL_REGEX, max_length=200)
    date_debut: datetime
    date_fin: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)
    itinerary_distance_km: Optional[float] = Field(None, ge=0, le=100000)
    itinerary_start_name: Optional[str] = Field(None, max_length=250)
    itinerary_end_name: Optional[str] = Field(None, max_length=250)
    itinerary_waypoints: Optional[str] = Field(None, max_length=5000)

    @field_validator("date_debut")
    @classmethod
    def _future_or_today(cls, v: datetime) -> datetime:
        if v.date() < date.today():
            raise ValueError("La date de départ ne peut pas être dans le passé.")
        return v

    @field_validator("date_fin")
    @classmethod
    def _fin_apres_debut(cls, v, info):
        if v is None:
            return v
        debut = info.data.get("date_debut")
        if debut and v <= debut:
            raise ValueError("La date de retour doit être postérieure à la date de départ.")
        return v

    @field_validator("client_email", mode="before")
    @classmethod
    def _empty_email_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v
