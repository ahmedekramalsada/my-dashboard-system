from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from core.config import settings
import docker
import logging
from services.db import provision_tenant_db, delete_tenant_db
from services.docker_manager import start_tenant_containers, delete_tenant_containers, docker_client

# Best Practice: Setup JSON Logging for production scale observability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' # You can switch this to a python-json-logger later
)
logger = logging.getLogger("ProvisioningAPI")

app = FastAPI(title="SaaS Provisioning Engine")

# Initialize docker client using the environment socket
try:
    docker_client = docker.from_env()
except Exception as e:
    logger.error(f"Failed to connect to Docker daemon: {str(e)}")
    # Note: the app will fail here in local environments without Docker running

class TenantCreate(BaseModel):
    tenant_name: str
    theme: str

class TenantDelete(BaseModel):
    tenant_name: str

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/create-store")
async def create_store(tenant_config: TenantCreate):
    logger.info(f"Received request to create store: {tenant_config.tenant_name} with theme {tenant_config.theme}")
    
    try:
        # 1. Create a logical schema in PostgreSQL
        logger.info("Step 1/2: Provisioning isolated Database")
        db_creds = await provision_tenant_db(tenant_config.tenant_name)
        
        # 2. Render templates and start Docker containers
        logger.info("Step 2/2: Starting Docker Containers")
        start_tenant_containers(
            tenant_name=tenant_config.tenant_name, 
            theme=tenant_config.theme, 
            db_credentials=db_creds
        )
        
        return {
            "status": "success",
            "message": f"Store {tenant_config.tenant_name} creation complete.",
            "subdomains": [
                f"{tenant_config.tenant_name}.{settings.DOMAIN}",
                f"admin.{tenant_config.tenant_name}.{settings.DOMAIN}"
            ]
        }
    except Exception as e:
        logger.error(f"Provisioning failed for {tenant_config.tenant_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stores-status")
async def stores_status():
    # Example to fetch running containers
    if docker_client:
        containers = docker_client.containers.list(filters={"name": "medusa|storefront"})
        status = [{"id": c.short_id, "name": c.name, "status": c.status} for c in containers]
        return {"running_containers": status}
    return {"error": "Docker client not available"}

@app.post("/delete-store")
async def delete_store(tenant_config: TenantDelete):
    logger.info(f"Received request to delete store: {tenant_config.tenant_name}")
    
    try:
        # 1. Stop and remove docker containers
        logger.info("Step 1/2: Stopping Docker Containers")
        delete_tenant_containers(tenant_config.tenant_name)
        
        # 2. Drop logical schema in PostgreSQL
        logger.info("Step 2/2: Deleting isolated Database")
        await delete_tenant_db(tenant_config.tenant_name)
        
        return {
            "status": "success",
            "message": f"Store {tenant_config.tenant_name} completely removed."
        }
    except Exception as e:
        logger.error(f"Deletion failed for {tenant_config.tenant_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

