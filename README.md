# Shopify Alternative SaaS Platform

Welcome to the ultimate SaaS Multi-tenant E-commerce platform repository. This project is built using a micro-architecture approach targeting immense scalability, strict tenant isolation, and zero-downtime deployments.

## 🗺️ Master Architecture & Phases

### 🔄 Phase 0: CI/CD & Automation (Azure DevOps)
_Status: Pending_
- **Platform**: Azure DevOps for Repositories, Pipelines, and Artifacts.
- **Pipelines**: Automated flows to validate, plan, and apply Terraform configurations, and deploy the FastAPI backend.

### ☁️ Phase 1: Base Infrastructure (The Groundwork)
_Status: Completed (Terraform Code ready)_
- **Infrastructure as Code**: Terraform scripts to provision AWS VPC, Subnets, Internet Gateway, and an EC2 Instance.
- **Bootstrapping**: An automated `user_data.sh` script that installs Docker, Docker Compose, and provisions the initial reverse proxy (Traefik) and the shared database (PostgreSQL 15).

### ⚙️ Phase 2: Core API (The Provisioning Engine)
_Status: Completed_
- **Framework**: Python 3.11+ using FastAPI (Async).
- **Control**: Integrating the `docker` Python SDK to programmatically spawn, mutate, and destroy tenant storefronts and schemas on-demand.

### 🍱 Phase 3: Blueprints (Docker Templates)
_Status: Completed_
- Pre-configured `docker-compose` setups for MedusaJS backends and dynamic Next.js storefronts representing different themes (e.g., Fashion, Electronics).

### 🖥️ Phase 4: Super Admin Dashboard
_Status: Completed_
- Visual control panel (HTML/TailwindJS/Glassmorphism) representing the "Command Center" of the SaaS platform to monitor tenants, create new stores, and deploy themes.

### 🧙‍♂️ Phase 5: The Magic Flow
_Status: Completed_
- **Control Plane**: A root `docker-compose.yml` that securely runs the Provisioning API (with access to the Docker socket) and serves the Dashboard via Nginx.
- **Routing**: End-to-end Traefik configuration handles routing for `superadmin.domain.com`, `api.admin.domain.com` out of the box.

---

## Getting Started

### 1. Provisioning Infrastructure
Infrastructure provisioning is primarily intended to be handled via **Azure DevOps Pipelines**, but for local testing:

```bash
cd terraform
# Remember to configure AWS credentials to access the 'my-dashboard-s3' backend
terraform init
terraform apply
```
This will set up the entire Base Infrastructure on your AWS account, securely storing the state in the `my-dashboard-s3` S3 bucket.

### 2. Deploying the Control Plane (The Dashboard & API)
Once the server is running, you deploy the core SaaS engine:

```bash
# Set your domain first
export DOMAIN="yourdomain.com"

# Spin up the API and Dashboard
docker compose up -d --build
```
This starts:
- The Super Admin Dashboard at `http://superadmin.yourdomain.com` (Served via Nginx)
- The Provisioning Engine API at `http://api.admin.yourdomain.com` (FastAPI)

### 3. Creating Tenants (The Flow)
1. Go to your Super Admin Dashboard.
2. Enter a subdomain (e.g., `shoes`) and choose a theme.
3. Click "Deploy".
4. The API connects to the shared PostgreSQL, creates a database `db_shoes` and user `user_shoes`.
5. The API copies the Medusa + Next.js blueprint from `/api/blueprints`, templates the `.env` with the new DB credentials.
6. The API runs `docker compose up -d` for that specific tenant.
7. Traefik automatically detects the new containers. The tenant is instantly live at `shoes.yourdomain.com` and `admin.shoes.yourdomain.com`.

### 🛡️ Best Practices Implemented
- **Idempotency**: Terraform and the Database creation scripts are idempotent and safe to re-run.
- **Micro-architecture**: Stores are completely separate containers, not a monolithic framework. If one store crashes, others are unaffected.
- **DB Isolation**: A single shared Postgres instance dynamically partitions data using separate Roles and Databases per tenant, saving massive amounts of RAM vs spinning up Postgres per tenant.
- **Dynamic Routing**: Traefik removes the need to ever manually touch Nginx or Apache configs when a new tenant signs up.
