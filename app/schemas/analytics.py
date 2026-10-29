from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnalyticsAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    session_id: str | None = None

    depart_lat: float | None = None
    depart_lon: float | None = None
    arrivee_lat: float | None = None
    arrivee_lon: float | None = None
    depart_nom: str | None = None
    arrivee_nom: str | None = None
    distance_km: float | None = None

    voiture_id: int | None = None
    type_location_id: int | None = None
    location_id: int | None = None
    prix: float | None = None

    referer_host: str | None = None
    hour_local: int | None = None
    created_at: datetime
