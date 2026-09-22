import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.voitures import service as car_service
from app.shared.deps import get_db
from app.templating import templates


router = APIRouter(prefix="", tags=["client-pages"])


def _parse_date(value: str | None) -> datetime.date | None:
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    depart = _parse_date(request.query_params.get("depart"))
    retour = _parse_date(request.query_params.get("retour"))
    voitures_dispo = await car_service.get_voitures_avec_disponibilite(
        db, depart, retour, limit=6
    )
    return templates.TemplateResponse("index.html", {
        "request": request,
        "voitures_dispo": voitures_dispo,
        "depart": depart.isoformat() if depart else "",
        "retour": retour.isoformat() if retour else "",
    })


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt(request: Request):
    base = str(request.base_url).rstrip("/")
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /api/\n"
        f"\nSitemap: {base}/sitemap.xml\n"
    )


@router.get("/sitemap.xml")
async def sitemap_xml(request: Request, db: AsyncSession = Depends(get_db)):
    base = str(request.base_url).rstrip("/")
    voitures = await car_service.get_available_voitures(db)

    urls = [f"{base}/", f"{base}/voitures"]
    for v in voitures:
        urls.append(f"{base}/voitures/{v.slug}")
        urls.append(f"{base}/voitures/{v.slug}/itineraire")

    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        body.append(f"  <url><loc>{url}</loc></url>")
    body.append("</urlset>")

    return Response(content="\n".join(body), media_type="application/xml")
