# SaaS Blueprint Connections & AI Standards

This document outlines how new blueprints are integrated into the control plane and the technical standards for creating AI-generated templates.

## 1. Blueprint Architecture
Each blueprint is a self-contained directory in `services/control-plane/blueprints/`.

### Directory Structure
```text
blueprint-name/
├── docker-compose.yml           # Service definitions
├── storefront-nginx.conf.template # Nginx config with placeholders
└── storefront.html              # Default entry point
```

### Dynamic Placeholders
The `provisioner.py` script performs runtime substitution on these files:
- `{{TENANT_NAME}}`: Used for service internal hostnames (e.g., `medusa-{{TENANT_NAME}}`).
- `${TENANT_NAME}`: Standard environment variable for Docker Compose.
- `${DOMAIN}`: The root domain of the SaaS platform.
- `{{SAAS_PROXY_API_URL}}`: Injected into HTML files for frontend-to-proxy communication.

---

## 2. Wiring Logic (Nginx Proxy)
To ensure security and unified routing, the `storefront-nginx.conf.template` must proxy specific paths to the backend service.

| Site Type | Backend Service | Proxy Path | Standard Port |
|-----------|-----------------|------------|---------------|
| `ecommerce` | `medusa-{{TENANT_NAME}}` | `/api/`, `/store/`, `/uploads/` | 9000 |
| `blog` | `ghost-{{TENANT_NAME}}` | `/ghost/`, `/content/` | 2368 |
| `cms` | `directus-{{TENANT_NAME}}` | `/api/`, `/assets/` | 8055 |
| `booking` | `booking-{{TENANT_NAME}}` | `/api/` | 3000 |
| `static` | N/A | Local serving only | 80 |

---

## 3. AI Template Standard
Templates uploaded via the Super Admin Dashboard must follow these rules to work with the proxy:

### A. API Endpoint Discovery
Instead of hardcoding URLs, use the injected `SAAS_CONTEXT` or relative paths:
```javascript
// FETCHING DATA
// The Nginx proxy handles authentication and routing
const response = await fetch('/api/items/products'); 
```

### B. Asset Handling
- Use relative paths for local images.
- For `cms` and `ecommerce` types, images are served via `/uploads/` or `/assets/` which are automatically proxied to the correct backend volume.

### C. State Management
The platform injects a `<script id="saas-context">` tag if custom variables are needed. Templates should check for this:
```javascript
const tenantInfo = window.SAAS_CONTEXT || { name: 'default' };
```

---

## 4. Provisioning Flow (Step-by-Step)
1. **Request**: Admin hits `/create-store`.
2. **DB**: `provisioner.py` calls `provision_tenant_db` (Isolated DB/Role).
3. **Files**: Blueprint is copied to `data/tenants/{tenant_name}`.
4. **Sub**: `{{TENANT_NAME}}` is replaced in `docker-compose.yml`.
5. **Nginx**: `storefront-nginx.conf.template` is rendered to `storefront-nginx.conf`.
6. **Docker**: `docker compose up -d` executes in the tenant directory.
7. **Registry**: Tenant is added to the `tenants` table in the shared Postgres.
