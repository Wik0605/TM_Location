from enum import Enum

from fastapi import Form
from pydantic import BaseModel


class LocationStatus(str, Enum):
    confirmee = "confirmée"
    en_cours = "en_cours"
    terminee = "terminée"
    annulee = "annulée"


class RentalStatusForm(BaseModel):
    status: LocationStatus

    @classmethod
    def as_form(cls, status: str = Form(...)) -> "RentalStatusForm":
        return cls(status=status)


class RentalDeleteForm(BaseModel):
    username: str
    password: str

    @classmethod
    def as_form(
        cls,
        username: str = Form(...),
        password: str = Form(...),
    ) -> "RentalDeleteForm":
        return cls(username=username, password=password)
