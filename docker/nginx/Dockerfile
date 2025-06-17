# Nginx with SSL support for OvozPay
FROM nginx:alpine

# Install additional packages
RUN apk add --no-cache \
    curl \
    openssl \
    certbot \
    certbot-nginx

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# Create necessary directories
RUN mkdir -p /var/www/certbot \
    /etc/nginx/ssl \
    /var/log/nginx

# Create self-signed certificate for initial setup
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/selfsigned.key \
    -out /etc/nginx/ssl/selfsigned.crt \
    -subj "/C=UZ/ST=Tashkent/L=Tashkent/O=OvozPay/CN=ovozpay.uz"

# Set proper permissions
RUN chown -R nginx:nginx /var/www/certbot \
    && chmod -R 755 /var/www/certbot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"] 