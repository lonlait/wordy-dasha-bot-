#!/bin/bash
# Скрипт для развертывания Wordy Dasha на Yandex Cloud

set -e

echo "🚀 Развертывание Wordy Dasha на Yandex Cloud..."

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "📦 Установка Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "⚠️  Перезапустите сессию или выполните: newgrp docker"
fi

# Собираем Docker образ
echo "🔨 Сборка Docker образа..."
docker build -t wordy-dasha .

# Останавливаем предыдущий контейнер если есть
echo "🛑 Остановка предыдущего контейнера..."
docker stop wordy-dasha 2>/dev/null || true
docker rm wordy-dasha 2>/dev/null || true

# Запускаем новый контейнер
echo "▶️  Запуск бота..."
docker run -d \
    --name wordy-dasha \
    --restart unless-stopped \
    --env-file .env \
    wordy-dasha

# Проверяем статус
echo "📊 Статус контейнера:"
docker ps | grep wordy-dasha

echo "✅ Wordy Dasha успешно развернут!"
echo "📝 Логи: docker logs -f wordy-dasha"
echo "🛑 Остановка: docker stop wordy-dasha"
