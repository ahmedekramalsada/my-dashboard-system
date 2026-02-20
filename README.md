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
_Status: Pending_
- Pre-configured `docker-compose` setups for MedusaJS backends and dynamic Next.js storefronts representing different themes (e.g., Fashion, Electronics).

### 🖥️ Phase 4: Super Admin Dashboard
_Status: Pending_
- Visual control panel representing the "Command Center" of the SaaS platform to monitor tenants, create new stores, and deploy themes.

### 🧙‍♂️ Phase 5: The Magic Flow
_Status: Pending_
- Tying it all together ensuring an end-to-end fully automated provisioning flow. Within seconds of dashboard submission, a new tenant is assigned a DB schema, subdomains mapped by Traefik, and complete containers spun up.

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

_Note: The `user_data.sh` applies Docker, Traefik, and PostgreSQL automatically once the EC2 instance is active._
