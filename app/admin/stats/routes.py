import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.stats import service
from app.shared.deps import get_db
from app.shared.security import require_admin
from app.templating import templates


router = APIRouter(
    prefix="/admin",
    tags=["admin-stats"],
    dependencies=[Depends(require_admin)],
)


@router.get("/stats", response_class=HTMLResponse)
async def admin_stats(request: Request, db: AsyncSession = Depends(get_db)):
    overview = await service.get_overview(db)
    daily = await service.get_daily_series(db, days=30)
    top_depart = await service.get_top_zones(db, "depart")
    top_arrivee = await service.get_top_zones(db, "arrivee")
    hours = await service.get_hour_distribution(db)
    referers = await service.get_top_referers(db)
    types_breakdown = await service.get_types_location_breakdown(db)
    trajets = await service.get_recent_trajets(db)

    return templates.TemplateResponse("admin/stats/stats.html", {
        "request": request,
        "overview": overview,
        "daily": daily,
        "top_depart": top_depart,
        "top_arrivee": top_arrivee,
        "hours": hours,
        "referers": referers,
        "types_breakdown": types_breakdown,
        "trajets_json": json.dumps(trajets),
    })
