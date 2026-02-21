#!/bin/sh
# Generates htpasswd from env vars at container start, then launches Nginx.
# Required env vars: DASHBOARD_USER, DASHBOARD_PASS
set -e

if [ -z "$DASHBOARD_USER" ] || [ -z "$DASHBOARD_PASS" ]; then
    echo "ERROR: DASHBOARD_USER and DASHBOARD_PASS must be set."
    exit 1
fi

echo "==> Generating htpasswd for user: $DASHBOARD_USER"
htpasswd -bc /etc/nginx/.htpasswd "$DASHBOARD_USER" "$DASHBOARD_PASS"
echo "==> htpasswd generated. Launching Nginx..."

exec nginx -g "daemon off;"
