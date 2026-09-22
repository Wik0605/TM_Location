from typing import Optional
from sqlmodel import SQLModel, Field


class ItineraireRequest(SQLModel):
    depart_lat: float = Field(ge=-90, le=90)
    depart_lon: float = Field(ge=-180, le=180)
    arrivee_lat: float = Field(ge=-90, le=90)
    arrivee_lon: float = Field(ge=-180, le=180)
    depart_nom: Optional[str] = None
    arrivee_nom: Optional[str] = None
    type_location_id: Optional[int] = None


class DevisResponse(SQLModel):
    distance_km: float
    prix_total: float
    source: str
    token: str
