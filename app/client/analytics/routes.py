from fastapi import APIRouter, BackgroundTasks, Request, Response, status
from pydantic import BaseModel, Field

from app.client.analytics import service


ALLOWED_EVENTS = {"pwa_installed", "pwa_standalone_session"}


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class EventPayload(BaseModel):
    type: str = Field(..., max_length=40)


@router.post("/event", status_code=status.HTTP_204_NO_CONTENT)
async def collect_event(
    payload: EventPayload,
    request: Request,
    response: Response,
    background: BackgroundTasks,
):
    if payload.type not in ALLOWED_EVENTS:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    session_id = service.get_or_create_session_id(request, response)
    ctx = service.extraire_contexte(request)
    background.add_task(
        service.enregistrer_event_client,
        payload.type,
        session_id,
        ctx["referer_host"],
        ctx["hour_local"],
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
