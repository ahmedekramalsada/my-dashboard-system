FROM nginx:alpine

# Copy the modern nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the static dashboard HTML
COPY dashboard.html /usr/share/nginx/html/index.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
