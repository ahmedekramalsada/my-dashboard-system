#!/bin/bash
# =============================================================================
# SaaS Platform Bootstrap — runs once on EC2 first boot via Terraform user_data
# All variables (${db_password}, ${domain_name}) are injected by Terraform templatefile()
# =============================================================================
set -euo pipefail

# Stream all output to both a log file and the system journal
exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1

echo "[$(date)] Starting SaaS Platform Initialization..."

# -----------------------------------------------------------------------------
# 1. Install Docker Engine
# -----------------------------------------------------------------------------
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

# -----------------------------------------------------------------------------
# 2. Create shared Docker network for Traefik + all services
#    (must exist before any compose file that references it as external)
# -----------------------------------------------------------------------------
docker network create traefik_default || echo "Network 'traefik_default' already exists — skipping."

# -----------------------------------------------------------------------------
# 3. Directory structure
# -----------------------------------------------------------------------------
mkdir -p /opt/saas/traefik/letsencrypt
mkdir -p /opt/saas/postgres
mkdir -p /opt/saas/tenants   # Tenant compose files will be written here by the API

# -----------------------------------------------------------------------------
# 4. Traefik Reverse Proxy
# -----------------------------------------------------------------------------
cat << 'EOF' > /opt/saas/traefik/docker-compose.yml
services:
  traefik:
    image: traefik:v2.11
    container_name: traefik
    restart: always
    environment:
      - DOCKER_API_VERSION=1.44
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      # Uncomment and configure when your domain is pointed at this server:
      # - "--certificatesresolvers.myresolver.acme.dnschallenge=true"
      # - "--certificatesresolvers.myresolver.acme.dnschallenge.provider=cloudflare"
      # - "--certificatesresolvers.myresolver.acme.email=you@example.com"
      # - "--certificatesresolvers.myresolver.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./letsencrypt:/letsencrypt"
    networks:
      - traefik_default

networks:
  traefik_default:
    external: true
EOF

# -----------------------------------------------------------------------------
# 5. Shared PostgreSQL — uses injected password from Terraform variable
# -----------------------------------------------------------------------------
cat << EOF > /opt/saas/postgres/docker-compose.yml
services:
  postgres:
    image: postgres:15-alpine
    container_name: shared-postgres
    restart: always
    environment:
      POSTGRES_USER: root
      POSTGRES_PASSWORD: ${db_password}
      POSTGRES_DB: defaultdb
    volumes:
      - pg-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U root -d defaultdb"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - traefik_default

volumes:
  pg-data:

networks:
  traefik_default:
    external: true
EOF

# -----------------------------------------------------------------------------
# 6. Start base services
# -----------------------------------------------------------------------------
echo "[$(date)] Starting Traefik..."
cd /opt/saas/traefik && docker compose up -d

echo "[$(date)] Starting PostgreSQL..."
cd /opt/saas/postgres && docker compose up -d

echo "[$(date)] Initialization Complete! Domain: ${domain_name}"
