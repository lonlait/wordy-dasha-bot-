#!/usr/bin/env python3
"""
Скрипт запуска Lingua Bot с загрузкой переменных окружения
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Проверяем наличие токена
if not os.getenv("BOT_TOKEN"):
    print("Ошибка: BOT_TOKEN не найден в переменных окружения")
    print("Создайте файл .env на основе env.example и добавьте ваш токен")
    exit(1)

# Запускаем основной модуль
if __name__ == "__main__":
    from app.main import main
    import asyncio
    
    print("Запуск Lingua Bot...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"Ошибка запуска: {e}")
