#!/bin/bash
# OvozPay Docker Deployment Script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="ovozpay"
DOMAIN="${DOMAIN:-ovozpay.uz}"
EMAIL="${SSL_EMAIL:-admin@ovozpay.uz}"

echo -e "${BLUE}🚀 OvozPay Docker Deployment Script${NC}"
echo "=================================="

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from example...${NC}"
    if [ -f "env.example" ]; then
        cp env.example .env
        echo -e "${RED}❌ Please edit .env file with your configuration and run again${NC}"
        exit 1
    else
        echo -e "${RED}❌ env.example not found. Please create .env file manually${NC}"
        exit 1
    fi
fi

# Check if required environment variables are set
echo -e "${BLUE}🔍 Checking environment variables...${NC}"
source .env

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ "$TELEGRAM_BOT_TOKEN" = "your-telegram-bot-token-here" ]; then
    echo -e "${RED}❌ TELEGRAM_BOT_TOKEN not set in .env file${NC}"
    exit 1
fi

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "your-super-secret-key-change-this-in-production" ]; then
    echo -e "${YELLOW}⚠️  Using default SECRET_KEY. Please change it in .env file${NC}"
fi

echo -e "${GREEN}✅ Environment variables check passed${NC}"

# Check Docker and Docker Compose
echo -e "${BLUE}🐳 Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found. Please install Docker Compose first${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose found${NC}"

# Create necessary directories
echo -e "${BLUE}📁 Creating necessary directories...${NC}"
mkdir -p postgres-init
mkdir -p backend/logs
mkdir -p docker/nginx/ssl

# Generate htpasswd for Flower if not exists
if [ ! -f "docker/nginx/.htpasswd" ]; then
    echo -e "${BLUE}🔐 Generating Flower authentication...${NC}"
    mkdir -p docker/nginx
    htpasswd -bc docker/nginx/.htpasswd ${FLOWER_USER:-admin} ${FLOWER_PASSWORD:-admin123}
fi

# Stop existing containers
echo -e "${BLUE}🛑 Stopping existing containers...${NC}"
docker-compose down --volumes --remove-orphans || true

# Build and start services
echo -e "${BLUE}🏗️  Building Docker images...${NC}"
docker-compose build --no-cache

echo -e "${BLUE}🚀 Starting services...${NC}"
docker-compose up -d postgres redis

# Wait for database to be ready
echo -e "${BLUE}⏳ Waiting for database to be ready...${NC}"
until docker-compose exec -T postgres pg_isready -U ${POSTGRES_USER:-ovozpay} -d ${POSTGRES_DB:-ovozpay_db}; do
    echo "Waiting for database..."
    sleep 2
done

echo -e "${GREEN}✅ Database is ready${NC}"

# Run Django migrations
echo -e "${BLUE}🔄 Running Django migrations...${NC}"
docker-compose run --rm django_app python manage.py migrate

# Create superuser if needed
echo -e "${BLUE}👤 Creating Django superuser...${NC}"
docker-compose run --rm django_app python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@ovozpay.uz', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF

# Collect static files
echo -e "${BLUE}📦 Collecting static files...${NC}"
docker-compose run --rm django_app python manage.py collectstatic --noinput

# Start all services
echo -e "${BLUE}🚀 Starting all services...${NC}"
docker-compose up -d

# Wait for services to start
echo -e "${BLUE}⏳ Waiting for services to start...${NC}"
sleep 30

# Check service health
echo -e "${BLUE}🏥 Checking service health...${NC}"

# Check Django
if curl -f http://localhost:8000/admin/ &> /dev/null; then
    echo -e "${GREEN}✅ Django backend is running${NC}"
else
    echo -e "${YELLOW}⚠️  Django backend might not be fully ready yet${NC}"
fi

# Check OCR service
if curl -f http://localhost:8001/health &> /dev/null; then
    echo -e "${GREEN}✅ OCR service is running${NC}"
else
    echo -e "${YELLOW}⚠️  OCR service might not be fully ready yet${NC}"
fi

# Check Whisper service
if curl -f http://localhost:8002/health &> /dev/null; then
    echo -e "${GREEN}✅ Whisper service is running${NC}"
else
    echo -e "${YELLOW}⚠️  Whisper service might not be fully ready yet${NC}"
fi

# Check Nginx
if curl -f http://localhost/health &> /dev/null; then
    echo -e "${GREEN}✅ Nginx is running${NC}"
else
    echo -e "${YELLOW}⚠️  Nginx might not be fully ready yet${NC}"
fi

# SSL Certificate setup (optional)
if [ "$1" = "--ssl" ]; then
    echo -e "${BLUE}🔒 Setting up SSL certificate...${NC}"
    
    # Stop nginx temporarily
    docker-compose stop nginx
    
    # Obtain certificate
    docker-compose run --rm certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        -d $DOMAIN
    
    # Start nginx again
    docker-compose start nginx
    
    echo -e "${GREEN}✅ SSL certificate setup completed${NC}"
fi

# Display status
echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo "======================================"
echo -e "${BLUE}📊 Service URLs:${NC}"
echo "🌐 Main site: http://localhost (or https://$DOMAIN if SSL enabled)"
echo "🔧 Django Admin: http://localhost/admin/ (admin/admin123)"
echo "🖼️  OCR Service: http://localhost:8001"
echo "🗣️  Voice Service: http://localhost:8002"
echo "🌸 Flower Monitoring: http://localhost:5555"
echo ""
echo -e "${BLUE}📋 Useful commands:${NC}"
echo "• View logs: docker-compose logs -f [service_name]"
echo "• Restart services: docker-compose restart"
echo "• Stop services: docker-compose down"
echo "• View status: docker-compose ps"
echo ""
echo -e "${YELLOW}⚠️  Don't forget to:${NC}"
echo "1. Change default passwords in .env file"
echo "2. Set up proper TELEGRAM_BOT_TOKEN"
echo "3. Configure domain DNS if using SSL"
echo "4. Set up backup strategy"

exit 0 