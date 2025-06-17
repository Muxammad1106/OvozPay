#!/bin/bash
# SSL Certificate Setup Script for OvozPay

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
DOMAIN="${DOMAIN:-ovozpay.uz}"
EMAIL="${SSL_EMAIL:-admin@ovozpay.uz}"

echo -e "${BLUE}🔒 OvozPay SSL Certificate Setup${NC}"
echo "================================"

# Check if domain is provided
if [ -z "$DOMAIN" ]; then
    echo -e "${RED}❌ DOMAIN environment variable not set${NC}"
    echo "Usage: DOMAIN=your-domain.com EMAIL=your@email.com ./ssl-setup.sh"
    exit 1
fi

if [ -z "$EMAIL" ]; then
    echo -e "${RED}❌ EMAIL environment variable not set${NC}"
    echo "Usage: DOMAIN=your-domain.com EMAIL=your@email.com ./ssl-setup.sh"
    exit 1
fi

echo -e "${BLUE}📋 Configuration:${NC}"
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo ""

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${RED}❌ Docker services are not running. Please start them first with:${NC}"
    echo "docker-compose up -d"
    exit 1
fi

# Create certificate directory
mkdir -p certbot_conf certbot_www

# Stop nginx temporarily for standalone certificate
echo -e "${BLUE}🛑 Stopping nginx temporarily...${NC}"
docker-compose stop nginx

# Request certificate
echo -e "${BLUE}📜 Requesting SSL certificate from Let's Encrypt...${NC}"
docker-compose run --rm \
    -p 80:80 \
    certbot certonly \
    --standalone \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d $DOMAIN

# Start nginx again
echo -e "${BLUE}🚀 Starting nginx with SSL...${NC}"
docker-compose start nginx

# Test certificate
echo -e "${BLUE}🧪 Testing SSL certificate...${NC}"
sleep 5

if curl -fsS "https://$DOMAIN/health" &> /dev/null; then
    echo -e "${GREEN}✅ SSL certificate is working correctly!${NC}"
else
    echo -e "${YELLOW}⚠️  SSL test failed. Check nginx logs:${NC}"
    echo "docker-compose logs nginx"
fi

# Set up auto-renewal
echo -e "${BLUE}🔄 Setting up auto-renewal...${NC}"

# Create renewal script
cat > scripts/ssl-renew.sh << 'EOF'
#!/bin/bash
# SSL Certificate Auto-Renewal Script

echo "$(date): Starting SSL certificate renewal check..."

# Renew certificates
docker-compose run --rm certbot renew --quiet

# Reload nginx if certificates were renewed
if [ $? -eq 0 ]; then
    echo "$(date): Certificates renewed, reloading nginx..."
    docker-compose exec nginx nginx -s reload
fi

echo "$(date): SSL renewal check completed"
EOF

chmod +x scripts/ssl-renew.sh

echo -e "${GREEN}🎉 SSL setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo "1. Test your site: https://$DOMAIN"
echo "2. Set up auto-renewal cron job:"
echo "   crontab -e"
echo "   Add: 0 3 * * * /path/to/ovozpay/scripts/ssl-renew.sh >> /var/log/ssl-renew.log 2>&1"
echo ""
echo -e "${BLUE}🔧 Useful commands:${NC}"
echo "• Manual renewal: ./scripts/ssl-renew.sh"
echo "• Check certificate: openssl x509 -in /path/to/cert.pem -text -noout"
echo "• Nginx reload: docker-compose exec nginx nginx -s reload" 