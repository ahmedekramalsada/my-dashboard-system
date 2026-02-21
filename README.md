# SaaS Multi-Tenant Platform — Operations Guide

> **Production-ready SaaS platform** that provisions isolated MedusaJS e-commerce stores on demand. Each tenant gets its own database, containers, and themed storefront.

---

## 🏗️ Architecture Overview

```
                          INTERNET
                             │
                          Traefik (Reverse Proxy + SSL)
                    ┌────────┴────────────────────┐
                    │                             │
         superadmin.{domain}            {tenant}.{domain}
         api.admin.{domain}         admin.{tenant}.{domain}
                    │                             │
              [Super Admin              [Tenant Traffic]
               Dashboard]                        │
               BasicAuth              ┌───────────┴──────────┐
                    │            Nginx Storefront    Medusa Admin
              FastAPI API          (themed HTML)    (port 9000)
              (control plane)           │                │
                    │              Products API      Order Mgmt
               ┌────┴────┐              └──────┬─────────┘
               │         │                     │
         shared-postgres  Docker SDK         Redis
         (tenant DBs)   (manages tenant      (per-tenant)
                         containers)
```

### Who uses what?

| Role | URL | Auth | Purpose |
|------|-----|------|---------|
| **You (super admin)** | `superadmin.{domain}` | HTTP Basic Auth | Manage all tenants |
| **Tenant owner** | `admin.{tenant}.{domain}/app` | Medusa login | Manage their store |
| **Shoppers** | `{tenant}.{domain}` | None (public) | Browse & buy |

---

## 🚀 First-Time Setup

### 1. Clone and configure

```bash
git clone <repo>
cd "my dashboard system"
cp .env.example .env
```

Edit `.env` and set **all** values:

```bash
DB_ROOT_PASSWORD=<strong-random-password>
DASHBOARD_USER=admin
DASHBOARD_PASS=<your-dashboard-password>
API_KEY=<run: openssl rand -hex 32>
DOMAIN=yourdomain.com   # or 127.0.0.1.nip.io for local
```

### 2. Build the Medusa base image (one-time)

```bash
bash services/tenant-blueprint/medusa/build_medusa_base.sh
```

This takes ~10 minutes on first run (builds MedusaJS from source).

### 3. Start the platform

```bash
# Create the shared Docker network (first time only)
docker network create traefik_default

# Create tenant data directory (first time only)
sudo mkdir -p /opt/saas/tenants

# Start everything
docker compose up -d
```

### 4. Verify it's running

```bash
docker compose ps
curl http://localhost:8000/health   # Should return {"status":"ok"}
```

Open **`http://superadmin.127.0.0.1.nip.io`** (or your domain) — you'll be prompted for username/password.

---

## 📋 Day-to-Day Operations

### Create a new tenant store

**Via dashboard:** Open superadmin, fill in Store Name + Theme, click **Deploy**.

**Via API:**
```bash
curl -X POST http://api.admin.127.0.0.1.nip.io/create-store \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"tenant_name": "mystore", "theme": "fashion"}'
```

Themes: `fashion`, `electronics`, `minimal`, `default`

### Site Types (Blueprints)
When creating a store, you can specify the `site_type`:

| Type | Backend | Use Case |
|------|---------|----------|
| `ecommerce` | MedusaJS | Online stores with full checkout |
| `blog` | Ghost | Content sites, newsletters, blogs |
| `cms` | Directus | Headless CMS for custom data |
| `static` | Nginx | Pure landing pages |
| `booking` | Cal.com | Scheduling and appointments |

The credentials modal shows the admin email + auto-generated password. Save it — it won't be shown again.

**Admin is ready after ~3 minutes** (Medusa runs database migrations on first start).

---

### Delete a tenant store

**Via dashboard:** Click the red 🗑️ trash icon → confirm in modal.

**Via API:**
```bash
curl -X POST http://api.admin.127.0.0.1.nip.io/delete-store \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"tenant_name": "mystore"}'
```

⚠️ This removes **all containers, database, and files** — irreversible.

---

### Suspend / Resume a tenant (keeps data)

```bash
# Suspend (stop containers, keep data)
curl -X POST http://api.admin.127.0.0.1.nip.io/tenants/mystore/suspend \
  -H "X-API-Key: YOUR_API_KEY"

# Resume (restart stopped containers)
curl -X POST http://api.admin.127.0.0.1.nip.io/tenants/mystore/resume \
  -H "X-API-Key: YOUR_API_KEY"
```

Or use the **Pause ⏸ / Play ▶** buttons on the dashboard.

---

### View tenant logs

```bash
curl http://api.admin.127.0.0.1.nip.io/tenants/mystore/logs?lines=100 \
  -H "X-API-Key: YOUR_API_KEY"
```

Or click the **Logs 📋** button on the dashboard.

---

### Re-seed admin user (reset password)

```bash
curl -X POST http://api.admin.127.0.0.1.nip.io/tenants/mystore/seed-admin \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"email": "admin@mystore.com", "password": "newpassword123"}'
```

Or use the **👤** button on the dashboard.

---

## 🔑 Changing Passwords & Secrets

### Change dashboard password

1. Edit `.env`: set `DASHBOARD_PASS=newpassword`
2. Rebuild: `docker compose build --no-cache saas-dashboard && docker compose up -d saas-dashboard`

### Rotate API key

1. Generate: `openssl rand -hex 32`
2. Edit `.env`: update `API_KEY=<new-key>`
3. Restart: `docker compose up -d saas-api`
4. Update your browser: `localStorage.setItem('saas_api_key', '<new-key>')`

### Set API key in the browser (after login to dashboard)

