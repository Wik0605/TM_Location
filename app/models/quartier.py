from typing import Optional
from uuid import UUID
from sqlalchemy import Column, Text, Boolean, Integer
from sqlalchemy import func
from geoalchemy2 import Geometry
from sqlmodel import SQLModel, Field

from app.utils.ids import new_uuid7


class Quartier(SQLModel, table=True):
    __tablename__ = "quartiers"

    id: Optional[UUID] = Field(default_factory=new_uuid7, primary_key=True)
    osm_id: Optional[int] = Field(default=None, sa_column=Column(Integer, unique=True))
    nom: str = Field(sa_column=Column(Text, nullable=False))
    nom_court: str = Field(sa_column=Column(Text, nullable=False))
    type: str = Field(sa_column=Column(Text, nullable=False))
    actif: bool = Field(default=True, sa_column=Column(Boolean, nullable=False))
    geom: Optional[str] = Field(default=None, sa_column=Column(Geometry("MULTIPOLYGON", srid=4326)))
