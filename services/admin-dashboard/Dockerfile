FROM nginx:1.27-alpine

# Install apache2-utils for htpasswd
RUN apk add --no-cache apache2-utils

# Copy Nginx config and dashboard HTML
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY dashboard.html /usr/share/nginx/html/index.html

# Copy and set up entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

# Use entrypoint to generate htpasswd then start nginx
ENTRYPOINT ["/entrypoint.sh"]
