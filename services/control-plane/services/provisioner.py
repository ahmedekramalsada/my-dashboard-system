import os
import time
import shutil
import json
import logging
import secrets
import subprocess
from abc import ABC, abstractmethod
from core.config import settings

logger = logging.getLogger("ProvisioningAPI.Provisioner")


# ---------------------------------------------------------------------------
# Storefront HTML Generator — themed landing page per tenant
# ---------------------------------------------------------------------------

def generate_storefront_html(tenant_name: str, theme: str, domain: str) -> str:
    """Generate a beautiful themed storefront HTML that fetches products from Medusa."""
    themes = {
        "fashion": {
            "primary": "#c084fc",
            "accent": "#7c3aed",
            "bg": "#0a0a0a",
            "card_bg": "#111111",
            "headline": "Fashion & Apparel",
            "tagline": "Discover the latest trends, curated just for you.",
            "emoji": "👗",
        },
        "electronics": {
            "primary": "#38bdf8",
            "accent": "#0ea5e9",
            "bg": "#050d1a",
            "card_bg": "#0d1b2a",
            "headline": "Tech & Electronics",
            "tagline": "Leading-edge gadgets & components, delivered fast.",
            "emoji": "⚡",
        },
        "minimal": {
            "primary": "#a3a3a3",
            "accent": "#525252",
            "bg": "#fafafa",
            "card_bg": "#ffffff",
            "headline": "Concept Store",
            "tagline": "Minimalism refined. Less, but better.",
            "emoji": "○",
        },
    }
    t = themes.get(theme, themes["fashion"])
    text_color = "#ffffff" if theme != "minimal" else "#111111"
    subtext_color = "#a3a3a3" if theme != "minimal" else "#666666"
    admin_url = f"http://admin.{tenant_name}.{domain}/app"
    api_url = f"http://admin.{tenant_name}.{domain}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{tenant_name.capitalize()} Store — {t["headline"]}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        :root {{
            --primary: {t["primary"]};
            --accent: {t["accent"]};
            --bg: {t["bg"]};
            --card-bg: {t["card_bg"]};
            --text: {text_color};
            --subtext: {subtext_color};
        }}
        body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }}

        /* NAV */
        nav {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 1.2rem 2rem; border-bottom: 1px solid rgba(255,255,255,0.07);
            position: sticky; top: 0; backdrop-filter: blur(12px);
            background: rgba(10,10,10,0.8); z-index: 100;
        }}
        .logo {{ font-weight: 700; font-size: 1.2rem; color: var(--primary); letter-spacing: -0.5px; }}
        .nav-links {{ display: flex; gap: 1.5rem; align-items: center; }}
        .nav-links a {{ color: var(--subtext); text-decoration: none; font-size: 0.9rem; transition: color 0.2s; }}
        .nav-links a:hover {{ color: var(--text); }}
        .cart-btn {{
            background: var(--primary); color: #fff; border: none; padding: 0.5rem 1.2rem;
            border-radius: 50px; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: opacity 0.2s;
        }}
        .cart-btn:hover {{ opacity: 0.85; }}

        /* HERO */
        .hero {{
            text-align: center; padding: 6rem 2rem 4rem;
            background: radial-gradient(ellipse at 50% 0%, {t["accent"]}22 0%, transparent 70%);
        }}
        .store-badge {{
            display: inline-block; background: {t["accent"]}22; color: var(--primary);
            border: 1px solid {t["accent"]}44; border-radius: 50px; padding: 0.3rem 1rem;
            font-size: 0.8rem; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 1.5rem; text-transform: uppercase;
        }}
        .hero h1 {{ font-size: clamp(2.5rem, 6vw, 4.5rem); font-weight: 700; line-height: 1.1; letter-spacing: -2px; margin-bottom: 1rem; }}
        .hero h1 span {{ color: var(--primary); }}
        .hero p {{ color: var(--subtext); font-size: 1.1rem; max-width: 500px; margin: 0 auto 2.5rem; line-height: 1.6; }}
        .hero-cta {{
            display: inline-flex; gap: 1rem; flex-wrap: wrap; justify-content: center;
        }}
        .btn-primary {{
            background: var(--primary); color: #fff; border: none; padding: 0.85rem 2rem;
            border-radius: 50px; font-size: 1rem; font-weight: 600; cursor: pointer;
            text-decoration: none; transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 0 30px {t["accent"]}55;
        }}
        .btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 4px 40px {t["accent"]}88; }}
        .btn-secondary {{
            background: transparent; color: var(--subtext); border: 1px solid rgba(255,255,255,0.15);
            padding: 0.85rem 2rem; border-radius: 50px; font-size: 1rem; font-weight: 500;
            cursor: pointer; text-decoration: none; transition: border-color 0.2s, color 0.2s;
        }}
        .btn-secondary:hover {{ border-color: var(--primary); color: var(--text); }}

        /* PRODUCTS */
        #products-section {{ padding: 4rem 2rem; max-width: 1200px; margin: 0 auto; }}
        .section-title {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem; }}
        .section-subtitle {{ color: var(--subtext); font-size: 0.9rem; margin-bottom: 2.5rem; }}
        #products-grid {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1.5rem;
        }}
        .product-card {{
            background: var(--card-bg); border: 1px solid rgba(255,255,255,0.07);
            border-radius: 16px; overflow: hidden; transition: transform 0.2s, border-color 0.2s;
        }}
        .product-card:hover {{ transform: translateY(-4px); border-color: {t["accent"]}55; }}
        .product-img {{
            width: 100%; aspect-ratio: 1; background: linear-gradient(135deg, {t["accent"]}22, {t["primary"]}11);
            display: flex; align-items: center; justify-content: center; font-size: 4rem;
        }}
        .product-info {{ padding: 1.2rem; }}
        .product-title {{ font-weight: 600; font-size: 0.95rem; margin-bottom: 0.4rem; }}
        .product-price {{ color: var(--primary); font-weight: 700; font-size: 1.1rem; margin-bottom: 1rem; }}
        .add-to-cart {{
            width: 100%; background: var(--accent); color: #fff; border: none; padding: 0.7rem;
            border-radius: 8px; font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: opacity 0.2s;
        }}
        .add-to-cart:hover {{ opacity: 0.85; }}

        /* EMPTY STATE */
        .empty-state {{
            text-align: center; padding: 4rem 2rem; grid-column: 1 / -1; color: var(--subtext);
        }}
        .empty-state p {{ font-size: 0.9rem; margin-top: 0.5rem; }}

        /* LOADING */
        .skeleton {{ background: linear-gradient(90deg, var(--card-bg) 25%, rgba(255,255,255,0.05) 50%, var(--card-bg) 75%); background-size: 200%; animation: shimmer 1.5s infinite; border-radius: 16px; height: 300px; }}
        @keyframes shimmer {{ 0% {{ background-position: 200% 0; }} 100% {{ background-position: -200% 0; }} }}

        /* FOOTER */
        footer {{ text-align: center; padding: 3rem 2rem; border-top: 1px solid rgba(255,255,255,0.07); color: var(--subtext); font-size: 0.85rem; margin-top: 4rem; }}
        footer a {{ color: var(--primary); text-decoration: none; }}
    </style>
