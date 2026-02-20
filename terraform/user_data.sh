#!/bin/bash
set -e

# Logging
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting SaaS Platform Initialization..."

# Update and install dependencies
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Set up the Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable and start Docker
systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

# Setup basic directory structure for SaaS
mkdir -p /opt/saas/traefik
mkdir -p /opt/saas/postgres
mkdir -p /opt/saas/api

# Create Traefik compose
cat << 'EOF' > /opt/saas/traefik/docker-compose.yml
services:
  traefik:
    image: traefik:v2.10
    container_name: traefik
    restart: always
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      # Cloudflare Setup for SSL (to be uncommented when domain is verified)
      # - "--certificatesresolvers.myresolver.acme.dnschallenge=true"
      # - "--certificatesresolvers.myresolver.acme.dnschallenge.provider=cloudflare"
      # - "--certificatesresolvers.myresolver.acme.email=${SSL_EMAIL}"
      # - "--certificatesresolvers.myresolver.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./letsencrypt:/letsencrypt"
EOF

# Create PostgreSQL shared instance
cat << 'EOF' > /opt/saas/postgres/docker-compose.yml
services:
  postgres:
    image: postgres:15-alpine
    container_name: shared-postgres
    restart: always
    environment:
      POSTGRES_USER: root
      POSTGRES_PASSWORD: supersecretpassword123
      POSTGRES_DB: defaultdb
    volumes:
      - pg-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  pg-data:
EOF

# Start the base services
cd /opt/saas/traefik && docker compose up -d
cd /opt/saas/postgres && docker compose up -d

echo "Initialization Complete!"
