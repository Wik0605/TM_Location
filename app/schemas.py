from datetime import datetime, date
from enum import Enum
from typing import Optional
from fastapi import Form
from pydantic import BaseModel, Field, field_validator


class CarBase(BaseModel):
    brand: str = Field(..., min_length=2, max_length=50)
    model: str = Field(..., min_length=1, max_length=50)
    year: int = Field(..., ge=2000, le=2030)
    plate_number: str = Field(..., min_length=4, max_length=20)
    daily_price: float = Field(..., gt=0)
    seats: int = Field(default=5, ge=1, le=9)
    description: Optional[str] = None
    image_url: Optional[str] = None


class CarCreate(CarBase):
    pass


class CarUpdate(BaseModel):
    brand: Optional[str] = Field(None, min_length=2, max_length=50)
    model: Optional[str] = Field(None, min_length=1, max_length=50)
    year: Optional[int] = Field(None, ge=2000, le=2030)
    plate_number: Optional[str] = Field(None, min_length=4, max_length=20)
    daily_price: Optional[float] = Field(None, gt=0)
    seats: Optional[int] = Field(None, ge=1, le=9)
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None


class CarResponse(CarBase):
    id: int
    is_available: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RentalTypeBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    duration_days: int = Field(..., gt=0)
    price_multiplier: float = Field(default=1.0, ge=0)
    prix_fixe: Optional[float] = Field(default=None, ge=0)
    fuel_consumption: Optional[float] = Field(default=None, ge=0)
    fuel_price: Optional[float] = Field(default=None, ge=0)
    discount_percent: float = Field(default=0.0, ge=0, le=100)
    description: Optional[str] = None


class RentalTypeCreate(RentalTypeBase):
    pass


class RentalTypeResponse(RentalTypeBase):
    id: int

    model_config = {"from_attributes": True}


class TypeLocationCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    prix: int = Field(..., gt=0)


class TypeLocationResponse(TypeLocationCreate):
    id: int
    voiture_id: int

    model_config = {"from_attributes": True}


class VoitureCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    consommation_carburant: float = Field(default=8.0, ge=0)
    places: int = Field(default=5, ge=1, le=20)


class VoitureUpdate(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=100)
    consommation_carburant: Optional[float] = Field(None, ge=0)
    places: Optional[int] = Field(None, ge=1, le=20)
    is_available: Optional[bool] = None


class VoitureResponse(BaseModel):
    id: int
    nom: str
    consommation_carburant: float
    places: int
    is_available: bool
    types_location: list[TypeLocationResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LocationCreate(BaseModel):
    voiture_id: int
    type_location_id: Optional[int] = None
    client_nom: str = Field(..., min_length=2, max_length=100)
    client_telephone: str = Field(..., min_length=8, max_length=20)
    client_email: Optional[str] = None
    date_debut: datetime
    date_fin: Optional[datetime] = None
    notes: Optional[str] = None


class LocationResponse(LocationCreate):
    id: int
    prix_total: float
    statut: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RentalBase(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    customer_phone: str = Field(..., min_length=8, max_length=20)
    customer_email: Optional[str] = None
    car_id: int
    rental_type_id: int
    start_date: datetime
    end_date: datetime
    notes: Optional[str] = None


class RentalCreate(RentalBase):
    pass


class RentalResponse(RentalBase):
    id: int
    total_price: float
    status: str
    created_at: datetime
    updated_at: datetime
    car: Optional[CarResponse] = None
    rental_type: Optional[RentalTypeResponse] = None

    model_config = {"from_attributes": True}


PHONE_REGEX = r"^[0-9+\s().-]{8,20}$"
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
NOM_PERSONNE_REGEX = r"^[A-Za-zÀ-ÿ\s'-]+$"


class LocationForm(BaseModel):
    type_location_id: Optional[int] = Field(None, gt=0)
    client_nom: str = Field(..., min_length=2, max_length=100, pattern=NOM_PERSONNE_REGEX)
    client_telephone: str = Field(..., pattern=PHONE_REGEX)
    client_email: Optional[str] = Field(None, pattern=EMAIL_REGEX, max_length=200)
    date_debut: date
    notes: Optional[str] = Field(None, max_length=1000)
    itinerary_distance_km: Optional[float] = Field(None, ge=0, le=100000)
    itinerary_start_name: Optional[str] = Field(None, max_length=250)
    itinerary_end_name: Optional[str] = Field(None, max_length=250)
    itinerary_waypoints: Optional[str] = Field(None, max_length=5000)

    @field_validator("date_debut")
    @classmethod
    def _future_or_today(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("La date de départ ne peut pas être dans le passé.")
        return v

    @field_validator("client_email", mode="before")
    @classmethod
    def _empty_email_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v

    @classmethod
    def as_form(
        cls,
        type_location_id: Optional[int] = Form(None),
        client_nom: str = Form(...),
        client_telephone: str = Form(...),
        client_email: Optional[str] = Form(None),
        date_debut: str = Form(...),
        notes: Optional[str] = Form(None),
        itinerary_distance_km: Optional[float] = Form(None),
        itinerary_start_name: Optional[str] = Form(None),
        itinerary_end_name: Optional[str] = Form(None),
        itinerary_waypoints: Optional[str] = Form(None),
    ) -> "LocationForm":
        return cls(
            type_location_id=type_location_id,
            client_nom=client_nom,
            client_telephone=client_telephone,
            client_email=client_email,
            date_debut=date_debut,
            notes=notes,
            itinerary_distance_km=itinerary_distance_km,
            itinerary_start_name=itinerary_start_name,
            itinerary_end_name=itinerary_end_name,
            itinerary_waypoints=itinerary_waypoints,
        )


class AdminLoginForm(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)

    @classmethod
    def as_form(
        cls,
        username: str = Form(...),
        password: str = Form(...),
    ) -> "AdminLoginForm":
        return cls(username=username, password=password)


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
