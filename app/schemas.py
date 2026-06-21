from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


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
