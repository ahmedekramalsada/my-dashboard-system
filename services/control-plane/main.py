from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.config import settings
import logging
import json
from services.db import provision_tenant_db, delete_tenant_db
from services.provisioner import active_provisioner

# ------------------------------------------------------------------
# JSON Structured Logging — production-ready for log aggregators
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
# App
# ------------------------------------------------------------------
app = FastAPI(title="SaaS Provisioning Engine", version="1.0.0")

# Fix: CORS middleware so the dashboard HTML can call the API from the browser.
# In production, lock 'allow_origins' down to your specific admin domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------
class TenantCreate(BaseModel):
    tenant_name: str
    theme: str

class TenantDelete(BaseModel):
    tenant_name: str

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """Liveness probe — also used by the dashboard badge."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/create-store")
async def create_store(tenant_config: TenantCreate):
    logger.info(json.dumps({
        "event": "create_store_requested",
        "tenant": tenant_config.tenant_name,
        "theme": tenant_config.theme,
    }))

    try:
        # Step 1 — Provision isolated PostgreSQL database + role
        logger.info(json.dumps({"event": "provisioning_db", "tenant": tenant_config.tenant_name}))
        db_creds = await provision_tenant_db(tenant_config.tenant_name)

        # Step 2 — Use Provisioner Adapter to spin up containers
        logger.info(json.dumps({"event": "starting_containers", "tenant": tenant_config.tenant_name}))
        active_provisioner.start_tenant(
            tenant_name=tenant_config.tenant_name,
            theme=tenant_config.theme,
            db_credentials=db_creds,
        )

        return {
            "status": "success",
            "message": f"Store '{tenant_config.tenant_name}' creation complete.",
            "subdomains": [
                f"{tenant_config.tenant_name}.{settings.DOMAIN}",
                f"admin.{tenant_config.tenant_name}.{settings.DOMAIN}",
            ],
        }
    except Exception as e:
        logger.error(json.dumps({"event": "create_store_failed", "tenant": tenant_config.tenant_name, "error": str(e)}))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stores-status")
async def stores_status():
    """Returns all running tenant containers grouped by tenant."""
    try:
        status = active_provisioner.get_tenant_status()
        return {"running_containers": status}
    except Exception as e:
        logger.error(json.dumps({"event": "get_tenant_status_failed", "error": str(e)}))
        raise HTTPException(status_code=503, detail="Provisioning orchestrator unavailable")


@app.post("/delete-store")
async def delete_store(tenant_config: TenantDelete):
    logger.info(json.dumps({"event": "delete_store_requested", "tenant": tenant_config.tenant_name}))

    try:
        # Step 1 — Stop and remove orchestrator containers
        logger.info(json.dumps({"event": "stopping_containers", "tenant": tenant_config.tenant_name}))
        active_provisioner.delete_tenant(tenant_config.tenant_name)

        # Step 2 — Drop tenant database + role
        logger.info(json.dumps({"event": "deleting_db", "tenant": tenant_config.tenant_name}))
        await delete_tenant_db(tenant_config.tenant_name)

        return {
            "status": "success",
            "message": f"Store '{tenant_config.tenant_name}' completely removed.",
        }
    except Exception as e:
        logger.error(json.dumps({"event": "delete_store_failed", "tenant": tenant_config.tenant_name, "error": str(e)}))
        raise HTTPException(status_code=500, detail=str(e))
