import aiosqlite
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "data/bot_database.db"):
        self.db_path = db_path
    
    async def init(self):
        """Инициализация базы данных"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Создаем таблицу пользователей
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        username TEXT,
                        first_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Создаем таблицу слов
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS words (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        word TEXT NOT NULL,
                        translation TEXT NOT NULL,
                        transcription TEXT,
                        examples TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Создаем таблицу словаря пользователя
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS user_words (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        word_id INTEGER NOT NULL,
                        mastered BOOLEAN DEFAULT FALSE,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (word_id) REFERENCES words (id)
                    )
                """)
                
                # Создаем таблицу статистики
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS user_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE NOT NULL,
                        correct_answers INTEGER DEFAULT 0,
                        wrong_answers INTEGER DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                
                await db.commit()
                logger.info("База данных инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise
    
    async def get_or_create_user(self, telegram_id: int, username: str = None, first_name: str = None) -> Dict:
        """Получить или создать пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Ищем существующего пользователя
                cursor = await db.execute(
                    "SELECT * FROM users WHERE telegram_id = ?",
                    (telegram_id,)
                )
                user = await cursor.fetchone()
                
                if user:
                    return dict(user)
                
                # Создаем нового пользователя
                cursor = await db.execute(
                    "INSERT INTO users (telegram_id, username, first_name) VALUES (?, ?, ?)",
                    (telegram_id, username, first_name)
                )
                await db.commit()
                
                # Получаем созданного пользователя
                cursor = await db.execute(
                    "SELECT * FROM users WHERE telegram_id = ?",
                    (telegram_id,)
                )
                user = await cursor.fetchone()
                
                # Создаем запись статистики
                await db.execute(
                    "INSERT INTO user_stats (user_id) VALUES (?)",
                    (user['id'],)
                )
                await db.commit()
                
                return dict(user)
                
        except Exception as e:
            logger.error(f"Ошибка получения/создания пользователя: {e}")
            raise
    
    async def add_word_to_user(self, user_id: int, meaning: Dict):
        """Добавить слово в словарь пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Добавляем слово в общую таблицу
                cursor = await db.execute(
                    "INSERT INTO words (word, translation, transcription, examples) VALUES (?, ?, ?, ?)",
                    (
                        meaning.get('text', ''),
                        meaning.get('translation', {}).get('text', ''),
                        meaning.get('transcription', ''),
                        str(meaning.get('examples', []))
                    )
                )
                word_id = cursor.lastrowid
                
                # Добавляем в словарь пользователя
                await db.execute(
                    "INSERT INTO user_words (user_id, word_id) VALUES (?, ?)",
                    (user_id, word_id)
                )
                
                await db.commit()
                logger.info(f"Слово добавлено в словарь пользователя {user_id}")
                
        except Exception as e:
            logger.error(f"Ошибка добавления слова: {e}")
            raise
    
    async def get_user_words(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получить слова пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT w.word, w.translation, uw.mastered
                    FROM user_words uw
                    JOIN words w ON uw.word_id = w.id
                    WHERE uw.user_id = ?
                    ORDER BY uw.added_at DESC
                    LIMIT ?
                """, (user_id, limit))
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Ошибка получения слов пользователя: {e}")
            return []
    
    async def get_user_stats(self, telegram_id: int) -> Dict:
        """Получить статистику пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Получаем пользователя
                cursor = await db.execute(
                    "SELECT id FROM users WHERE telegram_id = ?",
                    (telegram_id,)
                )
                user = await cursor.fetchone()
                
                if not user:
                    return {
                        'total_words': 0,
                        'mastered_words': 0,
                        'correct_answers': 0,
                        'wrong_answers': 0,
                        'accuracy': 0
                    }
                
                # Получаем статистику
                cursor = await db.execute("""
                    SELECT 
                        COUNT(uw.id) as total_words,
                        SUM(CASE WHEN uw.mastered THEN 1 ELSE 0 END) as mastered_words,
                        us.correct_answers,
                        us.wrong_answers
                    FROM user_words uw
                    LEFT JOIN user_stats us ON uw.user_id = us.user_id
                    WHERE uw.user_id = ?
                """, (user['id'],))
                
                stats = await cursor.fetchone()
                
                total_words = stats['total_words'] or 0
                mastered_words = stats['mastered_words'] or 0
                correct_answers = stats['correct_answers'] or 0
                wrong_answers = stats['wrong_answers'] or 0
                
                accuracy = 0
                if correct_answers + wrong_answers > 0:
                    accuracy = round((correct_answers / (correct_answers + wrong_answers)) * 100)
                
                return {
                    'total_words': total_words,
                    'mastered_words': mastered_words,
                    'correct_answers': correct_answers,
                    'wrong_answers': wrong_answers,
                    'accuracy': accuracy
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                'total_words': 0,
                'mastered_words': 0,
                'correct_answers': 0,
                'wrong_answers': 0,
                'accuracy': 0
            }
