import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties

# Исправляем импорты - добавляем точку для относительных импортов
from .skyeng_client import SkyengClient
from .ui.keyboards import kb_search_card, kb_quiz
from .ui.renderers import render_word_card, render_examples, render_quiz_question
from .database import Database
from .bot_settings import WELCOME_MESSAGE, HELP_MESSAGE

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

# Инициализация
bot = Bot(token=BOT_TOKEN, 
          default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
skyeng = SkyengClient()
db = Database()

# Обработчик команды /start
@dp.message(Command("start"))
async def on_start(m: Message):
    try:
        # Создаем или получаем пользователя
        user = await db.get_or_create_user(
            m.from_user.id,
            m.from_user.username,
            m.from_user.first_name
        )
        logger.info(f"Пользователь {user['telegram_id']} запустил бота")
        
        await m.answer(WELCOME_MESSAGE)
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")
        await m.answer("😅 Упс! Что-то пошло не так. Попробуй позже!")

# Обработчик команды /help
@dp.message(Command("help"))
async def on_help(m: Message):
    await m.answer(HELP_MESSAGE)

# Обработчик команды /stats
@dp.message(Command("stats"))
async def on_stats(m: Message):
    try:
        stats = await db.get_user_stats(m.from_user.id)
        stats_text = f"""
🎯 <b>Твоя статистика:</b>

📚 <b>Слов в словаре:</b> {stats['total_words']}
✅ <b>Изучено:</b> {stats['mastered_words']}
🎯 <b>Правильных ответов:</b> {stats['correct_answers']}
❌ <b>Ошибок:</b> {stats['wrong_answers']}
📊 <b>Точность:</b> {stats['accuracy']}%
        """.strip()
        
        await m.answer(stats_text)
    except Exception as e:
        logger.error(f"Ошибка в /stats: {e}")
        await m.answer("😅 Не удалось получить статистику. Попробуй позже!")

# Обработчик команды /dictionary
@dp.message(Command("dictionary"))
async def on_dictionary(m: Message):
    try:
        words = await db.get_user_words(m.from_user.id, limit=10)
        
        if not words:
            await m.answer("📚 Твой словарь пока пуст. Начни искать слова!")
            return
        
        text = "📚 <b>Твои последние слова:</b>\n\n"
        for i, word_data in enumerate(words, 1):
            mastered = "✅" if word_data['mastered'] else "📖"
            text += f"{i}. {mastered} <b>{word_data['word']}</b> — {word_data['translation']}\n"
        
        await m.answer(text)
    except Exception as e:
        logger.error(f"Ошибка в /dictionary: {e}")
        await m.answer("😅 Не удалось загрузить словарь. Попробуй позже!")

# Обработчик текстовых сообщений
@dp.message()
async def on_text(m: Message):
    if m.text.startswith('/'):
        return
        
    try:
        logger.info(f"Поиск слова: {m.text}")
        
        # Поиск слов
        words = await skyeng.search_words(m.text)
        if not words:
            await m.answer("😔 Слово не найдено. Попробуй другое!")
            return
        
        # Получаем детали первого слова
        meaning_ids = ([words[0].get("meaningIds", [])[0]]
                       if words[0].get("meaningIds") else [])
        meanings = await skyeng.get_meanings(meaning_ids)
        
        if not meanings:
            await m.answer("😔 Не удалось получить перевод. Попробуй позже!")
            return
        
        meaning = meanings[0]
        
        # Сохраняем слово в словарь пользователя
        user = await db.get_or_create_user(m.from_user.id)
        await db.add_word_to_user(user['id'], meaning)
        
        # Отправляем карточку слова
        card_text = render_word_card(meaning)
        await m.answer(card_text, reply_markup=kb_search_card())
        
    except Exception as e:
        logger.error(f"Ошибка при поиске слова '{m.text}': {e}")
        await m.answer("😅 Упс! Что-то пошло не так. Проблема с сетью или сервисом. "
                       "Попробуй позже!")

# Обработчик кнопки "Произнести"
@dp.callback_query(lambda c: c.data == "speak")
async def on_speak(c: CallbackQuery):
    await c.answer("🔊 Функция озвучки в разработке!")

# Обработчик кнопки "Примеры"
@dp.callback_query(lambda c: c.data == "examples")
async def on_examples(c: CallbackQuery):
    try:
        # Получаем текст сообщения для поиска примеров
        message_text = c.message.text
        word = message_text.split('\n')[0].replace('<b>', '').replace('</b>', '').split('[')[0].strip()
        
        # Ищем слово заново для получения примеров
        words = await skyeng.search_words(word)
        if not words:
            await c.answer("😔 Примеры не найдены!")
            return
        
        meaning_ids = [words[0].get("meaningIds", [])[0]] if words[0].get("meaningIds") else []
        meanings = await skyeng.get_meanings(meaning_ids)
        
        if not meanings:
            await c.answer("😔 Не удалось загрузить примеры!")
            return
        
        examples_text = render_examples(meanings[0])
        await c.message.answer(examples_text)
        await c.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении примеров: {e}")
        await c.answer("😅 Ошибка при загрузке примеров!")

# Обработчик кнопки "Квиз"
@dp.callback_query(lambda c: c.data == "quiz")
async def on_quiz(c: CallbackQuery):
    try:
        # Получаем слова пользователя для квиза
        user = await db.get_or_create_user(c.from_user.id)
        words = await db.get_user_words(user['id'], limit=5)
        
        if len(words) < 2:
            await c.answer("🎯 Добавь больше слов в словарь для квиза!")
            return
        
        # Выбираем случайное слово
        import random
        quiz_word = random.choice(words)
        
        # Создаем варианты ответов
        all_words = [w['translation'] for w in words if w['translation'] != quiz_word['translation']]
        options = [quiz_word['translation']] + random.sample(all_words, min(3, len(all_words)))
        random.shuffle(options)
        correct_index = options.index(quiz_word['translation'])
        
        question_text = render_quiz_question(quiz_word['word'], options, correct_index)
        await c.message.answer(question_text, reply_markup=kb_quiz())
        await c.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в квизе: {e}")
        await c.answer("😅 Ошибка при создании квиза!")

# Обработчики квиза
@dp.callback_query(lambda c: c.data.startswith("quiz_"))
async def on_quiz_answer(c: CallbackQuery):
    try:
        if c.data == "quiz_correct":
            await c.answer("✅ Правильно! Молодец!")
        elif c.data == "quiz_incorrect":
            await c.answer("❌ Неправильно! Попробуй еще раз!")
        elif c.data == "quiz_next":
            await c.answer("🔄 Новый вопрос!")
            # Здесь можно запустить новый квиз
        
        await c.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработке ответа квиза: {e}")
        await c.answer("😅 Ошибка!")

# Обработчик завершения работы
async def on_shutdown():
    await skyeng.aclose()
    logger.info("Бот остановлен")

# Главная функция
async def main():
    # Инициализируем базу данных
    await db.init()
    logger.info("База данных инициализирована")
    
    # Запускаем бота
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())