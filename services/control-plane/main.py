from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from core.config import settings
import logging
import json
import re
import secrets
import threading
from services.db import (
    provision_tenant_db,
    delete_tenant_db,
    ensure_tenant_registry,
    register_tenant,
    deregister_tenant,
    list_tenants,
    get_pool,
    close_pool,
)
from services.provisioner import active_provisioner

# ─────────────────────────────────────────────────────────────────────────────
# Structured JSON Logging
# ─────────────────────────────────────────────────────────────────────────────
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger("ProvisioningAPI")

# ─────────────────────────────────────────────────────────────────────────────
# Rate Limiter
# ─────────────────────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ─────────────────────────────────────────────────────────────────────────────
# API Key Security
# ─────────────────────────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def require_api_key(api_key: str = Security(api_key_header)):
    """Dependency — protect write endpoints with an API key."""
    if not settings.API_KEY:
        # No key configured → warn but allow (dev mode)
        logger.warning("API_KEY not set — endpoint is unprotected!")
        return True
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing X-API-Key header")
    return True

# ─────────────────────────────────────────────────────────────────────────────
# Lifespan — startup / shutdown
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Startup — initialising DB pool and tenant registry...")
    await get_pool()               # warm up the connection pool
    await ensure_tenant_registry() # create tenants table if missing
    logger.info("Startup complete.")
    yield
    logger.info("Shutdown — closing DB pool...")
    await close_pool()

# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SaaS Provisioning Engine",
    version="3.0.0",
    lifespan=lifespan,
    docs_url=None,   # Disable Swagger UI in production
    redoc_url=None,  # Disable ReDoc in production
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────
TENANT_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,28}[a-z0-9]$")

class TenantCreate(BaseModel):
    tenant_name: str
    theme: str = "fashion"

    @field_validator("tenant_name")
    @classmethod
    def validate_tenant_name(cls, v: str) -> str:
        v = v.strip().lower()
        if not TENANT_NAME_RE.match(v):
            raise ValueError(
                "tenant_name must be 3-30 lowercase alphanumeric characters or hyphens, "
                "and cannot start or end with a hyphen."
            )
        return v

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        allowed = {"fashion", "electronics", "minimal", "default"}
        if v not in allowed:
            raise ValueError(f"theme must be one of: {', '.join(allowed)}")
        return v

class TenantDelete(BaseModel):
    tenant_name: str

class SeedAdminRequest(BaseModel):
    email: str | None = None
    password: str | None = None

# ─────────────────────────────────────────────────────────────────────────────
# Routes — Public (no auth)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "3.0.0"}


@app.get("/tenants")
async def get_tenants():
    """Returns all provisioned tenants from the persistent registry."""
    try:
        tenants = await list_tenants()
        return {"tenants": tenants}
    except Exception as e:
        logger.error(json.dumps({"event": "list_tenants_failed", "error": str(e)}))
        raise HTTPException(status_code=503, detail="Could not retrieve tenant registry")


@app.get("/stores-status")
async def stores_status():
    """Returns live Docker container status for all tenant Medusa containers."""
    try:
        status = active_provisioner.get_tenant_status()
        return {"running_containers": status}
    except Exception as e:
        logger.error(json.dumps({"event": "get_tenant_status_failed", "error": str(e)}))
        raise HTTPException(status_code=503, detail="Provisioning orchestrator unavailable")


# ─────────────────────────────────────────────────────────────────────────────
# Routes — Protected (require API key)
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/create-store", dependencies=[Depends(require_api_key)])
@limiter.limit("5/minute")
async def create_store(request: Request, tenant_config: TenantCreate):
    tenant_name = tenant_config.tenant_name
    theme = tenant_config.theme
    logger.info(json.dumps({"event": "create_store_requested", "tenant": tenant_name, "theme": theme}))

    try:
        db_creds = await provision_tenant_db(tenant_name)

        active_provisioner.start_tenant(
            tenant_name=tenant_name,
            theme=theme,
            db_credentials=db_creds,
        )

        admin_email = f"admin@{tenant_name}.com"
        admin_password = secrets.token_urlsafe(14)

        await register_tenant(
            tenant_name=tenant_name,
            theme=theme,
            admin_email=admin_email,
            db_name=db_creds["DB_NAME"],
            db_user=db_creds["DB_USER"],
        )

        def seed_in_background():
            try:
                active_provisioner.seed_admin_user(tenant_name, admin_email, admin_password)
                logger.info(json.dumps({"event": "auto_seed_complete", "tenant": tenant_name}))
            except Exception as seed_err:
                logger.error(json.dumps({"event": "auto_seed_failed", "tenant": tenant_name, "error": str(seed_err)}))

        threading.Thread(target=seed_in_background, daemon=True).start()

        return {
            "status": "success",
            "message": f"Store '{tenant_name}' provisioned. Admin seeding in background (~60s).",
            "subdomains": {
                "storefront": f"http://{tenant_name}.{settings.DOMAIN}",
                "admin": f"http://admin.{tenant_name}.{settings.DOMAIN}/app",
            },
            "credentials": {
                "email": admin_email,
                "password": admin_password,
                "note": "Admin ready after migrations (~60 seconds)",
            },
        }
    except Exception as e:
        logger.error(json.dumps({"event": "create_store_failed", "tenant": tenant_name, "error": str(e)}))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/delete-store", dependencies=[Depends(require_api_key)])
async def delete_store(tenant_config: TenantDelete):
    tenant_name = tenant_config.tenant_name
    logger.info(json.dumps({"event": "delete_store_requested", "tenant": tenant_name}))
    try:
        active_provisioner.delete_tenant(tenant_name)
        await delete_tenant_db(tenant_name)
        await deregister_tenant(tenant_name)
        return {"status": "success", "message": f"Store '{tenant_name}' completely removed."}
    except Exception as e:
        logger.error(json.dumps({"event": "delete_store_failed", "tenant": tenant_name, "error": str(e)}))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tenants/{tenant_name}/seed-admin", dependencies=[Depends(require_api_key)])
async def seed_admin(tenant_name: str, body: SeedAdminRequest):
    """Create or re-create an admin user for a tenant on demand."""
    email = body.email or f"admin@{tenant_name}.com"
    password = body.password or secrets.token_urlsafe(14)
    try:
        active_provisioner.seed_admin_user(tenant_name, email, password)
        return {"status": "success", "email": email, "password": password}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tenants/{tenant_name}/suspend", dependencies=[Depends(require_api_key)])
async def suspend_tenant(tenant_name: str):
    """Stop tenant containers without removing data."""
    try:
        active_provisioner.suspend_tenant(tenant_name)
        return {"status": "success", "message": f"Tenant '{tenant_name}' suspended."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tenants/{tenant_name}/resume", dependencies=[Depends(require_api_key)])
async def resume_tenant(tenant_name: str):
    """Restart previously suspended tenant containers."""
    try:
        active_provisioner.resume_tenant(tenant_name)
        return {"status": "success", "message": f"Tenant '{tenant_name}' resumed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tenants/{tenant_name}/logs", dependencies=[Depends(require_api_key)])
async def get_tenant_logs(tenant_name: str, lines: int = 100):
    """Return last N lines of the Medusa container logs."""
    try:
        logs = active_provisioner.get_tenant_logs(tenant_name, lines=lines)
        return {"tenant": tenant_name, "logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
