#!/usr/bin/env python3
"""
Скрипт для проверки здоровья Lingua Bot
"""

import requests
import json
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def check_bot_health():
    """Проверяем здоровье бота"""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("❌ BOT_TOKEN не найден в .env файле")
        return False
    
    try:
        # Проверяем API Telegram
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                print(f"✅ Бот активен: @{bot_info.get('username')}")
                print(f"   Имя: {bot_info.get('first_name')}")
                print(f"   ID: {bot_info.get('id')}")
                return True
            else:
                print(f"❌ Ошибка API: {data.get('description')}")
                return False
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def check_skyeng_api():
    """Проверяем доступность Skyeng API"""
    try:
        url = "https://dictionary.skyeng.ru/api/public/v1/words/search"
        response = requests.get(url, params={"search": "test"}, timeout=10)
        
        if response.status_code == 200:
            print("✅ Skyeng API доступен")
            return True
        else:
            print(f"❌ Skyeng API недоступен: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения к Skyeng API: {e}")
        return False

if __name__ == "__main__":
    print("🏥 Проверка здоровья Lingua Bot...")
    print("-" * 40)
    
    bot_ok = check_bot_health()
    print()
    
    skyeng_ok = check_skyeng_api()
    print()
    
    if bot_ok and skyeng_ok:
        print("🎉 Все системы работают нормально!")
        exit(0)
    else:
        print("⚠️  Обнаружены проблемы!")
        exit(1)
