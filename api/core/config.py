from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # Base configuration
    PROJECT_NAME: str = "SaaS Provisioning API"
    DOMAIN: str = os.getenv("DOMAIN", "example.com")
    
    # Shared Postgres Database Configuration (For provisioning)
    # The API needs admin credentials to the shared DB to create tenant databases and roles
    DB_HOST: str = os.getenv("DB_HOST", "shared-postgres")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "supersecretpassword123")
    DB_NAME: str = os.getenv("DB_NAME", "defaultdb")
    
    # Path inside the container where tenant data/configs will be stored
    TENANTS_DIR: str = os.getenv("TENANTS_DIR", "/opt/saas/tenants")

    class Config:
        env_file = ".env"

settings = Settings()
