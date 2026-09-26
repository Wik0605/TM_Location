from datetime import datetime

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
    images: list[VoitureImageFull] = []
    types_location: list[TypeLocationLite] = []


class VoitureAdmin(VoitureFull):
    is_available: bool
    created_at: datetime
    updated_at: datetime
