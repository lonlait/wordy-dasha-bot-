FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копирование кода
COPY app ./app
COPY .env ./.env

# Создание директории для логов и базы данных
RUN mkdir -p logs data

# Установка прав на базу данных
RUN chmod 755 data

# Метаданные
LABEL maintainer="Dasha"
LABEL description="Wordy Dasha - English Learning Bot"
LABEL version="1.0"

# Запуск
CMD ["python", "-m", "app.main"]
