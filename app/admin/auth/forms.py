from fastapi import Form
from pydantic import BaseModel, Field


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
