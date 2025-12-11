from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "devtask-87719"
    secret_key: str
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"
    database_url: str = "sqlite:///./devtask.db"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> "Settings":
    # Use lru_cache to avoid issues with BaseSettings in some environments
    return Settings()
