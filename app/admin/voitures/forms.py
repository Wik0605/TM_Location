from typing import Optional

from fastapi import Form
from pydantic import BaseModel, Field


class VoitureCreateForm(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=2000)
    places: int = Field(5, ge=1, le=20)
    consommation_carburant: float = Field(8.0, ge=0, le=100)

    @classmethod
    def as_form(
        cls,
        nom: str = Form(...),
        description: str = Form(...),
        places: int = Form(5),
        consommation_carburant: float = Form(8.0),
    ) -> "VoitureCreateForm":
        return cls(
            nom=nom,
            description=description,
            places=places,
            consommation_carburant=consommation_carburant,
        )


class VoitureUpdateForm(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    places: Optional[int] = Field(None, ge=1, le=20)
    consommation_carburant: Optional[float] = Field(None, ge=0, le=100)
    is_available: Optional[str] = Field(None, max_length=10)

    @classmethod
    def as_form(
        cls,
        nom: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        places: Optional[int] = Form(None),
        consommation_carburant: Optional[float] = Form(None),
        is_available: Optional[str] = Form(None),
    ) -> "VoitureUpdateForm":
        return cls(
            nom=nom,
            description=description,
            places=places,
            consommation_carburant=consommation_carburant,
            is_available=is_available,
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
