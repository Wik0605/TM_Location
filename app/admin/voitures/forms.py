from datetime import time
from typing import Optional

from fastapi import Form
from pydantic import BaseModel, Field


class VoitureCreateForm(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=2000)
    places: int = Field(5, ge=1, le=20)
    consommation_carburant: float = Field(8.0, ge=0, le=100)
    heure_dispo_debut: Optional[time] = None
    heure_dispo_fin: Optional[time] = None

    @classmethod
    def as_form(
        cls,
        nom: str = Form(...),
        description: str = Form(...),
        places: int = Form(5),
        consommation_carburant: float = Form(8.0),
        heure_dispo_debut: Optional[str] = Form(None),
        heure_dispo_fin: Optional[str] = Form(None),
    ) -> "VoitureCreateForm":
        return cls(
            nom=nom,
            description=description,
            places=places,
            consommation_carburant=consommation_carburant,
            heure_dispo_debut=time.fromisoformat(heure_dispo_debut) if heure_dispo_debut else None,
            heure_dispo_fin=time.fromisoformat(heure_dispo_fin) if heure_dispo_fin else None,
        )


class VoitureUpdateForm(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    places: Optional[int] = Field(None, ge=1, le=20)
    consommation_carburant: Optional[float] = Field(None, ge=0, le=100)
    is_available: Optional[str] = Field(None, max_length=10)
    heure_dispo_debut: Optional[time] = None
    heure_dispo_fin: Optional[time] = None

    @classmethod
    def as_form(
        cls,
        nom: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        places: Optional[int] = Form(None),
        consommation_carburant: Optional[float] = Form(None),
        is_available: Optional[str] = Form(None),
        heure_dispo_debut: Optional[str] = Form(None),
        heure_dispo_fin: Optional[str] = Form(None),
    ) -> "VoitureUpdateForm":
        return cls(
            nom=nom,
            description=description,
            places=places,
            consommation_carburant=consommation_carburant,
            is_available=is_available,
            heure_dispo_debut=time.fromisoformat(heure_dispo_debut) if heure_dispo_debut else None,
            heure_dispo_fin=time.fromisoformat(heure_dispo_fin) if heure_dispo_fin else None,
        )


class TypeLocationForm(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    prix: int = Field(..., gt=0, lt=100_000_000)

    @classmethod
    def as_form(
        cls,
        nom: str = Form(...),
        prix: int = Form(...),
    ) -> "TypeLocationForm":
        return cls(nom=nom, prix=prix)
