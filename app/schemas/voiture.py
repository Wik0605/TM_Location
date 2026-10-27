from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, ConfigDict


class VoitureImageLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str


class VoitureImageFull(VoitureImageLite):
    position: int


class VoitureImageAdmin(VoitureImageFull):
    id: int
    voiture_id: int


class TypeLocationLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prix: int


class TypeLocationAdmin(TypeLocationLite):
    voiture_id: int


class VoitureLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    nom: str
    places: int


class VoitureFull(VoitureLite):
    description: str
    consommation_carburant: float
    heure_dispo_debut: Optional[time] = None
    heure_dispo_fin: Optional[time] = None
    images: list[VoitureImageFull] = []
    types_location: list[TypeLocationLite] = []


class VoitureAdmin(VoitureFull):
    is_available: bool
    created_at: datetime
    updated_at: datetime
