from aiogram.utils.keyboard import InlineKeyboardBuilder


def kb_search_card():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔊 Произнести", callback_data="speak")
    kb.button(text="📚 Примеры", callback_data="examples")
    kb.button(text="🎯 Квиз", callback_data="quiz")
    kb.adjust(2, 1)
    return kb.as_markup()


def kb_quiz():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Правильно", callback_data="quiz_correct")
    kb.button(text="❌ Неправильно", callback_data="quiz_incorrect")
    kb.button(text="🔄 Другое слово", callback_data="quiz_next")
    kb.adjust(2, 1)
    return kb.as_markup()
