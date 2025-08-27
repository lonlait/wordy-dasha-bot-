import logging
import os
from datetime import datetime

# Создаем директорию для логов
os.makedirs("logs", exist_ok=True)

# Настраиваем логирование
def setup_logger():
    """Настройка логирования для бота"""
    logger = logging.getLogger("lingua_bot")
    logger.setLevel(logging.INFO)
    
    # Форматтер для логов
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Хендлер для файла
    file_handler = logging.FileHandler(
        f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log",
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Хендлер для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Добавляем хендлеры
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Создаем логгер
logger = setup_logger()
