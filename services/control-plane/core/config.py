from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "SaaS Provisioning API"

    # Domain
    DOMAIN: str = Field("127.0.0.1.nip.io", env="DOMAIN")

    # CORS — raw string from env. Use comma-separated list in production.
    # Example: CORS_ORIGINS=http://superadmin.myplatform.com
    CORS_ORIGINS_RAW: str = Field("*", env="CORS_ORIGINS")

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Split comma-separated origins from CORS_ORIGINS env var."""
        return [o.strip() for o in self.CORS_ORIGINS_RAW.split(",") if o.strip()]

    # Shared Postgres root credentials (used to provision per-tenant DBs)
    DB_HOST: str = os.getenv("DB_HOST", "shared-postgres")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "defaultdb")

    # Tenant data directory (inside the container)
    TENANTS_DIR: str = os.getenv("TENANTS_DIR", "/opt/saas/tenants")

    # API Key — required as X-API-Key header on all write endpoints
    # Generate: openssl rand -hex 32
    API_KEY: str = os.getenv("API_KEY", "")

    @field_validator("API_KEY")
    @classmethod
    def api_key_warn_if_missing(cls, v: str) -> str:
        if not v or v.startswith("CHANGE_ME"):
            import logging
            logging.getLogger("ProvisioningAPI").warning(
                "API_KEY is not set — write endpoints are UNPROTECTED. Set API_KEY in .env."
            )
        return v

    @field_validator("DB_PASSWORD")
    @classmethod
    def db_password_required(cls, v: str) -> str:
        if not v or v.startswith("CHANGE_ME"):
            raise ValueError("DB_PASSWORD must be set in .env before starting the platform.")
        return v

    class Config:
        env_file = ".env"


settings = Settings()
