from pydantic_settings import BaseSettings

INSECURE_DEFAULTS = {"changeme", "admin", ""}


class Settings(BaseSettings):
    secret_key: str = "changeme"
    admin_username: str = "admin"
    admin_password: str = "admin"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    environment: str = "development"
    allowed_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    def assert_production_ready(self) -> None:
        if not self.is_production:
            return
        problems = []
        if self.secret_key in INSECURE_DEFAULTS or len(self.secret_key) < 32:
            problems.append("SECRET_KEY doit etre defini et faire au moins 32 caracteres")
        if self.admin_password in INSECURE_DEFAULTS or len(self.admin_password) < 12:
            problems.append("ADMIN_PASSWORD doit etre defini et faire au moins 12 caracteres")
        if self.admin_username in INSECURE_DEFAULTS:
            problems.append("ADMIN_USERNAME doit etre defini (pas 'admin')")
        if problems:
            raise RuntimeError(
                "Configuration de production non securisee:\n  - "
                + "\n  - ".join(problems)
            )

    class Config:
        env_file = ".env"


settings = Settings()
settings.assert_production_ready()
