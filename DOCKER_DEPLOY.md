# 🐳 OvozPay Docker Deployment Guide

Полное руководство по развертыванию OvozPay с использованием Docker и Docker Compose.

## 📋 Содержание

- [Быстрый старт](#-быстрый-старт)
- [Системные требования](#-системные-требования)
- [Структура проекта](#-структура-проекта)
- [Конфигурация](#️-конфигурация)
- [Развертывание](#-развертывание)
- [SSL сертификаты](#-ssl-сертификаты)
- [Мониторинг](#-мониторинг)
- [Управление](#️-управление)
- [Резервное копирование](#-резервное-копирование)
- [Устранение неполадок](#-устранение-неполадок)

## ⚡ Быстрый старт

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/your-username/ovozpay.git
cd ovozpay

# 2. Настройте окружение
make setup
# Отредактируйте .env файл с вашими настройками

# 3. Разверните проект
make deploy

# 4. (Опционально) Настройте SSL
DOMAIN=ovozpay.uz EMAIL=admin@ovozpay.uz make ssl
```

## 🖥️ Системные требования

### Минимальные требования:
- **CPU:** 2 ядра
- **RAM:** 4 GB
- **Диск:** 20 GB свободного места
- **ОС:** Ubuntu 20.04+, CentOS 8+, Debian 11+

### Рекомендуемые требования:
- **CPU:** 4 ядра
- **RAM:** 8 GB
- **Диск:** 50 GB SSD
- **ОС:** Ubuntu 22.04 LTS

### Программное обеспечение:
- Docker 24.0+
- Docker Compose 2.0+
- Git
- Make (опционально)

## 📁 Структура проекта

```
ovozpay/
├── 📁 backend/                  # Django приложение
│   ├── 📄 Dockerfile           # Dockerfile для Django
│   ├── 📄 Dockerfile.bot       # Dockerfile для Telegram бота
│   └── 📄 requirements.txt     # Python зависимости
├── 📁 docker/                  # Docker сервисы
│   ├── 📁 nginx/              # Nginx конфигурация
│   ├── 📁 tesseract/          # OCR сервис
│   └── 📁 whisper/            # Voice recognition сервис
├── 📁 scripts/                # Скрипты развертывания
├── 📄 docker-compose.yml      # Основная конфигурация
├── 📄 env.example             # Пример переменных окружения
├── 📄 deploy.sh              # Скрипт автоматического развертывания
├── 📄 Makefile               # Команды управления
└── 📄 DOCKER_DEPLOY.md       # Данное руководство
```

## ⚙️ Конфигурация

### 1. Создание .env файла

```bash
cp env.example .env
```

### 2. Редактирование .env

```bash
# Обязательные параметры
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
SECRET_KEY=your-super-secret-key
DOMAIN=ovozpay.uz
SSL_EMAIL=admin@ovozpay.uz

# База данных
POSTGRES_PASSWORD=secure-password
REDIS_PASSWORD=redis-password

# Безопасность
FLOWER_USER=admin
FLOWER_PASSWORD=flower-password
```

### 3. Настройка Telegram бота

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите токен
3. Добавьте токен в `.env` файл

## 🚀 Развертывание

### Автоматическое развертывание

```bash
# Полное развертывание
./deploy.sh

# С SSL сертификатами
./deploy.sh --ssl
```

### Ручное развертывание

```bash
# 1. Сборка образов
make build

# 2. Запуск сервисов
make up

# 3. Миграции базы данных
make migrate

# 4. Сбор статических файлов
make collectstatic

# 5. Создание суперпользователя
make superuser
```

## 🔒 SSL сертификаты

### Автоматическая настройка

```bash
DOMAIN=ovozpay.uz EMAIL=admin@ovozpay.uz make ssl
```

### Ручная настройка

```bash
# 1. Остановка nginx
docker-compose stop nginx

# 2. Получение сертификата
docker-compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email admin@ovozpay.uz \
    --agree-tos \
    --no-eff-email \
    -d ovozpay.uz

# 3. Запуск nginx
docker-compose start nginx
```

### Автоматическое обновление

Добавьте в crontab:

```bash
crontab -e
# Добавьте строку:
0 3 * * * /path/to/ovozpay/scripts/ssl-renew.sh >> /var/log/ssl-renew.log 2>&1
```

## 📊 Мониторинг

### Доступные интерфейсы

| Сервис | URL | Описание |
|--------|-----|----------|
| Django Admin | http://localhost/admin/ | Административная панель |
| Flower | http://localhost:5555 | Мониторинг Celery |
| OCR API | http://localhost:8001 | OCR сервис документация |
| Voice API | http://localhost:8002 | Voice сервис документация |
| Nginx Status | http://localhost:8080/nginx_status | Статистика Nginx |

### Команды мониторинга

```bash
# Статус сервисов
make ps

# Логи всех сервисов
make logs

# Логи конкретного сервиса
make logs-django
make logs-bot
make logs-nginx

# Использование ресурсов
make top

# Проверка здоровья
make health
```

## 🛠️ Управление

### Основные команды

```bash
# Запуск
make up

# Остановка
make down

# Перезапуск
make restart

# Обновление
make update

# Очистка
make clean
```

### Работа с базой данных

```bash
# Доступ к PostgreSQL
make db-shell

# Резервная копия
make db-backup

# Восстановление
make db-restore FILE=backup.sql

# Django команды
make migrate
make makemigrations
make shell
```

### Масштабирование

Увеличение количества worker'ов:

```bash
# Редактирование docker-compose.yml
docker-compose up -d --scale celery_worker=3
```

## 💾 Резервное копирование

### Автоматическое резервное копирование

```bash
# База данных
make db-backup

# Медиа файлы
tar -czf backups/media_$(date +%Y%m%d_%H%M%S).tar.gz backend/media/

# Полное резервное копирование
./scripts/backup.sh
```

### Стратегия резервного копирования

1. **Ежедневно:** База данных
2. **Еженедельно:** Медиа файлы
3. **Ежемесячно:** Полный образ системы

### Восстановление

```bash
# База данных
make db-restore FILE=backups/db_backup_20241201_120000.sql

# Медиа файлы
tar -xzf backups/media_20241201_120000.tar.gz -C backend/
```

## 🔧 Устранение неполадок

### Общие проблемы

#### 1. Сервисы не запускаются

```bash
# Проверка логов
make logs

# Проверка образов
docker images

# Пересборка
make clean
make build
make up
```

#### 2. База данных недоступна

```bash
# Проверка статуса PostgreSQL
docker-compose exec postgres pg_isready

# Перезапуск базы данных
docker-compose restart postgres

# Проверка логов
make logs-postgres
```

#### 3. AI сервисы не работают

```bash
# Проверка OCR
curl http://localhost:8001/health

# Проверка Whisper
curl http://localhost:8002/health

# Проверка логов
make logs-ocr
make logs-whisper
```

#### 4. SSL проблемы

```bash
# Проверка сертификата
openssl x509 -in /etc/letsencrypt/live/ovozpay.uz/fullchain.pem -text -noout

# Обновление сертификата
make ssl-renew

# Проверка конфигурации Nginx
docker-compose exec nginx nginx -t
```

### Производительность

#### Оптимизация памяти

```bash
# Ограничение памяти для контейнеров
# В docker-compose.yml добавьте:
deploy:
  resources:
    limits:
      memory: 512M
```

#### Мониторинг ресурсов

```bash
# Использование CPU и памяти
docker stats

# Использование диска
df -h
docker system df
```

### Логирование

#### Настройка уровня логирования

В `.env` файле:

```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

#### Ротация логов

```bash
# Настройка логротate
sudo nano /etc/logrotate.d/ovozpay
```

### Безопасность

#### Обновление безопасности

```bash
# Обновление образов
docker-compose pull
make restart

# Проверка уязвимостей
docker scout cves
```

#### Файрвол

```bash
# Базовая настройка UFW
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 📞 Поддержка

### Полезные ссылки

- [Docker Documentation](https://docs.docker.com/)
- [Django Documentation](https://docs.djangoproject.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

### Контакты

- **Email:** support@ovozpay.uz
- **Telegram:** @ovozpay_support
- **GitHub Issues:** [Issues](https://github.com/your-username/ovozpay/issues)

---

**© 2024 OvozPay. Все права защищены.** 