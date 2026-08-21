from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://clinicbrain:clinicbrain@localhost:5433/clinicbrain"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "devsecret-change-me"
    jwt_expires_minutes: int = 720
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "clinicbrain"
    s3_secret_key: str = "clinicbrain-secret"
    s3_bucket: str = "clinicbrain-docs"
    extraction_provider: str = "gpt"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
