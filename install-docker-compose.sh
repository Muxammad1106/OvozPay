#!/bin/bash
# Установка Docker Compose на Ubuntu/Debian сервер

set -e

echo "🐳 Установка Docker Compose..."

# Проверяем архитектуру системы
ARCH=$(uname -m)
case $ARCH in
    x86_64) ARCH="x86_64" ;;
    aarch64) ARCH="aarch64" ;;
    armv7l) ARCH="armv7" ;;
    *) echo "Неподдерживаемая архитектура: $ARCH"; exit 1 ;;
esac

echo "Архитектура: $ARCH"

# Скачиваем последнюю версию Docker Compose
DOCKER_COMPOSE_VERSION="v2.24.0"
echo "Скачивание Docker Compose $DOCKER_COMPOSE_VERSION..."

sudo curl -L "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-linux-$ARCH" -o /usr/local/bin/docker-compose

# Делаем исполняемым
sudo chmod +x /usr/local/bin/docker-compose

# Создаем символическую ссылку для совместимости
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Проверяем установку
echo "Проверка установки..."
docker-compose --version

echo "✅ Docker Compose успешно установлен!" 