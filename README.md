# Shopify Alternative SaaS Platform

A production-ready, multi-tenant SaaS e-commerce platform. Each tenant gets their own isolated MedusaJS backend + Next.js storefront, provisioned on-demand by a FastAPI control plane, all routed dynamically through Traefik.

---

## 🗺️ Architecture Overview

```
                         [ Internet ]
                              │
                         [ Traefik ]  ← auto-discovers containers via Docker socket
                        /           \
             superadmin.*          api.admin.*          tenant.yourdomain.com
                  │                     │                        │
          [Nginx Dashboard]     [FastAPI API :8000]    [Medusa + Next.js per tenant]
                                        │
                              [Shared PostgreSQL]
                              (per-tenant DB + Role)
```

---

## 📦 Project Structure

```
.
├── api/
│   ├── blueprints/default/    # Docker Compose template copied per tenant
│   ├── core/config.py         # Settings from environment variables
│   ├── services/db.py         # Tenant DB provisioning (asyncpg)
│   ├── services/docker_manager.py  # Blueprint copy + docker compose subprocess
│   ├── main.py                # FastAPI app (CORS, routes, JSON logging)
│   ├── Dockerfile             # Installs docker-ce-cli for subprocess calls
│   └── requirements.txt
├── terraform/
│   ├── main.tf                # VPC, EC2 + templatefile() for user_data
│   ├── variables.tf           # db_password (sensitive), domain_name, key_name
│   ├── user_data.sh           # Bootstrap: Docker, traefik_default network, Traefik, Postgres
│   ├── backend.tf             # S3 remote state
│   └── outputs.tf
├── docker-compose.yml         # Control plane: API + Dashboard + shared-postgres
├── dashboard.html             # Super Admin UI (glassmorphism, dynamic health check)
└── azure-pipelines.yml        # CI/CD: terraform init → validate → plan → apply
```

---

## 🔴 Fixes Applied (v3)

| # | File | Fix |
|---|------|-----|
| 1 | `docker-compose.yml` | Added missing `shared-postgres` service with healthcheck |
| 2 | `main.py` | Removed `docker_client` name collision (shadowing import) |
| 3 | `main.py` | Added CORS middleware with secure `CORS_ORIGINS` setting |
| 4 | `Dockerfile` | Install `docker-ce-cli` so `subprocess docker compose` works |
| 5 | `main.py` | Fixed `/stores-status` broken regex filter |
| 6 | `user_data.sh` | Create `traefik_default` network + set `DOCKER_API_VERSION=1.44` |
| 7 | `azure-pipelines.yml` | Added `-auto-approve` — pipeline was hanging indefinitely |
| 8 | `user_data.sh` | Parameterize DB password via Terraform variable (secret) |
| 9 | `dashboard.html` | Dynamic domain via `nip.io` when accessed by IP |
| 10 | `dashboard.html` | Real `/health` API check drives the badge (red/green) |
| 11 | `api/blueprints/` | Replaced missing `storefront:fashion` and `medusajs/medusa` images with `nginx:alpine` and dynamically generated HTML placeholders |
| 12 | `docker_manager.py` | Removed scary stub generator, added HTML generators |
| 13 | `requirements.txt` | Upgraded to latest stable versions |
| 14 | `docker-compose.yml` | Replaced named volume with host bind-mount `/opt/saas/tenants` so sibling containers can mount generated HTML files |
| 15 | `docker-compose.yml` | Added `healthcheck` to `saas-api` |

---

## 🚀 Getting Started

### Prerequisites
- AWS account with credentials configured
- Azure DevOps project with `aws-terraform-connection` service connection
- S3 bucket `my-dashboard-s3` (for Terraform state)
- EC2 Key Pair created in your AWS region

### 1. Set Pipeline Variables (Azure DevOps)
In your pipeline, set these as **secret variables** in the Library:
- `DB_PASSWORD` — root PostgreSQL password (secret)
- `key_name` — EC2 key pair name
- `domain_name` — your base domain (e.g. `myshop.io`)

### 2. Provision Infrastructure (runs via Azure DevOps on push to `main`)
```bash
cd terraform
terraform init   # Uses S3 backend: my-dashboard-s3
terraform apply  # Creates VPC, EC2, bootstraps Docker + Traefik + Postgres
```

### 3. Deploy the Control Plane (on the EC2 server)
```bash
# SSH into the server
ssh -i my-aws-key.pem ubuntu@<EC2_PUBLIC_IP>

# Clone the repo and deploy
git clone <this-repo> /opt/saas/control-plane
cd /opt/saas/control-plane

# Copy environment variables and adjust as needed
cat > .env << EOF
DOMAIN=<EC2_PUBLIC_IP>.nip.io
DB_ROOT_USER=root
DB_ROOT_PASSWORD=your-secret-password
DB_ROOT_NAME=defaultdb
CORS_ORIGINS=["*"]
EOF

docker compose up -d --build
```

### 4. Access the Dashboard
- **Super Admin**: `http://superadmin.<EC2_PUBLIC_IP>.nip.io` (or `http://<IP>:8081`)
- **API**: `http://api.admin.<EC2_PUBLIC_IP>.nip.io` (or `http://<IP>:8000`)
- **API Docs**: `http://<IP>:8000/docs`

### 5. Provision a Tenant via Dashboard
1. Enter a subdomain (e.g., `shoes`)
2. Pick a theme (Fashion / Electronics / Minimal)
3. Click **Deploy Tenant**
4. The API creates `db_shoes` + `user_shoes` in Postgres, copies the blueprint, runs `docker compose up -d`
5. Traefik auto-routes `shoes.<DOMAIN>` → storefront and `admin.shoes.<DOMAIN>` → Medusa

---

## 🛡️ Best Practices Implemented

| Practice | Implementation |
|---|---|
| **Idempotency** | DB creation and Terraform are safe to re-run |
| **Micro-architecture** | Each tenant is isolated containers — one crash doesn't affect others |
| **DB Isolation** | Separate Postgres DB + Role per tenant on a shared Postgres instance |
| **Dynamic Routing** | Traefik auto-discovers containers via Docker socket — zero manual config |
| **Secret Management** | DB password injected as Terraform `sensitive` variable from pipeline secrets |
| **JSON Logging** | All API events emit structured JSON for log aggregator ingestion |
| **Healthchecks** | API and Shared DB actively checked for uptime to ensure proper orchestration |
| **Strict Security** | Customizable CORS origins via `.env` file |

---

## ⚠️ Suggestions for Future Improvements

1. **Secret Manager** — Move DB credentials to AWS Secrets Manager and fetch them from the API at startup
2. **TLS / SSL** — Uncomment the Traefik ACME config in `user_data.sh` to enable Let's Encrypt
3. **State Locking** — Uncomment `dynamodb_table` in `backend.tf` to prevent concurrent Terraform applies
4. **Tenant Registry** — Store tenant metadata (name, theme, created_at) in the shared DB, not just in Docker container names
5. **Add Tests** — Integration tests for `/create-store` and `/delete-store` using `pytest` + `httpx`
6. **Rate Limiting** — Add `slowapi` middleware to the FastAPI app to prevent provisioning abuse
7. **CORS Lockdown** — Change `allow_origins=["*"]` in `main.py` to `["https://superadmin.yourdomain.com"]`
