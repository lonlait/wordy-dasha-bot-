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
    # В новом API Skyeng примеры не приходят в meaning
    # Нужно получать их отдельно через API meanings
    return "😔 Примеры не найдены для этого слова.\n\nВ новом API Skyeng примеры нужно получать отдельно."


def render_quiz_question(word: str, options: List[str], correct: int) -> str:
    """Рендерит вопрос для квиза"""
    question = f"🎯 Как переводится слово «{word}»?\n\n"
    
    for i, option in enumerate(options):
        marker = "✅" if i == correct else "❌"
        question += f"{marker} {escape(option)}\n"
    
    return question
