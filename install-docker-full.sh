#!/bin/bash
# Полная установка Docker и Docker Compose на Ubuntu/Debian

set -e

echo "🚀 Полная установка Docker + Docker Compose"
echo "==========================================="

# Обновление системы
echo "📦 Обновление системы..."
sudo apt update

# Установка зависимостей
echo "🔧 Установка зависимостей..."
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Добавление Docker GPG ключа
echo "🔑 Добавление Docker GPG ключа..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавление Docker репозитория
echo "📦 Добавление Docker репозитория..."
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Обновление списка пакетов
sudo apt update

# Установка Docker
echo "🐳 Установка Docker..."
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Добавление пользователя в группу docker
echo "👤 Добавление пользователя в группу docker..."
sudo usermod -aG docker $USER

# Запуск и включение Docker
echo "🚀 Запуск Docker..."
sudo systemctl start docker
sudo systemctl enable docker

# Установка Docker Compose (standalone)
echo "🔧 Установка Docker Compose standalone..."
DOCKER_COMPOSE_VERSION="v2.24.0"
ARCH=$(uname -m)

case $ARCH in
    x86_64) ARCH="x86_64" ;;
    aarch64) ARCH="aarch64" ;;
    armv7l) ARCH="armv7" ;;
    *) echo "Неподдерживаемая архитектура: $ARCH"; exit 1 ;;
esac

sudo curl -L "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-linux-$ARCH" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Создание символической ссылки
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Проверка установки
echo "✅ Проверка установки..."
echo "Docker версия:"
docker --version
echo "Docker Compose версия:"
docker-compose --version

echo ""
echo "🎉 Установка завершена успешно!"
echo ""
echo "⚠️  ВАЖНО: Перезайдите в систему или выполните:"
echo "   newgrp docker"
echo ""
echo "📋 Полезные команды:"
echo "   docker ps              # Список контейнеров"
echo "   docker-compose --help  # Справка по Docker Compose"
echo "   docker info            # Информация о Docker" 