</head>
<body>
    <nav>
        <div class="logo">{t["emoji"]} {tenant_name.capitalize()}</div>
        <div class="nav-links">
            <a href="#">Shop</a>
            <a href="#">Collections</a>
            <a href="{admin_url}" target="_blank">Admin ↗</a>
            <button class="cart-btn">🛒 Cart (0)</button>
        </div>
    </nav>

    <section class="hero">
        <div class="store-badge">{t["headline"]}</div>
        <h1>Shop the <span>Future</span><br>of Retail</h1>
        <p>{t["tagline"]}</p>
        <div class="hero-cta">
            <a href="#products-section" class="btn-primary">Browse Products</a>
            <a href="{admin_url}" target="_blank" class="btn-secondary">Manage Store</a>
        </div>
    </section>

    <section id="products-section">
        <h2 class="section-title">Featured Products</h2>
        <p class="section-subtitle">Pulled live from your Medusa backend</p>
        <div id="products-grid">
            <div class="skeleton"></div>
            <div class="skeleton"></div>
            <div class="skeleton"></div>
            <div class="skeleton"></div>
        </div>
    </section>

    <footer>
        <p>Powered by <a href="{admin_url}" target="_blank">{tenant_name.capitalize()} Store</a> · Built on MedusaJS</p>
    </footer>

    <script>
        let cartId = localStorage.getItem('cart_id');

        async function updateCartCount() {
            if (!cartId) return;
            try {
                const res = await fetch(`/store/carts/${cartId}`);
                if (res.ok) {
                    const { cart } = await res.json();
                    const count = cart.items?.reduce((all, item) => all + item.quantity, 0) || 0;
                    document.querySelector('.cart-btn').innerText = `🛒 Cart (${count})`;
                }
            } catch (e) { console.error("Cart update failed", e); }
        }

        async function createCart() {
            try {
                // Medusa v2 Create Cart
                const res = await fetch('/store/carts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                const { cart } = await res.json();
                cartId = cart.id;
                localStorage.setItem('cart_id', cartId);
                return cartId;
            } catch (e) {
                console.error("Failed to create cart", e);
            }
        }

        async function addToCart(variantId) {
            const btn = event.target;
            const originalText = btn.innerText;
            btn.innerText = 'adding...';
            btn.disabled = true;

            try {
                if (!cartId) await createCart();
                
                // Medusa v2 Add Line Item
                const res = await fetch(`/store/carts/${cartId}/line-items`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ variant_id: variantId, quantity: 1 })
                });

                if (res.ok) {
                    await updateCartCount();
                    btn.innerText = 'Added! ✅';
                    setTimeout(() => {
                        btn.innerText = originalText;
                        btn.disabled = false;
                    }, 2000);
                } else {
                    throw new Error('Add failed');
                }
            } catch (e) {
                alert("Could not add to cart. Is the backend ready?");
                btn.innerText = originalText;
                btn.disabled = false;
            }
        }

        async function loadProducts() {
            const grid = document.getElementById('products-grid');
            try {
                // Calls via Nginx proxy — the proxy injects the publishable API key automatically
                const res = await fetch('/api/items');
                if (!res.ok) throw new Error('API not ready');
                const { products } = await res.json();

                if (!products || products.length === 0) {
                    grid.innerHTML = `<div class="empty-state"><h3>No products yet</h3><p>Add products from your <a href="${admin_url}" target="_blank" style="color: var(--primary)">admin panel</a>.</p></div>`;
                    return;
                }

                grid.innerHTML = products.map(p => {
                    const variant = p.variants?.[0];
                    const price = variant?.calculated_price?.calculated_amount;
                    const currency = variant?.calculated_price?.currency_code?.toUpperCase() || 'USD';
                    const formattedPrice = price ? (price / 100).toFixed(2) + ' ' + currency : 'View Store';
                    const thumbnail = p.thumbnail;
                    return `
                        <div class="product-card">
                            <div class="product-img">
                                ${thumbnail ? `<img src="${thumbnail}" alt="${p.title}" style="width:100%;height:100%;object-fit:cover;">` : '{t["emoji"]}'}
                            </div>
                            <div class="product-info">
                                <div class="product-title">${p.title}</div>
                                <div class="product-price">${formattedPrice}</div>
                                <button class="add-to-cart" onclick="addToCart('${variant?.id}')">Add to Cart</button>
                            </div>
                        </div>`;
                }).join('');
            } catch (err) {
                grid.innerHTML = `<div class="empty-state"><h3>Store is starting up…</h3><p>Check back in a few seconds or visit your <a href="${admin_url}" target="_blank" style="color: var(--primary)">admin panel</a> to add products.</p></div>`;
            }
        }
        
        loadProducts();
        updateCartCount();
    </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Abstract Provisioner Interface
