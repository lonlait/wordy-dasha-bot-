#!/bin/bash

echo "🚀 Запуск Wordy Dasha бота..."

# Остановка существующего контейнера
echo "🛑 Остановка существующего контейнера..."
docker stop wordy-dasha 2>/dev/null || true
docker rm wordy-dasha 2>/dev/null || true

# Создание директорий для данных
echo "📁 Создание директорий для данных..."
mkdir -p data logs

# Сборка нового образа
echo "🔨 Сборка Docker образа..."
docker build -t wordy-dasha .

# Запуск контейнера с volume для базы данных
echo "🚀 Запуск нового контейнера..."
docker run -d \
    --name wordy-dasha \
    --restart unless-stopped \
    --env-file .env \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/logs:/app/logs \
    wordy-dasha

# Проверка статуса
echo "✅ Проверка статуса..."
sleep 3
docker ps | grep wordy-dasha

echo "🎉 Бот Wordy Dasha успешно запущен!"
echo "📊 Логи: docker logs wordy-dasha"
echo "🗄️ База данных: ./data/"
echo "📝 Логи: ./logs/"
echo "🛑 Остановка: docker stop wordy-dasha"
