from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    picture: str | None = None


class UserFull(UserLite):
    email: str


class UserAdmin(UserFull):
    google_id: str | None = None
    facebook_id: str | None = None
    created_at: datetime
