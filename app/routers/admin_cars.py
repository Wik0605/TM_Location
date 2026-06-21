from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pathlib import Path
import uuid

from app.database import get_db
from app.services import admin_service
from app.routers.admin_auth import require_admin

UPLOAD_DIR = Path(__file__).parent.parent.parent / "static" / "uploads" / "voitures"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/admin", tags=["admin-cars"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/voitures", response_class=HTMLResponse)
async def admin_voitures(request: Request, db: AsyncSession = Depends(get_db)):
    redirect = require_admin(request)
    if redirect:
        return redirect
    voitures = await admin_service.get_all_voitures(db)
    return templates.TemplateResponse("admin/voitures.html", {
        "request": request,
        "voitures": voitures,
        "active": "voitures",
    })


@router.post("/voitures/create", response_class=HTMLResponse)
async def create_voiture(
    request: Request,
    nom: str = Form(...),
    places: int = Form(5),
    consommation_carburant: float = Form(8.0),
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    data = {
        "nom": nom,
        "places": places,
        "consommation_carburant": consommation_carburant,
        "is_available": True,
    }
    await admin_service.create_voiture(db, data)
    voitures = await admin_service.get_all_voitures(db)
    return templates.TemplateResponse("admin/partials/_voitures_grid.html", {
        "request": request,
        "voitures": voitures,
    })


@router.post("/voitures/{voiture_id}/delete", response_class=HTMLResponse)
async def delete_voiture(
    request: Request,
    voiture_id: int,
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    await admin_service.delete_voiture(db, voiture_id)
    voitures = await admin_service.get_all_voitures(db)
    return templates.TemplateResponse("admin/partials/_voitures_grid.html", {
        "request": request,
        "voitures": voitures,
    })


@router.post("/voitures/{voiture_id}/edit", response_class=HTMLResponse)
async def edit_voiture(
    request: Request,
    voiture_id: int,
    nom: Optional[str] = Form(None),
    places: Optional[int] = Form(None),
    consommation_carburant: Optional[float] = Form(None),
    is_available: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    data = {
        "nom": nom if nom else None,
        "places": places,
        "consommation_carburant": consommation_carburant,
        "is_available": is_available == "on" if is_available is not None else None,
    }
    data = {k: v for k, v in data.items() if v is not None}
    voiture = await admin_service.update_voiture(db, voiture_id, data)
    return templates.TemplateResponse("admin/partials/_voiture_card.html", {
        "request": request,
        "voiture": voiture,
        "success": True,
    })


@router.post("/voitures/{voiture_id}/images", response_class=HTMLResponse)
async def add_voiture_images(
    request: Request,
    voiture_id: int,
    files: List[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    upload_dir = UPLOAD_DIR / str(voiture_id)
    upload_dir.mkdir(exist_ok=True)

    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            continue
        ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        dest = upload_dir / filename
        dest.write_bytes(await file.read())
        url = f"/static/uploads/voitures/{voiture_id}/{filename}"
        await admin_service.add_voiture_image(db, voiture_id, url)

    voiture = await admin_service.get_voiture_by_id(db, voiture_id)
    return templates.TemplateResponse("admin/partials/_voiture_images.html", {
        "request": request,
        "voiture": voiture,
    })


@router.post("/voitures/{voiture_id}/images/{image_id}/delete", response_class=HTMLResponse)
async def delete_voiture_image(
    request: Request,
    voiture_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    await admin_service.delete_voiture_image(db, image_id)
    voiture = await admin_service.get_voiture_by_id(db, voiture_id)
    return templates.TemplateResponse("admin/partials/_voiture_images.html", {
        "request": request,
        "voiture": voiture,
    })


@router.post("/voitures/{voiture_id}/types/create", response_class=HTMLResponse)
async def add_type_location(
    request: Request,
    voiture_id: int,
    nom: str = Form(...),
    prix: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    await admin_service.add_type_location(db, voiture_id, nom, prix)
    voiture = await admin_service.get_voiture_by_id(db, voiture_id)
    return templates.TemplateResponse("admin/partials/_types_location_list.html", {
        "request": request,
        "voiture": voiture,
    })


@router.post("/voitures/{voiture_id}/types/{type_id}/delete", response_class=HTMLResponse)
async def delete_type_location(
    request: Request,
    voiture_id: int,
    type_id: int,
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    await admin_service.delete_type_location(db, type_id)
    voiture = await admin_service.get_voiture_by_id(db, voiture_id)
    return templates.TemplateResponse("admin/partials/_types_location_list.html", {
        "request": request,
        "voiture": voiture,
    })
