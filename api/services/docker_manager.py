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


THEME_CONFIG = {
    "fashion": {
        "title": "Fashion & Apparel Store",
        "emoji": "👗",
        "color": "#ec4899",
        "gradient": "linear-gradient(135deg, #ec4899, #8b5cf6)",
        "description": "Discover the latest trends in fashion and style.",
    },
    "electronics": {
        "title": "Tech & Electronics Store",
        "emoji": "⚡",
        "color": "#3b82f6",
        "gradient": "linear-gradient(135deg, #3b82f6, #06b6d4)",
        "description": "Cutting-edge technology at your fingertips.",
    },
    "minimal": {
        "title": "Minimal Concept Store",
        "emoji": "🪴",
        "color": "#10b981",
        "gradient": "linear-gradient(135deg, #10b981, #6366f1)",
        "description": "Less is more. Curated essentials for modern living.",
    },
}

def generate_storefront_html(tenant_dir: str, tenant_name: str, theme: str, domain: str) -> None:
    """
    Generates a styled storefront placeholder HTML file served by nginx:alpine.
    This allows the full provisioning flow to work without needing a custom
    Next.js image built and pushed to a registry.
    """
    cfg = THEME_CONFIG.get(theme, THEME_CONFIG["fashion"])
    store_url = f"http://{tenant_name}.{domain}"
    admin_url = f"http://admin.{tenant_name}.{domain}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{cfg['title']} — {tenant_name}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #0f172a; color: #e2e8f0; min-height: 100vh;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
    }}
    .hero {{
      text-align: center; padding: 60px 24px;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 24px; max-width: 600px; width: 100%;
    }}
    .emoji {{ font-size: 80px; margin-bottom: 24px; display: block; }}
    .badge {{
      display: inline-block; padding: 6px 16px; border-radius: 99px;
      background: {cfg['color']}20; color: {cfg['color']};
      font-size: 12px; font-weight: 600; letter-spacing: 0.05em;
      text-transform: uppercase; margin-bottom: 20px; border: 1px solid {cfg['color']}40;
    }}
    h1 {{ font-size: 2.5rem; font-weight: 800; margin-bottom: 12px;
      background: {cfg['gradient']}; -webkit-background-clip: text;
      -webkit-text-fill-color: transparent; background-clip: text; }}
    p {{ color: #94a3b8; font-size: 1.1rem; line-height: 1.6; margin-bottom: 32px; }}
    .store-name {{
      font-size: 1rem; color: #64748b;
      background: rgba(255,255,255,0.04); padding: 10px 20px;
      border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);
      font-family: monospace; margin-bottom: 32px; display: inline-block;
    }}
    .cta {{
      display: inline-block; padding: 14px 32px; border-radius: 12px;
      background: {cfg['gradient']}; color: white;
      font-weight: 700; font-size: 1rem; text-decoration: none;
      box-shadow: 0 8px 32px {cfg['color']}40;
    }}
    .footer {{ margin-top: 48px; color: #334155; font-size: 0.8rem; }}
    .footer a {{ color: #64748b; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="hero">
    <span class="emoji">{cfg['emoji']}</span>
    <div class="badge">{theme} theme</div>
    <h1>{tenant_name}</h1>
    <p>{cfg['description']}</p>
    <div class="store-name">{store_url}</div>
    <br>
    <a href="{admin_url}" class="cta">Open Admin Panel →</a>
  </div>
  <div class="footer">
    Powered by <a href="#">SaaS Platform</a> &nbsp;·&nbsp; Tenant: {tenant_name}
  </div>
</body>
</html>"""

    html_path = os.path.join(tenant_dir, "storefront.html")
    with open(html_path, "w") as f:
        f.write(html)
    logger.info(json.dumps({"event": "storefront_html_written", "path": html_path, "theme": theme}))


def generate_admin_html(tenant_dir: str, tenant_name: str, domain: str) -> None:
    """
    Generates a placeholder admin panel HTML served by nginx:alpine.
    Replace with the real MedusaJS admin when available.
    """
    admin_url = f"http://admin.{tenant_name}.{domain}"
    store_url = f"http://{tenant_name}.{domain}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Admin Panel — {tenant_name}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #0f172a; color: #e2e8f0; min-height: 100vh;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
    }}
    .card {{
      text-align: center; padding: 60px 40px;
      background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
      border-radius: 24px; max-width: 560px; width: 100%;
    }}
    .icon {{ font-size: 64px; margin-bottom: 20px; }}
    .badge {{
      display: inline-block; padding: 5px 14px; border-radius: 99px;
      background: #7c3aed20; color: #a78bfa; font-size: 11px; font-weight: 700;
      letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 20px;
      border: 1px solid #7c3aed40;
    }}
    h1 {{ font-size: 2rem; font-weight: 800; color: white; margin-bottom: 10px; }}
    p {{ color: #64748b; margin-bottom: 30px; line-height: 1.6; }}
    .btn {{
      display: inline-block; padding: 12px 28px; border-radius: 10px;
      background: linear-gradient(135deg, #7c3aed, #ec4899); color: white;
      font-weight: 700; text-decoration: none; font-size: 0.95rem;
    }}
    .info {{ margin-top: 32px; font-size: 0.8rem; color: #334155; font-family: monospace; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">🛠️</div>
    <div class="badge">Admin Panel</div>
    <h1>{tenant_name}</h1>
    <p>Your store admin panel is provisioned and ready.<br>
       Connect a real MedusaJS backend to manage products, orders, and customers.</p>
    <a href="{store_url}" class="btn">View Storefront →</a>
    <div class="info">{admin_url}</div>
  </div>
</body>
</html>"""

    html_path = os.path.join(tenant_dir, "admin.html")
    with open(html_path, "w") as f:
        f.write(html)
    logger.info(json.dumps({"event": "admin_html_written", "path": html_path}))


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
    generate_storefront_html(tenant_dir, tenant_name, theme, settings.DOMAIN)
    generate_admin_html(tenant_dir, tenant_name, settings.DOMAIN)

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
