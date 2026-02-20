import os
import shutil
import json
import logging
import subprocess
from abc import ABC, abstractmethod
from typing import Dict
from core.config import settings

logger = logging.getLogger("ProvisioningAPI.Provisioner")

class Provisioner(ABC):
    """
    Abstract interface for tenant provisioning.
    Allows the platform to run on Local Docker, Kubernetes, ECS, etc.
    """
    @abstractmethod
    def get_tenant_status(self) -> list[dict]:
        pass

    @abstractmethod
    def start_tenant(self, tenant_name: str, theme: str, db_credentials: dict) -> bool:
        pass

    @abstractmethod
    def delete_tenant(self, tenant_name: str) -> bool:
        pass

class LocalDockerProvisioner(Provisioner):
    """
    Provisions tenants by writing a .env file and running `docker compose up`.
    Assumes the API container has access to the host's Docker socket.
    """
    def __init__(self):
        try:
            import docker
            self.client = docker.from_env()
            logger.info(json.dumps({"event": "local_docker_provisioner_init", "status": "success"}))
        except Exception as e:
            logger.error(json.dumps({"event": "local_docker_provisioner_init_failed", "error": str(e)}))
            self.client = None

    def get_tenant_status(self) -> list[dict]:
        if not self.client:
            raise RuntimeError("Docker client unavailable")
        
        # We list medusa containers as the canonical source of truth for active tenants.
        containers = self.client.containers.list(filters={"name": "medusa-"})
        return [
            {"id": c.short_id, "name": c.name, "status": c.status}
            for c in containers
        ]

    def start_tenant(self, tenant_name: str, theme: str, db_credentials: dict) -> bool:
        tenant_dir = self._copy_blueprint(tenant_name)
        self._render_env_file(tenant_dir, tenant_name, theme, db_credentials)
        
        logger.info(json.dumps({"event": "docker_compose_up", "tenant": tenant_name, "dir": tenant_dir}))
        try:
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=tenant_dir,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            logger.info(json.dumps({
                "event": "docker_compose_up_success",
                "tenant": tenant_name,
                "stdout": result.stdout.strip(),
            }))
            return True
        except subprocess.CalledProcessError as e:
            logger.error(json.dumps({
                "event": "docker_compose_up_failed",
                "tenant": tenant_name,
                "stderr": e.stderr,
            }))
            raise Exception(f"Failed to start Docker containers: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise Exception(f"docker compose up timed out for tenant: {tenant_name}")

    def delete_tenant(self, tenant_name: str) -> bool:
        tenant_dir = os.path.join(settings.TENANTS_DIR, tenant_name)

        if not os.path.exists(tenant_dir):
            logger.warning(json.dumps({"event": "tenant_dir_not_found", "tenant": tenant_name, "path": tenant_dir}))
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
            logger.error(json.dumps({"event": "docker_compose_down_failed", "tenant": tenant_name, "stderr": e.stderr}))
            raise Exception(f"Failed to take down Docker containers: {e.stderr}")

        shutil.rmtree(tenant_dir)
        logger.info(json.dumps({"event": "tenant_dir_removed", "path": tenant_dir}))
        return True

    def _copy_blueprint(self, tenant_name: str) -> str:
        # Move one directory up since we are in `services/control-plane/services/`
        blueprint_src = os.path.join(os.path.dirname(__file__), "..", "blueprints", "default")
        blueprint_src = os.path.abspath(blueprint_src)
        tenant_dir = os.path.join(settings.TENANTS_DIR, tenant_name)

        if not os.path.isdir(blueprint_src):
            raise FileNotFoundError(f"Blueprint source directory not found: {blueprint_src}")

        if os.path.exists(tenant_dir):
            shutil.rmtree(tenant_dir)

        shutil.copytree(blueprint_src, tenant_dir)
        return tenant_dir

    def _render_env_file(self, tenant_dir: str, tenant_name: str, theme: str, db_credentials: dict) -> None:
        context = {
            "TENANT_NAME": tenant_name,
            "DOMAIN": settings.DOMAIN,
            "THEME": theme,
            **db_credentials,
        }
        env_content = f"""# Auto-generated .env for tenant {context['TENANT_NAME']}
DOMAIN={context['DOMAIN']}
TENANT_NAME={context['TENANT_NAME']}
DB_HOST={context['DB_HOST']}
DB_PORT={context['DB_PORT']}
DB_NAME={context['DB_NAME']}
DB_USER={context['DB_USER']}
DB_PASSWORD={context['DB_PASSWORD']}
THEME={context['THEME']}

# Medusa specific variables
DATABASE_URL=postgres://{context['DB_USER']}:{context['DB_PASSWORD']}@{context['DB_HOST']}:{context['DB_PORT']}/{context['DB_NAME']}?sslmode=disable
REDIS_URL=redis://redis-{context['TENANT_NAME']}:6379
STORE_CORS=http://{context['TENANT_NAME']}.{context['DOMAIN']}
ADMIN_CORS=http://admin.{context['TENANT_NAME']}.{context['DOMAIN']}
AUTH_CORS=http://admin.{context['TENANT_NAME']}.{context['DOMAIN']},http://{context['TENANT_NAME']}.{context['DOMAIN']}
JWT_SECRET=supersecret
COOKIE_SECRET=supersecret
"""
        env_path = os.path.join(tenant_dir, ".env")
        with open(env_path, "w") as f:
            f.write(env_content)
        logger.info(json.dumps({"event": "env_file_written", "path": env_path}))


class KubernetesProvisioner(Provisioner):
    """
    Provisions tenants by submitting native Kubernetes manifests to the K8s API.
    Placeholder for Phase 7 execution.
    """
    def get_tenant_status(self) -> list[dict]:
        # Implementation via kubernetes python client would list namespaces/deployments
        return []

    def start_tenant(self, tenant_name: str, theme: str, db_credentials: dict) -> bool:
        logger.info(json.dumps({"event": "k8s_provisioning_started", "tenant": tenant_name}))
        # Implementation would use kubernetes python client to create Namespace, Deployment, Service, Ingress
        return True

    def delete_tenant(self, tenant_name: str) -> bool:
        logger.info(json.dumps({"event": "k8s_deprovisioning_started", "tenant": tenant_name}))
        # Implementation would use kubernetes python client to delete Namespace
        return True

# Initialize the active provisioner based on environment configuration
# Defaulting to LocalDockerProvisioner for now, to be switched via env var later.
active_provisioner = LocalDockerProvisioner()
