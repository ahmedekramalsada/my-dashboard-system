from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import docker
import logging

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

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/create-store")
async def create_store(tenant_config: TenantCreate):
    logger.info(f"Received request to create store: {tenant_config.tenant_name} with theme {tenant_config.theme}")
    
    # TODO: Implement the underlying provisioning logic (Phase 2):
    # 1. Create a logical schema in PostgreSQL
    # 2. Render templates and start MedusaJS docker container
    # 3. Start Next.js container linked to MedusaJS
    # 4. Attach Dynamic Traefik Labels to route domain properly
    
    return {"message": f"Store {tenant_config.tenant_name} creation initiated."}

@app.get("/stores-status")
async def stores_status():
    # Example to fetch running containers
    containers = docker_client.containers.list()
    status = [{"id": c.short_id, "name": c.name, "status": c.status} for c in containers]
    return {"running_containers": status}
