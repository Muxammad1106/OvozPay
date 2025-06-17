# OvozPay Docker Management Makefile

.PHONY: help build up down restart logs clean ssl backup restore

# Default target
help: ## Show this help message
	@echo "OvozPay Docker Management Commands"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Environment setup
setup: ## Setup environment file from example
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "Created .env file from example. Please edit it with your configuration."; \
	else \
		echo ".env file already exists"; \
	fi

# Build and deployment
build: ## Build all Docker images
	docker-compose build --no-cache

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

stop: ## Stop all services (alias for down)
	docker-compose down

restart: ## Restart all services
	docker-compose restart

# Development commands
dev: ## Start in development mode with live reload
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

shell: ## Access Django shell
	docker-compose exec django_app python manage.py shell

migrate: ## Run Django migrations
	docker-compose exec django_app python manage.py migrate

makemigrations: ## Create Django migrations
	docker-compose exec django_app python manage.py makemigrations

collectstatic: ## Collect static files
	docker-compose exec django_app python manage.py collectstatic --noinput

superuser: ## Create Django superuser
	docker-compose exec django_app python manage.py createsuperuser

# Logs and monitoring
logs: ## Show logs for all services
	docker-compose logs -f

logs-django: ## Show Django logs
	docker-compose logs -f django_app

logs-bot: ## Show Telegram bot logs
	docker-compose logs -f telegram_bot

logs-nginx: ## Show Nginx logs
	docker-compose logs -f nginx

logs-ocr: ## Show OCR service logs
	docker-compose logs -f tesseract_ocr

logs-whisper: ## Show Whisper service logs
	docker-compose logs -f whisper_voice

ps: ## Show running services
	docker-compose ps

top: ## Show service resource usage
	docker-compose top

# Database management
db-shell: ## Access PostgreSQL shell
	docker-compose exec postgres psql -U ovozpay -d ovozpay_db

db-backup: ## Backup database
	@mkdir -p backups
	docker-compose exec postgres pg_dump -U ovozpay ovozpay_db > backups/db_backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Database backup created in backups/"

db-restore: ## Restore database (usage: make db-restore FILE=backup.sql)
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make db-restore FILE=backup.sql"; \
		exit 1; \
	fi
	docker-compose exec -T postgres psql -U ovozpay -d ovozpay_db < $(FILE)

# SSL and security
ssl: ## Setup SSL certificates
	DOMAIN=$(DOMAIN) EMAIL=$(EMAIL) ./scripts/ssl-setup.sh

ssl-renew: ## Renew SSL certificates
	./scripts/ssl-renew.sh

# Testing
test: ## Run tests
	docker-compose exec django_app python manage.py test

test-ocr: ## Test OCR service
	curl -X GET http://localhost:8001/health

test-whisper: ## Test Whisper service
	curl -X GET http://localhost:8002/health

test-all: ## Test all services
	@echo "Testing Django..."
	@curl -f http://localhost:8000/admin/ > /dev/null && echo "✅ Django OK" || echo "❌ Django failed"
	@echo "Testing OCR..."
	@curl -f http://localhost:8001/health > /dev/null && echo "✅ OCR OK" || echo "❌ OCR failed"
	@echo "Testing Whisper..."
	@curl -f http://localhost:8002/health > /dev/null && echo "✅ Whisper OK" || echo "❌ Whisper failed"
	@echo "Testing Nginx..."
	@curl -f http://localhost/health > /dev/null && echo "✅ Nginx OK" || echo "❌ Nginx failed"

# Cleanup
clean: ## Clean up Docker resources
	docker-compose down --volumes --remove-orphans
	docker system prune -f
	docker volume prune -f

clean-all: ## Clean up everything including images
	docker-compose down --volumes --remove-orphans
	docker system prune -af
	docker volume prune -f

# Full deployment
deploy: ## Full deployment (build, migrate, start)
	@echo "🚀 Starting full deployment..."
	make build
	make up
	@sleep 10
	make migrate
	make collectstatic
	@echo "✅ Deployment completed!"

deploy-ssl: ## Deploy with SSL setup
	@echo "🚀 Starting deployment with SSL..."
	make deploy
	make ssl
	@echo "✅ SSL deployment completed!"

# Production commands
prod-deploy: ## Production deployment
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Run 'make setup' first"; \
		exit 1; \
	fi
	@echo "🚀 Production deployment starting..."
	./deploy.sh

prod-ssl: ## Production deployment with SSL
	@echo "🚀 Production deployment with SSL..."
	./deploy.sh --ssl

# Health checks
health: ## Check service health
	@echo "🏥 Checking service health..."
	@docker-compose ps
	@echo ""
	@make test-all

# Quick start
quick-start: setup deploy health ## Quick start for development

# Update
update: ## Update and restart services
	git pull origin main
	docker-compose pull
	make build
	make restart
	make migrate

# Monitoring
monitor: ## Open monitoring dashboard
	@echo "📊 Opening monitoring..."
	@echo "Flower: http://localhost:5555"
	@echo "Nginx Status: http://localhost:8080/nginx_status" 