# ---------------------------------------------------------------------------

class Provisioner(ABC):
    @abstractmethod
    def get_tenant_status(self) -> list[dict]:
        pass

    @abstractmethod
    def start_tenant(self, tenant_name: str, theme: str, db_credentials: dict, site_type: str = "ecommerce") -> bool:
        pass

    @abstractmethod
    def delete_tenant(self, tenant_name: str) -> bool:
        pass

    @abstractmethod
    def seed_admin_user(self, tenant_name: str, email: str, password: str) -> bool:
        pass

    @abstractmethod
    def suspend_tenant(self, tenant_name: str) -> bool:
        pass

    @abstractmethod
    def resume_tenant(self, tenant_name: str) -> bool:
        pass

    @abstractmethod
    def get_tenant_logs(self, tenant_name: str, lines: int = 100) -> str:
        pass


# ---------------------------------------------------------------------------
# Local Docker Provisioner
# ---------------------------------------------------------------------------

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
        containers = self.client.containers.list(filters={"name": "medusa-"})
        result = []
        for c in containers:
            health = "unknown"
            try:
                health_status = c.attrs.get("State", {}).get("Health", {})
                if health_status:
                    health = health_status.get("Status", "none")  # healthy / starting / unhealthy / none
                else:
                    health = "none"  # no healthcheck configured
            except Exception:
                health = "unknown"
            result.append({"id": c.short_id, "name": c.name, "status": c.status, "health": health})
        return result

    def start_tenant(self, tenant_name: str, theme: str, db_credentials: dict, site_type: str = "ecommerce") -> bool:
        tenant_dir = self._copy_blueprint(tenant_name, site_type)
        env_vars = self._render_env_file(tenant_dir, tenant_name, theme, db_credentials, site_type)
        self._render_storefront(tenant_dir, tenant_name, theme)

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

    def seed_admin_user(self, tenant_name: str, email: str, password: str) -> bool:
        """
        Waits for the Medusa container to be healthy, then seeds the admin user.
        Retries up to 30 times (5 minutes) to allow migrations to complete.
        """
        container_name = f"medusa-{tenant_name}"
        logger.info(json.dumps({"event": "seeding_admin_user", "tenant": tenant_name, "email": email}))

        # Wait for container to become healthy (up to 5 minutes)
        for attempt in range(30):
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format={{.State.Health.Status}}", container_name],
                    capture_output=True, text=True, timeout=10,
                )
                health = result.stdout.strip()
                logger.info(json.dumps({"event": "container_health_check", "tenant": tenant_name, "health": health, "attempt": attempt + 1}))

                if health == "healthy":
                    break
                elif health in ("", "none"):
                    # Container has no healthcheck — just wait a fixed time
                    time.sleep(10)
                    break
            except Exception as e:
                logger.warning(f"Health check probe failed: {e}")
            time.sleep(10)
        else:
            logger.error(json.dumps({"event": "container_never_healthy", "tenant": tenant_name}))
            raise Exception(f"Container {container_name} never became healthy for admin seeding")

        # Delete the user if they already exist so we can recreate them with the new password
        try:
            db_name = f"db_{tenant_name}"
            subprocess.run(
                [
                    "docker", "exec", "shared-postgres", 
                    "psql", "-U", "root", "-d", db_name, 
                    "-c", f"DELETE FROM auth_identity WHERE id IN (SELECT auth_identity_id FROM provider_identity WHERE entity_id='{email}'); DELETE FROM \"user\" WHERE email='{email}';"
                ],
                capture_output=True, timeout=15
            )
            logger.info(json.dumps({"event": "cleared_existing_admin", "tenant": tenant_name, "email": email}))
        except Exception as e:
            logger.warning(f"Could not clear existing admin before seeding: {e}")

        # Seed the user
        try:
            result = subprocess.run(
                ["docker", "exec", container_name, "npx", "medusa", "user", "-e", email, "-p", password],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                logger.info(json.dumps({"event": "admin_user_seeded", "tenant": tenant_name, "email": email}))
                return True
            else:
                logger.error(json.dumps({"event": "admin_seed_failed", "tenant": tenant_name, "stderr": result.stderr}))
                raise Exception(f"Admin seed failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise Exception(f"Admin seeding timed out for tenant: {tenant_name}")

    def fetch_and_inject_publishable_key(self, tenant_name: str) -> bool:
        """
        Retrieves the publishable API key auto-generated by Medusa and injects it 
        into the live Storefront Nginx container so the frontend can query products.
        """
        logger.info(json.dumps({"event": "fetching_publishable_key", "tenant": tenant_name}))
        db_name = f"db_{tenant_name.replace('-', '_')}"
        
        # Poll the database for up to 30 seconds since migrations might be running
        for _ in range(30):
            try:
                result = subprocess.run(
                    [
                        "docker", "exec", "shared-postgres", 
                        "psql", "-U", "root", "-d", db_name, "-t", "-c", 
                        "SELECT token FROM api_key WHERE type='publishable' LIMIT 1;"
                    ],
                    capture_output=True, text=True, timeout=10
                )
                token = result.stdout.strip()
                if token.startswith("pk_"):
                    # We got the token! Inject it into the Nginx container
                    storefront_container = f"storefront-{tenant_name}"
                    # Modify the Nginx configuration file directly using Python because 
                    # running `sed -i` fails on Docker bind mounts (device or resource busy)
                    nginx_conf_path = os.path.join(settings.TENANTS_DIR, tenant_name, "storefront-nginx.conf")
                    if os.path.exists(nginx_conf_path):
                        with open(nginx_conf_path, "r") as f:
                            conf_data = f.read()
                        
                        conf_data = conf_data.replace('window.SAAS_API=""', f'window.SAAS_API="{token}"')
                        conf_data = conf_data.replace('# MEDUSA_API_KEY_PLACEHOLDER', f'proxy_set_header x-publishable-api-key "{token}";')
                        
                        with open(nginx_conf_path, "w") as f:
                            f.write(conf_data)
                    
                    # Reload the Nginx container to apply the changes
                    reload_cmd = ["docker", "exec", storefront_container, "nginx", "-s", "reload"]
                    subprocess.run(reload_cmd, capture_output=True, timeout=10)
                    logger.info(json.dumps({"event": "publishable_key_injected", "tenant": tenant_name, "token_prefix": token[:10]}))
                    return True
            except Exception as e:
                logger.warning(f"Error checking publishable key: {e}")
            time.sleep(5)
            
        logger.error(json.dumps({"event": "publishable_key_timeout", "tenant": tenant_name}))
        return False

    def suspend_tenant(self, tenant_name: str) -> bool:
        """Stop tenant containers without removing data or volumes."""
        tenant_dir = os.path.join(settings.TENANTS_DIR, tenant_name)
        if not os.path.exists(tenant_dir):
            raise FileNotFoundError(f"Tenant directory not found: {tenant_dir}")
        logger.info(json.dumps({"event": "suspend_tenant", "tenant": tenant_name}))
        try:
            subprocess.run(
                ["docker", "compose", "stop"],
                cwd=tenant_dir, check=True, capture_output=True, text=True, timeout=60,
            )
            logger.info(json.dumps({"event": "suspend_tenant_success", "tenant": tenant_name}))
            return True
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to suspend tenant: {e.stderr}")

    def resume_tenant(self, tenant_name: str) -> bool:
        """Restart previously stopped tenant containers."""
        tenant_dir = os.path.join(settings.TENANTS_DIR, tenant_name)
        if not os.path.exists(tenant_dir):
            raise FileNotFoundError(f"Tenant directory not found: {tenant_dir}")
        logger.info(json.dumps({"event": "resume_tenant", "tenant": tenant_name}))
        try:
            subprocess.run(
                ["docker", "compose", "start"],
                cwd=tenant_dir, check=True, capture_output=True, text=True, timeout=60,
            )
            logger.info(json.dumps({"event": "resume_tenant_success", "tenant": tenant_name}))
            return True
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to resume tenant: {e.stderr}")

    def get_tenant_logs(self, tenant_name: str, lines: int = 100) -> str:
        """Return the last N lines of Medusa container logs."""
        container_name = f"medusa-{tenant_name}"
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), container_name],
                capture_output=True, text=True, timeout=15,
            )
            return result.stdout + result.stderr  # Medusa logs to stderr
        except subprocess.TimeoutExpired:
            return "Log fetch timed out."
        except Exception as e:
            raise Exception(f"Could not fetch logs for {container_name}: {e}")

    # --- Private helpers ---

    def _copy_blueprint(self, tenant_name: str, site_type: str = "ecommerce") -> str:
        blueprint_src = os.path.join(os.path.dirname(__file__), "..", "blueprints", site_type)
        blueprint_src = os.path.abspath(blueprint_src)
        tenant_dir = os.path.join(settings.TENANTS_DIR, tenant_name)

        if not os.path.isdir(blueprint_src):
            raise FileNotFoundError(f"Blueprint source directory not found: {blueprint_src}")

        if os.path.exists(tenant_dir):
            shutil.rmtree(tenant_dir)

        shutil.copytree(blueprint_src, tenant_dir)
        
        # Substitute {{TENANT_NAME}} inside docker-compose.yml so that
        # dynamic identifiers (e.g. volume names) are resolved before Docker validates the file
        compose_path = os.path.join(tenant_dir, "docker-compose.yml")
        if os.path.exists(compose_path):
            with open(compose_path, "r") as f:
                compose_content = f.read()
            compose_content = compose_content.replace("{{TENANT_NAME}}", tenant_name)
            with open(compose_path, "w") as f:
                f.write(compose_content)
        
        return tenant_dir

    def _render_env_file(self, tenant_dir: str, tenant_name: str, theme: str, db_credentials: dict, site_type: str = "ecommerce") -> dict:
        """Generate .env with unique cryptographic secrets per tenant."""
        jwt_secret = secrets.token_hex(32)
        cookie_secret = secrets.token_hex(32)

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
"""
        if site_type == "ecommerce":
            env_content += f"""