Open browser console on the dashboard and run:
```javascript
localStorage.setItem('saas_api_key', 'your-api-key-here')
location.reload()
```

This stores the key in your browser so all dashboard buttons work with authentication.

### Change Postgres root password

> ⚠️ Do this BEFORE creating any tenants. Changing after requires migration.

1. Edit `.env`: set `DB_ROOT_PASSWORD=<new-password>`
2. `docker compose down` then `docker volume rm mydashboardsystem_pg-data`
3. `docker compose up -d`

---

## 🔒 Security Checklist

Before going to production:

- [ ] `DASHBOARD_PASS` is a strong, unique password (not `admin123`)
- [ ] `API_KEY` is a 32+ char random hex (not the placeholder)
- [ ] `DB_ROOT_PASSWORD` is a strong, unique password
- [ ] `.env` is in `.gitignore` (it is — but verify before `git push`)
- [ ] `my-aws-key.pem` is moved out of the project directory
- [ ] `CORS_ORIGINS` is set to your exact domain (not `*`) in production
- [ ] HTTPS is configured (set `LETS_ENCRYPT_EMAIL` in `.env`)
- [ ] Port 8000 is not open in your firewall (API is behind Traefik only)

---

## ☁️ Enabling HTTPS (Let's Encrypt)

1. Make sure your domain's DNS A record points to your server IP
2. In `.env`, set: `LETS_ENCRYPT_EMAIL=you@yourdomain.com`
3. In `docker-compose.yml`, uncomment the HTTPS lines (marked with `# Uncomment for HTTPS`)
4. Restart Traefik: `docker compose up -d traefik`

---

## 📊 Monitoring & Logs

### Platform logs

```bash
# Control plane API
docker logs saas-api --tail 50 -f

# Dashboard Nginx
docker logs saas-dashboard --tail 50 -f

# Shared Postgres
docker logs shared-postgres --tail 50 -f
```

### Tenant logs

```bash
docker logs medusa-<tenant-name> --tail 100 -f
```

### Check all container health

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

## 🔧 Common Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| Admin panel 404 | Medusa still migrating | Wait 3-5 min, watch for "Starting…" badge |
| Admin panel 404 after restart | Password drift | `curl -X POST .../tenants/{name}/seed-admin` or re-provision |
| Dashboard shows 401 | Wrong password | Check `DASHBOARD_PASS` in `.env` |
| API returns 403 | Missing/wrong API key | Set `localStorage.setItem('saas_api_key', '...')` in browser |
| Create store returns 422 | Invalid name | Names must be 3-30 lowercase chars, no leading/trailing hyphens |
| Tenant stuck "Starting…" | DB auth failure | Check `docker logs medusa-<name>` for password errors |

### Fix password drift (tenant can't connect to DB)

```bash
# Get the password from the tenant's .env
PASS=$(docker exec saas-api grep DB_PASSWORD /opt/saas/tenants/<name>/.env | cut -d= -f2)
# Sync the Postgres role password
docker exec shared-postgres psql -U root -d defaultdb -c "ALTER ROLE user_<name> WITH PASSWORD '$PASS';"
# Restart Medusa
docker restart medusa-<name>
```

---

## 📦 Upgrades

### Upgrade Medusa version

1. Edit `build_medusa_base.sh` — update the git clone branch/tag
2. Rebuild the base image: `bash services/tenant-blueprint/medusa/build_medusa_base.sh`
3. Restart existing tenant containers: `docker restart medusa-<name>`

### Upgrade the control plane

```bash
git pull
docker compose build --no-cache saas-api saas-dashboard
docker compose up -d saas-api saas-dashboard
```

---

## 🗂️ File Structure

```
.
├── .env                          ← Your secrets (never commit)
├── .env.example                  ← Template — commit this
├── docker-compose.yml            ← Platform services (Traefik, Postgres, API, Dashboard)
├── README.md                     ← This file
└── services/
    ├── admin-dashboard/
    │   ├── Dockerfile            ← Nginx + htpasswd for BasicAuth
    │   ├── nginx.conf            ← Auth + security headers
    │   ├── entrypoint.sh         ← Generates htpasswd at runtime
    │   └── dashboard.html        ← Super Admin UI
    ├── control-plane/
    │   ├── main.py               ← FastAPI: all endpoints
    │   ├── core/config.py        ← Settings (reads from .env)
    │   ├── services/
    │   │   ├── db.py             ← Postgres pool + tenant DB lifecycle
    │   │   └── provisioner.py    ← Docker Compose orchestration (multi-blueprint)
    │   └── blueprints/           ← Per-site-type container templates
    │       ├── ecommerce/        ← MedusaJS + Nginx Storefront
    │       ├── blog/             ← Ghost + Nginx Storefront
    │       ├── cms/              ← Directus + Nginx Storefront
    │       └── booking/          ← Cal.com + Nginx Storefront
    └── tenant-blueprint/medusa/
        └── build_medusa_base.sh  ← One-time base image builder
```

---

## API Reference

All write endpoints require `X-API-Key: <your-key>` header.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | None | Platform health check |
| `GET` | `/tenants` | None | List all provisioned tenants |
| `GET` | `/stores-status` | None | Live Docker container statuses |
| `POST` | `/create-store` | ✅ | Provision a new tenant (rate: 5/min) |
| `POST` | `/delete-store` | ✅ | Permanently delete a tenant |
| `POST` | `/tenants/{name}/seed-admin` | ✅ | Create/reset admin user |
| `POST` | `/tenants/{name}/suspend` | ✅ | Stop containers (keep data) |
| `POST` | `/tenants/{name}/resume` | ✅ | Restart stopped containers |
| `GET` | `/tenants/{name}/logs` | ✅ | Fetch last N Medusa log lines |
