import asyncio
import os
import logging
from typing import Dict

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, URLInputFile
from aiogram.client.default import DefaultBotProperties

from app.skyeng_client import SkyengClient
from app.ui.keyboards import kb_search_card
from app.ui.renderers import render_word_card, render_examples

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")  # помести токен в .env
if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN in environment")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# В простом прототипе держим найденную meaning в памяти по пользователю (volatile).
# В проде — хранить ID в БД/кэше.
LAST_MEANING: Dict[int, Dict] = {}

client = SkyengClient()


@dp.message(CommandStart())
async def on_start(m: Message):
    await m.answer(
        "Привет! Я — Wordy Dasha 🤓\n\n"
        "Помогу учить английские слова:\n"
        "• 🔍 Найду перевод и примеры\n"
        "• 🔊 Произнесу слово вслух\n"
        "• 📚 Подберу примеры и картинки\n"
        "• 📝 Дам мини-квиз для тренировки\n\n"
        "Напиши слово (по-английски или по-русски) и посмотрим, что получится!\n\n"
        "Если хочешь заниматься английским индивидуально, напиши настоящей Даше в личку @daria_lanina и подписывайся на её канал @dasha_ate_my_hw"
    )


@dp.message(Command("help"))
async def on_help(m: Message):
    await m.answer(
        "Wordy Dasha — твой помощник в изучении английского! ✨\n\n"
        "Как использовать:\n"
        "• Просто напиши слово: <b>run</b> или <b>бежать</b>\n"
        "• Или используй команду: /search <слово>\n\n"
        "Что ты получишь:\n"
        "• 📝 Перевод и транскрипцию\n"
        "• 🔊 Озвучку произношения\n"
        "• 📚 Примеры использования\n"
        "• 🎯 Мини-квиз для закрепления\n\n"
        "💡 <b>Хочешь больше?</b>\n"
        "Занимайся английским индивидуально с настоящей Дашей:\n"
        "• Личка: @daria_lanina\n"
        "• Канал: @dasha_ate_my_hw"
    )


@dp.message(Command("search"))
async def on_search_cmd(m: Message):
    query = (m.text or "").split(maxsplit=1)
    if len(query) < 2:
        await m.answer("Использование: /search <слово>")
        return
    await handle_query(m, query[1])


@dp.message(F.text)
async def on_text(m: Message):
    # Проверяем, что это не команда
    if m.text.startswith('/'):
        return  # Игнорируем команды
    await handle_query(m, m.text.strip())


@dp.message(Command("stats"))
async def on_stats(m: Message):
    await m.answer(
        "📊 <b>Статистика изучения</b>\n\n"
        "Эта функция пока в разработке! 🚧\n\n"
        "Скоро ты сможешь:\n"
        "• 📈 Отслеживать прогресс\n"
        "• 🎯 Видеть изученные слова\n"
        "• 🏆 Получать достижения\n\n"
        "А пока что продолжай учить новые слова! 💪"
    )


async def handle_query(m: Message, q: str):
    try:
        logger.info(f"Поиск слова: {q}")
        
        # Убираем проблемный answer_chat_action
        
        words = await client.search_words(q)
        logger.info(f"Найдено слов: {len(words)}")
        
        if not words:
            await m.answer(
                f"🤔 Ничего не нашла по запросу «{q}».\n\n"
                "Попробуй:\n"
                "• Проверить написание\n"
                "• Использовать другое слово\n"
                "• Или напиши на другом языке"
            )
            return

        # Берём первый подходящий meaning_id
        meaning_ids = []
        for w in words:
            # слово из /words/search содержит meanings с id
            for mm in (w.get("meanings") or []):
                mid = mm.get("id")
                if isinstance(mid, int):
                    meaning_ids.append(mid)
        meaning_ids = list(dict.fromkeys(meaning_ids))  # unique, preserve order
        
        logger.info(f"Meaning IDs: {meaning_ids}")

        if not meaning_ids:
            await m.answer(
                f"😕 По «{q}» значений не нашлось.\n\n"
                "Возможно, это редкое слово или опечатка."
            )
            return

        details = await client.get_meanings(meaning_ids[:1])  # минимально: берём одно значение
        logger.info(f"Получено деталей: {len(details)}")
        
        if not details:
            await m.answer(
                "😔 Не смогла получить детали значения.\n\n"
                "Попробуй другое слово или обратись позже."
            )
            return

        meaning = details[0]
        LAST_MEANING[m.from_user.id] = meaning  # запомним для кнопки «Произнести»

        text = render_word_card(meaning)
        await m.answer(
            f"🎯 <b>Найдено!</b>\n\n{text}",
            reply_markup=kb_search_card()
        )
        
        logger.info(f"Успешно обработано слово: {q}")

    except Exception as e:
        logger.error(f"Ошибка при обработке слова '{q}': {e}", exc_info=True)
        await m.answer(
            "😅 Упс! Что-то пошло не так.\n\n"
            "Проблема с сетью или сервисом. Попробуй позже!"
        )


@dp.callback_query(F.data == "speak")
async def on_speak(c: CallbackQuery):
    meaning = LAST_MEANING.get(c.from_user.id)
    if not meaning:
        await c.answer("Сначала найди слово! 🔍", show_alert=True)
        return

    # В ответе /meanings часто встречается поле soundUrl
    sound_url = meaning.get("soundUrl") or \
                (meaning.get("pronunciation") or {}).get("soundUrl")
    if not sound_url:
        await c.answer("😔 Озвучка недоступна для этого слова.", show_alert=True)
        return

    try:
        await c.message.answer_audio(
            audio=URLInputFile(sound_url),
            caption=f"🔊 Произношение: {meaning.get('text') or meaning.get('word')}"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке аудио: {e}")
        await c.answer("😅 Не получилось отправить аудио.", show_alert=True)


@dp.callback_query(F.data == "examples")
async def on_examples(c: CallbackQuery):
    meaning = LAST_MEANING.get(c.from_user.id)
    if not meaning:
        await c.answer("Сначала найди слово! 🔍", show_alert=True)
        return
    text = render_examples(meaning)
    await c.message.answer(f"📚 {text}")


async def main():
    logger.info("Запуск Wordy Dasha...")
    # Long polling — проще для ВМ в Yandex Cloud без HTTPS для webhook
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        # аккуратное закрытие httpx клиента
        try:
            import anyio
            anyio.from_thread.run(client.aclose)  # на случай sync выхода
        except Exception:
            pass