# Medusa specific variables
DATABASE_URL=postgres://{context['DB_USER']}:{context['DB_PASSWORD']}@{context['DB_HOST']}:{context['DB_PORT']}/{context['DB_NAME']}?sslmode=disable
REDIS_URL=redis://redis-{context['TENANT_NAME']}:6379
SECURE_COOKIES=false
STORE_CORS=http://{context['TENANT_NAME']}.{context['DOMAIN']}
ADMIN_CORS=http://admin.{context['TENANT_NAME']}.{context['DOMAIN']}
AUTH_CORS=http://admin.{context['TENANT_NAME']}.{context['DOMAIN']},http://{context['TENANT_NAME']}.{context['DOMAIN']}
JWT_SECRET={jwt_secret}
COOKIE_SECRET={cookie_secret}
# BACKEND_URL: Medusa prefixes uploaded image URLs with this value
BACKEND_URL=http://{context['TENANT_NAME']}.{context['DOMAIN']}
"""
        elif site_type == "cms":
            env_content += f"""
# Directus specific variables
KEY={secrets.token_hex(16)}
SECRET={secrets.token_hex(16)}
DB_CLIENT=pg
DB_HOST={context['DB_HOST']}
DB_PORT={context['DB_PORT']}
DB_DATABASE={context['DB_NAME']}
DB_USER={context['DB_USER']}
DB_PASSWORD={context['DB_PASSWORD']}
PUBLIC_URL=http://admin.{context['TENANT_NAME']}.{context['DOMAIN']}
"""
        elif site_type == "blog":
            env_content += f"""
