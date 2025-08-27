FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY .env ./.env

# Создаем директорию для логов
RUN mkdir -p logs

# Метаданные образа
LABEL maintainer="Wordy Dasha Bot Team"
LABEL description="Telegram bot for learning English words"
LABEL version="1.0.0"

CMD ["python", "-m", "app.main"]
