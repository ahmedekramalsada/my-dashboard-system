import os
import shutil
import docker
import logging
from typing import Dict
from jinja2 import Template
from core.config import settings

logger = logging.getLogger("ProvisioningAPI.Docker")

try:
    docker_client = docker.from_env()
except Exception as e:
    logger.error(f"Failed to connect to Docker daemon: {str(e)}")
    docker_client = None

def render_env_file(tenant_dir: str, context: Dict):
    """
    Renders the .env file for the tenant from a template.
    """
    env_content = f"""
# Auto-generated .env for tenant {context['TENANT_NAME']}
DOMAIN={context['DOMAIN']}
DB_HOST={context['DB_HOST']}
DB_PORT={context['DB_PORT']}
DB_NAME={context['DB_NAME']}
DB_USER={context['DB_USER']}
DB_PASSWORD={context['DB_PASSWORD']}
THEME={context['THEME']}
"""
    with open(os.path.join(tenant_dir, '.env'), 'w') as f:
        f.write(env_content.strip())

def copy_blueprint(tenant_name: str, theme: str) -> str:
    """
    Copies the blueprint (docker-compose template) to a new tenant directory.
    To be fully idempotent, it overwrites if it already exists.
    """
    # Assuming blueprints are injected or built into the api container at /app/blueprints
    blueprint_src = f"/app/blueprints/{theme}" 
    tenant_dir = os.path.join(settings.TENANTS_DIR, tenant_name)
    
    # In a real scenario, make sure the blueprint exists
    if not os.path.exists(blueprint_src):
        # Fallback to a default or raise an error
        # Creating a stub for now so the logic is complete
        os.makedirs(blueprint_src, exist_ok=True)
        with open(os.path.join(blueprint_src, 'docker-compose.yml'), 'w') as f:
            f.write(f"""
services:
  medusa:
    image: medusajs/medusa:latest
    container_name: medusa-{tenant_name}
    env_file: .env
    restart: always
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.admin-{tenant_name}.rule=Host(`admin.{tenant_name}.${{DOMAIN}}`)"
  storefront:
    image: my-nextjs-storefront:{theme}
    container_name: storefront-{tenant_name}
    env_file: .env
    restart: always
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.store-{tenant_name}.rule=Host(`{tenant_name}.${{DOMAIN}}`)"
            """.strip())
    
    if not os.path.exists(tenant_dir):
        logger.info(f"Copying blueprints for {tenant_name} from {blueprint_src}")
        shutil.copytree(blueprint_src, tenant_dir)
    else:
        logger.warning(f"Tenant directory {tenant_dir} already exists. Overwriting blueprints.")
        shutil.rmtree(tenant_dir)
        shutil.copytree(blueprint_src, tenant_dir)
        
    return tenant_dir

def start_tenant_containers(tenant_name: str, theme: str, db_credentials: dict):
    """
    Orchestrates the docker compose up process for a new tenant via the Docker python sdk.
    Since docker-compose is technically an external binary, we either shell out or use the newer compose API.
    A reliable, production-ready way in python is using python subprocess to call `docker compose up -d`
    in the tenant directory.
    """
    import subprocess
    
    tenant_dir = copy_blueprint(tenant_name, theme)
    
    context = {
        "TENANT_NAME": tenant_name,
        "DOMAIN": settings.DOMAIN,
        "THEME": theme,
        **db_credentials
    }
    
    render_env_file(tenant_dir, context)
    
    logger.info(f"Starting docker containers for {tenant_name}...")
    
    # Using subprocess to run docker compose
    # The API container itself must have the docker cli installed and docker.sock mounted (Docker-in-Docker pattern or sibling container)
    try:
        result = subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=tenant_dir,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Containers started for {tenant_name}. Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start containers for {tenant_name}. Error: {e.stderr}")
        raise Exception(f"Failed to start Docker containers: {e.stderr}")

def delete_tenant_containers(tenant_name: str):
    """
    Spins down tenant containers and removes the tenant directory.
    """
    import subprocess
    tenant_dir = os.path.join(settings.TENANTS_DIR, tenant_name)
    
    if os.path.exists(tenant_dir):
        logger.info(f"Taking down docker containers for {tenant_name}...")
        try:
            # -v removes associated anonymous volumes
            subprocess.run(
                ["docker", "compose", "down", "-v"],
                cwd=tenant_dir,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Containers stopped and removed for {tenant_name}.")
            
            logger.info(f"Removing tenant files...")
            shutil.rmtree(tenant_dir)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop/remove containers for {tenant_name}. Error: {e.stderr}")
            raise Exception(f"Failed to take down Docker containers: {e.stderr}")
    else:
        logger.warning(f"Tenant directory {tenant_dir} not found. Skipping docker take down.")
        return False

