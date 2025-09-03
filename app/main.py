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
            m.from_user.first_name,
            m.from_user.last_name
        )
        logger.info(f"Пользователь {m.from_user.id} запустил бота")
        await m.answer(WELCOME_MESSAGE)
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")
        await m.answer("😔 Не удалось инициализировать бота. Попробуй позже!")

# Обработчик команды /help
@dp.message(Command("help"))
async def on_help(m: Message):
    await m.answer(HELP_MESSAGE)

# Обработчик команды /search
@dp.message(Command("search"))
async def on_search(m: Message):
    search_help = """🔍 <b>Как искать слова:</b>

<b>Команда:</b> /search слово
<b>Пример:</b> /search hello

<b>Или просто напиши слово:</b>
• hello
• привет
• run
• бежать

<b>Что ты получишь:</b>
�� Перевод и транскрипцию
🔊 Озвучку произношения
📚 Примеры использования
🎯 Мини-квиз для закрепления

<b>Дополнительные команды:</b>
/start - запустить бота
/help - помощь
/stats - твоя статистика
/dictionary - твой словарь
/quiz - начать квиз"""
    
    await m.answer(search_help)

# Обработчик команды /stats
@dp.message(Command("stats"))
async def on_stats(m: Message):
    try:
        user = await db.get_user_by_telegram_id(m.from_user.id)
        if not user:
            await m.answer("😔 Сначала запусти бота командой /start")
            return
        
        stats = await db.get_user_stats(user['id'])
        stats_text = f"""�� <b>Твоя статистика:</b>

📚 Слов в словаре: {stats['total_words']}
✅ Изучено: {stats['learned_words']}
�� Правильных ответов: {stats['correct_answers']}
❌ Ошибок: {stats['wrong_answers']}
�� Точность: {stats['accuracy']:.1f}%"""
        
        await m.answer(stats_text)
    except Exception as e:
        logger.error(f"Ошибка в /stats: {e}")
        await m.answer("😅 Не удалось загрузить статистику. Попробуй позже!")

# Обработчик команды /dictionary
@dp.message(Command("dictionary"))
async def on_dictionary(m: Message):
    try:
        user = await db.get_user_by_telegram_id(m.from_user.id)
        if not user:
            await m.answer("😔 Сначала запусти бота командой /start")
            return
        
        words = await db.get_user_words(m.from_user.id, limit=10)
        if not words:
            await m.answer("�� Твой словарь пуст. Начни изучать слова!")
            return
        
        words_text = "�� <b>Твой словарь:</b>\n\n"
        for i, word in enumerate(words, 1):
            words_text += f"{i}. <b>{word['word']}</b> — {word['translation']}\n"
        
        await m.answer(words_text)
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
        logger.info(f"meaning_ids: {meaning_ids}")
        
        meanings = await skyeng.get_meanings(meaning_ids)
        logger.info(f"Получены meanings: {meanings}")
        
        if not meanings:
            logger.warning("meanings пустой!")
            await m.answer("😔 Не удалось получить перевод. Попробуй позже!")
            return
        
        meaning = meanings[0]
        logger.info(f"Выбранное meaning: {meaning}")
        
        # Сохраняем слово в словарь пользователя
        try:
            logger.info("Начинаем сохранение в базу данных...")
            user = await db.get_or_create_user(m.from_user.id)
            logger.info(f"Пользователь получен: {user}")
            await db.add_word_to_user(user['id'], meaning)
            logger.info("Слово сохранено в базу данных")
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                # Пользователь уже существует, получаем его данные
                user = await db.get_user_by_telegram_id(m.from_user.id)
                if user:
                    await db.add_word_to_user(user['id'], meaning)
                    logger.info("Слово сохранено в базу данных (пользователь уже существовал)")
                else:
                    logger.error(f"Не удалось получить пользователя: {e}")
                    await m.answer("😔 Не удалось сохранить слово. Попробуй позже!")
                    return
            else:
                logger.error(f"Ошибка при работе с пользователем: {e}")
                await m.answer("😔 Не удалось сохранить слово. Попробуй позже!")
                return
        
        # Отправляем карточку слова
        try:
            logger.info(f"Данные meaning: {meaning}")
            card_text = render_word_card(meaning)
            logger.info(f"Создана карточка: {card_text[:100]}...")
            await m.answer(card_text, reply_markup=kb_search_card())
            logger.info("Карточка отправлена успешно")
        except Exception as e:
            logger.error(f"Ошибка в render_word_card: {e}")
            logger.error(f"Тип данных meaning: {type(meaning)}")
            await m.answer("😔 Ошибка при создании карточки слова")
        
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
            await c.answer("�� Примеры не найдены!")
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
        try:
            user = await db.get_or_create_user(c.from_user.id)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                # Пользователь уже существует, получаем его данные
                user = await db.get_user_by_telegram_id(c.from_user.id)
                if not user:
                    await c.answer("😔 Не удалось получить пользователя!")
                    return
            else:
                logger.error(f"Ошибка при работе с пользователем: {e}")
                await c.answer("😔 Ошибка при работе с пользователем!")
                return
        
        words = await db.get_user_words(c.from_user.id, limit=5)
        
        if len(words) < 2:
            await c.answer("�� Добавь больше слов в словарь для квиза!")
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
        logger.error(f"Ошибка при создании квиза: {e}")
        await c.answer("😅 Ошибка при создании квиза!")

# Обработчик ответов на квиз
@dp.callback_query(lambda c: c.data.startswith("quiz_"))
async def on_quiz_answer(c: CallbackQuery):
    try:
        # Получаем данные из callback_data
        data = c.data.split("_")
        if len(data) != 3:
            await c.answer("😅 Ошибка в данных квиза!")
            return
        
        word = data[1]
        answer_index = int(data[2])
        
        # Получаем правильный ответ из сообщения
        message_text = c.message.text
        lines = message_text.split('\n')
        correct_index = -1
        for i, line in enumerate(lines):
            if line.startswith("✅"):
                correct_index = i - 2  # -2 потому что первые две строки - заголовок
                break
        
        if correct_index == -1:
            await c.answer("😅 Не удалось определить правильный ответ!")
            return
        
        # Проверяем ответ
        if answer_index == correct_index:
            await c.answer("🎉 Правильно!")
            # Здесь можно добавить логику для увеличения счетчика правильных ответов
        else:
            await c.answer("❌ Неправильно!")
            # Здесь можно добавить логику для увеличения счетчика неправильных ответов
        
    except Exception as e:
        logger.error(f"Ошибка при обработке ответа на квиз: {e}")
        await c.answer("�� Ошибка при обработке ответа!")

async def main():
    """Основная функция запуска бота"""
    try:
        logger.info("База данных инициализирована")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        logger.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())