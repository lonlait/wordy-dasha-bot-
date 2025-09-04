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
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Получить пользователя по telegram_id"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute(
                    "SELECT * FROM users WHERE telegram_id = ?",
                    (telegram_id,)
                )
                user = await cursor.fetchone()
                
                return dict(user) if user else None
                
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None

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
                        meaning.get('word', meaning.get('text', '')),
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
    
    async def get_user_words(self, telegram_id: int, limit: int = 10) -> List[Dict]:
        """Получить слова пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT w.id, w.word, w.translation, uw.mastered
                    FROM user_words uw
                    JOIN words w ON uw.word_id = w.id
                    JOIN users u ON uw.user_id = u.id
                    WHERE u.telegram_id = ?
                    ORDER BY uw.added_at DESC
                    LIMIT ?
                """, (telegram_id, limit))
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Ошибка получения слов пользователя: {e}")
            return []
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """Получить статистику пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Получаем статистику
                cursor = await db.execute("""
                    SELECT 
                        COALESCE(COUNT(uw.id), 0) as total_words,
                        COALESCE(SUM(CASE WHEN uw.mastered THEN 1 ELSE 0 END), 0) as mastered_words,
                        COALESCE(us.correct_answers, 0) as correct_answers,
                        COALESCE(us.wrong_answers, 0) as wrong_answers
                    FROM users u
                    LEFT JOIN user_words uw ON u.id = uw.user_id
                    LEFT JOIN user_stats us ON u.id = us.user_id
                    WHERE u.id = ?
                    GROUP BY u.id
                """, (user_id,))
                
                row = await cursor.fetchone()
                
                if row:
                    total_words = row['total_words']
                    mastered_words = row['mastered_words']
                    correct_answers = row['correct_answers']
                    wrong_answers = row['wrong_answers']
                    
                    accuracy = (correct_answers / (correct_answers + wrong_answers) * 100) if (correct_answers + wrong_answers) > 0 else 0
                    
                    return {
                        'total_words': total_words,
                        'mastered_words': mastered_words,
                        'correct_answers': correct_answers,
                        'wrong_answers': wrong_answers,
                        'accuracy': round(accuracy, 1)
                    }
                else:
                    return {
                        'total_words': 0,
                        'mastered_words': 0,
                        'correct_answers': 0,
                        'wrong_answers': 0,
                        'accuracy': 0.0
                    }
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                'total_words': 0,
                'mastered_words': 0,
                'correct_answers': 0,
                'wrong_answers': 0,
                'accuracy': 0.0
            }
    
    async def update_user_stats(self, user_id: int, correct_answers: int = 0, wrong_answers: int = 0):
        """Обновить статистику пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Проверяем, есть ли запись статистики
                cursor = await db.execute(
                    "SELECT id FROM user_stats WHERE user_id = ?",
                    (user_id,)
                )
                stats_record = await cursor.fetchone()
                
                if stats_record:
                    # Обновляем существующую запись
                    if correct_answers > 0:
                        await db.execute(
                            "UPDATE user_stats SET correct_answers = correct_answers + ? WHERE user_id = ?",
                            (correct_answers, user_id)
                        )
                    if wrong_answers > 0:
                        await db.execute(
                            "UPDATE user_stats SET wrong_answers = wrong_answers + ? WHERE user_id = ?",
                            (wrong_answers, user_id)
                        )
                else:
                    # Создаем новую запись
                    await db.execute(
                        "INSERT INTO user_stats (user_id, correct_answers, wrong_answers) VALUES (?, ?, ?)",
                        (user_id, correct_answers, wrong_answers)
                    )
                
                await db.commit()
                logger.info(f"Статистика пользователя {user_id} обновлена: +{correct_answers} правильных, +{wrong_answers} неправильных")
                
        except Exception as e:
            logger.error(f"Ошибка обновления статистики: {e}")
            raise
