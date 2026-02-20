import os
import shutil
import docker
import logging
import json
from typing import Dict
from core.config import settings

logger = logging.getLogger("ProvisioningAPI.Docker")

# Single source of truth for the Docker client — imported by main.py as well.
try:
    docker_client = docker.from_env()
    logger.info(json.dumps({"event": "docker_client_connected"}))
except Exception as e:
    logger.error(json.dumps({"event": "docker_client_failed", "error": str(e)}))
    docker_client = None


def render_env_file(tenant_dir: str, context: Dict) -> None:
    """Renders the .env file for a tenant from the provisioned credentials."""
    env_content = f"""# Auto-generated .env for tenant {context['TENANT_NAME']}
DOMAIN={context['DOMAIN']}
TENANT_NAME={context['TENANT_NAME']}
DB_HOST={context['DB_HOST']}
DB_PORT={context['DB_PORT']}
DB_NAME={context['DB_NAME']}
DB_USER={context['DB_USER']}
DB_PASSWORD={context['DB_PASSWORD']}
THEME={context['THEME']}
"""
    env_path = os.path.join(tenant_dir, ".env")
    with open(env_path, "w") as f:
        f.write(env_content)
    logger.info(json.dumps({"event": "env_file_written", "path": env_path}))


def copy_blueprint(tenant_name: str, theme: str) -> str:
    """
    Copies the default blueprint into a new per-tenant directory.
    Idempotent: overwrites if the tenant directory already exists.
    Raises FileNotFoundError if the blueprint source is missing — the stub
    auto-generator was removed to prevent corrupting a real blueprint.
    """
    blueprint_src = os.path.join(
        os.path.dirname(__file__), "..", "blueprints", "default"
    )
    blueprint_src = os.path.abspath(blueprint_src)
    tenant_dir = os.path.join(settings.TENANTS_DIR, tenant_name)

    # Guard: fail fast with a clear message if blueprint is missing
    if not os.path.isdir(blueprint_src):
        raise FileNotFoundError(
            f"Blueprint source directory not found: {blueprint_src}. "
            "Ensure api/blueprints/default/ exists and is mounted correctly."
        )

    # Idempotent copy — always start fresh for the tenant
    if os.path.exists(tenant_dir):
        logger.warning(json.dumps({
            "event": "tenant_dir_overwrite",
            "tenant": tenant_name,
            "path": tenant_dir,
        }))
        shutil.rmtree(tenant_dir)

    shutil.copytree(blueprint_src, tenant_dir)
    logger.info(json.dumps({
        "event": "blueprint_copied",
        "tenant": tenant_name,
        "src": blueprint_src,
        "dst": tenant_dir,
    }))
    return tenant_dir


def start_tenant_containers(tenant_name: str, theme: str, db_credentials: dict) -> bool:
    """
    Copies the blueprint, renders the .env, then runs `docker compose up -d`
    inside the tenant directory.

    Requires: docker CLI must be installed inside this container (see Dockerfile).
    The Docker socket must be bind-mounted at /var/run/docker.sock.
    """
    import subprocess

    tenant_dir = copy_blueprint(tenant_name, theme)

    context = {
        "TENANT_NAME": tenant_name,
        "DOMAIN": settings.DOMAIN,
        "THEME": theme,
        **db_credentials,
    }
    render_env_file(tenant_dir, context)

    logger.info(json.dumps({"event": "docker_compose_up", "tenant": tenant_name, "dir": tenant_dir}))

    try:
        result = subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=tenant_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,  # Prevent hanging indefinitely
        )
        logger.info(json.dumps({
            "event": "docker_compose_up_success",
            "tenant": tenant_name,
            "stdout": result.stdout.strip(),
        }))
        return True
    except FileNotFoundError:
        raise RuntimeError(
            "docker CLI not found inside the API container. "
            "Ensure the Dockerfile installs docker-ce-cli."
        )
    except subprocess.CalledProcessError as e:
        logger.error(json.dumps({
            "event": "docker_compose_up_failed",
            "tenant": tenant_name,
            "stderr": e.stderr,
        }))
        raise Exception(f"Failed to start Docker containers: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise Exception(f"docker compose up timed out for tenant: {tenant_name}")


def delete_tenant_containers(tenant_name: str) -> bool:
    """
    Runs `docker compose down -v` for the tenant then removes the tenant directory.
    """
    import subprocess

    tenant_dir = os.path.join(settings.TENANTS_DIR, tenant_name)

    if not os.path.exists(tenant_dir):
        logger.warning(json.dumps({
            "event": "tenant_dir_not_found",
            "tenant": tenant_name,
            "path": tenant_dir,
        }))
        return False

    logger.info(json.dumps({"event": "docker_compose_down", "tenant": tenant_name}))

    try:
        subprocess.run(
            ["docker", "compose", "down", "-v"],
            cwd=tenant_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        logger.info(json.dumps({"event": "docker_compose_down_success", "tenant": tenant_name}))
    except subprocess.CalledProcessError as e:
        logger.error(json.dumps({
            "event": "docker_compose_down_failed",
            "tenant": tenant_name,
            "stderr": e.stderr,
        }))
        raise Exception(f"Failed to take down Docker containers: {e.stderr}")

    shutil.rmtree(tenant_dir)
    logger.info(json.dumps({"event": "tenant_dir_removed", "path": tenant_dir}))
    return True
