import datetime

from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PrefixLoader, select_autoescape

from app.csrf import csrf_input, get_or_create_csrf_token


def _to_webp(url: str) -> str:
    if not url:
        return url
    for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
        if url.endswith(ext):
            return url[: -len(ext)] + ".webp"
    return url


_client_features = PrefixLoader({
    "voitures": FileSystemLoader("app/client/voitures/templates"),
    "reservations": FileSystemLoader("app/client/reservations/templates"),
    "pages": FileSystemLoader("app/client/pages/templates"),
})

_admin_features = PrefixLoader({
    "voitures": FileSystemLoader("app/admin/voitures/templates"),
    "reservations": FileSystemLoader("app/admin/reservations/templates"),
    "stats": FileSystemLoader("app/admin/stats/templates"),
    "auth": FileSystemLoader("app/admin/auth/templates"),
})

_loader = ChoiceLoader([
    FileSystemLoader("app/templates"),
    PrefixLoader({"client": _client_features, "admin": _admin_features}),
])

_env = Environment(loader=_loader, autoescape=select_autoescape(["html", "xml"]))

templates = Jinja2Templates(env=_env)
templates.env.globals["csrf_input"] = csrf_input
templates.env.globals["csrf_token"] = get_or_create_csrf_token
templates.env.filters["current_year"] = lambda: datetime.datetime.now().year
templates.env.filters["to_webp"] = _to_webp