# Ghost specific variables
database__client=pg
database__connection__host={context['DB_HOST']}
database__connection__port={context['DB_PORT']}
database__connection__user={context['DB_USER']}
database__connection__password={context['DB_PASSWORD']}
database__connection__database={context['DB_NAME']}
url=http://admin.{context['TENANT_NAME']}.{context['DOMAIN']}
"""
        elif site_type == "booking":
            env_content += f"""
# Cal.com specific variables
DATABASE_URL=postgresql://{context['DB_USER']}:{context['DB_PASSWORD']}@{context['DB_HOST']}:{context['DB_PORT']}/{context['DB_NAME']}?sslmode=disable
NEXTAUTH_SECRET={secrets.token_hex(32)}
CALENDSO_ENCRYPTION_KEY={secrets.token_hex(24)}
NEXT_PUBLIC_WEBAPP_URL=http://admin.{context['TENANT_NAME']}.{context['DOMAIN']}
"""
        elif site_type == "static":
            # Just default vars already included
            pass
            
        env_path = os.path.join(tenant_dir, ".env")
        with open(env_path, "w") as f:
            f.write(env_content)
        logger.info(json.dumps({"event": "env_file_written", "path": env_path}))
        return context

    def _render_storefront(self, tenant_dir: str, tenant_name: str, theme: str) -> None:
        """Generate a themed storefront HTML file and mount it into Nginx."""
        # Note: If custom template was supplied, it's copied over right after creation,
        # but here we generate the initial one or the default one.
        html = generate_storefront_html(tenant_name, theme, settings.DOMAIN)
        storefront_path = os.path.join(tenant_dir, "storefront.html")
        with open(storefront_path, "w") as f:
            f.write(html)
        logger.info(json.dumps({"event": "storefront_html_generated", "tenant": tenant_name, "theme": theme}))

        # Generate Nginx Config
        nginx_template_path = os.path.join(tenant_dir, "storefront-nginx.conf.template")
        nginx_out_path = os.path.join(tenant_dir, "storefront-nginx.conf")
        
        if os.path.exists(nginx_template_path):
            with open(nginx_template_path, "r") as f:
                nginx_config = f.read()
            
            nginx_config = nginx_config.replace("{{TENANT_NAME}}", tenant_name)
            nginx_config = nginx_config.replace("{{DOMAIN}}", settings.DOMAIN)
            
            with open(nginx_out_path, "w") as f:
                f.write(nginx_config)
            logger.info(json.dumps({"event": "nginx_config_generated", "tenant": tenant_name}))


# ---------------------------------------------------------------------------
# Kubernetes Provisioner (Stub — Phase 7)
# ---------------------------------------------------------------------------

class KubernetesProvisioner(Provisioner):
    def get_tenant_status(self) -> list[dict]:
        return []

    def start_tenant(self, tenant_name: str, theme: str, db_credentials: dict) -> bool:
        logger.info(json.dumps({"event": "k8s_provisioning_started", "tenant": tenant_name}))
        return True

    def delete_tenant(self, tenant_name: str) -> bool:
        logger.info(json.dumps({"event": "k8s_deprovisioning_started", "tenant": tenant_name}))
        return True

    def seed_admin_user(self, tenant_name: str, email: str, password: str) -> bool:
        logger.info(json.dumps({"event": "k8s_seed_admin_started", "tenant": tenant_name}))
        return True

    def suspend_tenant(self, tenant_name: str) -> bool:
        logger.info(json.dumps({"event": "k8s_suspend_started", "tenant": tenant_name}))
        return True

    def resume_tenant(self, tenant_name: str) -> bool:
        logger.info(json.dumps({"event": "k8s_resume_started", "tenant": tenant_name}))
        return True

    def get_tenant_logs(self, tenant_name: str, lines: int = 100) -> str:
        return "Log streaming not implemented for Kubernetes yet."


# Initialize the active provisioner based on environment configuration
active_provisioner = LocalDockerProvisioner()
