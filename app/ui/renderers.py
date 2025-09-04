from html import escape
from typing import Dict, List


def _safe(v, default="—"):
    return v if (v is not None and v != "") else default


def render_word_card(meaning: Dict) -> str:
    """
    meaning — элемент из /meanings
    ожидаемые поля: text/word, transcription, translation.text, partOfSpeechCode, imageUrl
    """
    word = meaning.get("text") or meaning.get("word") or ""
    transcription = meaning.get("transcription")
    pos = meaning.get("partOfSpeechCode")
    translation = (meaning.get("translation") or {}).get("text")
    note = (meaning.get("translation") or {}).get("note")

    title = f"<b>{escape(_safe(word))}</b>"
    if transcription:
        title += f" [{escape(transcription)}]"
    if pos:
        title += f" • {escape(pos)}"
    
    body = f"<b>Перевод:</b> {escape(_safe(translation))}"
    
    # Добавляем примечание, если есть
    if note:
        body += f" <i>({escape(note)})</i>"

    # дополнительные переводы, если есть
    alts: List[str] = []
    for tr in (meaning.get("meaningsWithSimilarTranslation") or []):
        t = (tr.get("translation") or {}).get("text")
        if t and t != translation and t not in alts:
            alts.append(t)
    if alts:
        body += f"\n<b>Ещё:</b> {escape('; '.join(alts[:4]))}"

    return f"{title}\n{body}"


def render_examples(meaning: Dict) -> str:
    examples = meaning.get("examples") or []
    if not examples:
        return "😔 Примеры не найдены для этого слова."
    
    # Логируем структуру примера для отладки
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Структура примера: {examples[0] if examples else 'Нет примеров'}")
    
    lines = []
    for i, ex in enumerate(examples[:5]):
        en = ex.get("text") or ""
        
        # Пробуем разные варианты получения перевода ПРИМЕРА (не слова)
        ru = ""
        
        # Сначала пробуем получить перевод примера из разных полей
        if ex.get("translation"):
            if isinstance(ex["translation"], dict):
                ru = ex["translation"].get("text") or ""
            else:
                ru = str(ex["translation"])
        
        # Если перевода нет, попробуем другие поля для перевода примера
        if not ru:
            ru = ex.get("translationText") or ex.get("translation_text") or ""
        
        # Если все еще нет перевода примера, попробуем другие возможные поля
        if not ru:
            ru = ex.get("translation_text") or ex.get("translationText") or ""
        
        # Логируем, что мы нашли для отладки
        logger.info(f"Пример: '{en}' -> Перевод: '{ru}'")
        
        # Показываем только английский текст (переводы примеров недоступны в API)
        lines.append(f"<b>{i+1}.</b> {escape(en)}")
    
    return "📚 <b>Примеры употребления:</b>\n\n" + "\n\n".join(lines)


def render_quiz_question(word: str, options: List[str], correct: int) -> str:
    """Рендерит вопрос для квиза"""
    question = f"🎯 Как переводится слово «{word}»?\n\n"
    
    for i, option in enumerate(options):
        question += f"{i+1}. {escape(option)}\n"
    
    return question

def render_quiz_result(word: str, options: List[str], correct: int, user_answer: int) -> str:
    """Рендерит результат квиза"""
    result = f"🎯 Как переводится слово «{word}»?\n\n"
    
    for i, option in enumerate(options):
        if i == correct:
            marker = "✅"
        elif i == user_answer and i != correct:
            marker = "❌"
        else:
            marker = "⚪"
        result += f"{marker} {escape(option)}\n"
    
    if user_answer == correct:
        result += "\n🎉 Правильно!"
    else:
        result += f"\n😔 Неправильно! Правильный ответ: {escape(options[correct])}"
    
    return result
