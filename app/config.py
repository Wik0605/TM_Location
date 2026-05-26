from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str = "changeme"
    admin_username: str = "admin"
    admin_password: str = "admin"

    class Config:
        env_file = ".env"


settings = Settings()
