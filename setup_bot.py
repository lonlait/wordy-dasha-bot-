#!/usr/bin/env python3
"""
Скрипт для настройки бота Wordy Dasha
Устанавливает команды, описание и about текст
"""

import asyncio
import os
from dotenv import load_dotenv
from bot_settings import (
    BOT_COMMANDS, 
    BOT_DESCRIPTION, 
    BOT_ABOUT
)

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден в .env файле")
    exit(1)

async def setup_bot():
    """Настраиваем бота"""
    from aiogram import Bot
    
    bot = Bot(BOT_TOKEN)
    
    try:
        print("🤖 Настройка бота Wordy Dasha...")
        
        # Устанавливаем команды
        print("📝 Устанавливаем команды...")
        await bot.set_my_commands(BOT_COMMANDS)
        print("✅ Команды установлены")
        
        # Устанавливаем описание
        print("📖 Устанавливаем описание...")
        await bot.set_my_description(BOT_DESCRIPTION)
        print("✅ Описание установлено")
        
        # Устанавливаем about текст
        print("ℹ️ Устанавливаем about текст...")
        await bot.set_my_short_description(BOT_ABOUT)
        print("✅ About текст установлен")
        
        # Получаем информацию о боте
        me = await bot.get_me()
        print(f"\n🎉 Бот @{me.username} успешно настроен!")
        print(f"Имя: {me.first_name}")
        print(f"ID: {me.id}")
        
    except Exception as e:
        print(f"❌ Ошибка настройки: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    print("🚀 Запуск настройки бота...")
    asyncio.run(setup_bot())
    print("✅ Настройка завершена!")
