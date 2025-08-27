#!/usr/bin/env python3
"""
Скрипт для тестирования Skyeng API локально
"""

import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from skyeng_client import SkyengClient


async def test_skyeng_api():
    """Тестируем Skyeng API"""
    client = SkyengClient()
    
    try:
        # Тестируем поиск слова
        print("🔍 Тестируем поиск слова 'hello'...")
        words = await client.search_words("hello")
        print(f"Найдено слов: {len(words)}")
        
        if words:
            # Получаем meaning_id из первого слова
            meaning_ids = []
            for w in words:
                for mm in (w.get("meanings") or []):
                    mid = mm.get("id")
                    if isinstance(mid, int):
                        meaning_ids.append(mid)
            
            if meaning_ids:
                print(f"Meaning IDs: {meaning_ids[:3]}")
                
                # Получаем детали
                print("📝 Получаем детали значения...")
                details = await client.get_meanings(meaning_ids[:1])
                
                if details:
                    meaning = details[0]
                    print(f"Слово: {meaning.get('text')}")
                    print(f"Транскрипция: {meaning.get('transcription')}")
                    print(f"Перевод: {meaning.get('translation', {}).get('text')}")
                    print(f"Часть речи: {meaning.get('partOfSpeechCode')}")
                    print(f"Звук: {meaning.get('soundUrl')}")
                    
                    # Примеры
                    examples = meaning.get("examples", [])
                    if examples:
                        print(f"Примеры: {len(examples)}")
                        for i, ex in enumerate(examples[:2]):
                            print(f"  {i+1}. {ex.get('text')}")
                            print(f"     — {ex.get('translation', {}).get('text')}")
                else:
                    print("❌ Не удалось получить детали")
            else:
                print("❌ Не найдено meaning IDs")
        else:
            print("❌ Слова не найдены")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await client.aclose()


if __name__ == "__main__":
    print("🧪 Тестирование Skyeng API...")
    asyncio.run(test_skyeng_api())
    print("✅ Тест завершен")
