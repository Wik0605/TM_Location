from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.voiture import TypeLocationLite, VoitureLite


class LocationLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date_debut: datetime
    date_fin: datetime | None = None
    prix_total: float
    voiture: VoitureLite


class LocationFull(LocationLite):
    duree_minutes: int | None = None
    itineraire_distance_km: float | None = None
    itineraire_depart: str | None = None
    itineraire_arrivee: str | None = None
    type_location: TypeLocationLite | None = None


class LocationAdmin(LocationFull):
    client_nom: str
    client_telephone: str
    client_email: str | None = None
    statut: str
    notes: str | None = None
    depart_coords: str | None = None
    arrivee_coords: str | None = None
    itineraire_etapes: str | None = None
    itineraire_source: str | None = None
    created_at: datetime
    updated_at: datetime
