from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str = "changeme"
    admin_username: str = "admin"
    admin_password: str = "admin"
    google_client_id: str = ""
    google_client_secret: str = ""
    environment: str = "development"
    allowed_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
