import aiosqlite
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "wordy_dasha.db"):
        self.db_path = db_path
        
    async def init(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level INTEGER DEFAULT 1,
                    words_learned INTEGER DEFAULT 0
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    translation TEXT NOT NULL,
                    transcription TEXT,
                    part_of_speech TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    mastered BOOLEAN DEFAULT FALSE,
                    review_count INTEGER DEFAULT 0,
                    last_reviewed TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, word)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS quiz_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    correct BOOLEAN NOT NULL,
                    answer TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            await db.commit()
            logger.info("База данных инициализирована")
    
    async def get_or_create_user(self, telegram_id: int, username: str = None, 
                                first_name: str = None) -> Dict:
        """Получить или создать пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем существующего пользователя
            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", 
                (telegram_id,)
            )
            user = await cursor.fetchone()
            
            if user:
                return dict(zip([col[0] for col in cursor.description], user))
            
            # Создаем нового пользователя
            await db.execute(
                "INSERT INTO users (telegram_id, username, first_name) VALUES (?, ?, ?)",
                (telegram_id, username, first_name)
            )
            await db.commit()
            
            # Возвращаем созданного пользователя
            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", 
                (telegram_id,)
            )
            user = await cursor.fetchone()
            return dict(zip([col[0] for col in cursor.description], user))
    
    async def add_word_to_user(self, user_id: int, word_data: Dict) -> bool:
        """Добавить слово в словарь пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO user_words 
                    (user_id, word, translation, transcription, 
                     part_of_speech)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    word_data.get('text', ''),
                    word_data.get('translation', {}).get('text', ''),
                    word_data.get('transcription', ''),
                    word_data.get('partOfSpeechCode', '')
                ))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении слова: {e}")
            return False
    
    async def get_user_words(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Получить слова пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM user_words 
                WHERE user_id = ? 
                ORDER BY added_at DESC 
                LIMIT ?
            """, (user_id, limit))
            
            rows = await cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    async def save_quiz_result(self, user_id: int, word: str, correct: bool, 
                              answer: str) -> bool:
        """Сохранить результат квиза"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO quiz_results (user_id, word, correct, answer)
                    VALUES (?, ?, ?, ?)
                """, (user_id, word, correct, answer))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении результата квиза: {e}")
            return False
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """Получить статистику пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            # Общее количество слов
            cursor = await db.execute(
                "SELECT COUNT(*) FROM user_words WHERE user_id = ?", 
                (user_id,)
            )
            total_words = (await cursor.fetchone())[0]
            
            # Изученные слова
            cursor = await db.execute(
                "SELECT COUNT(*) FROM user_words WHERE user_id = ? "
                "AND mastered = TRUE", 
                (user_id,)
            )
            mastered_words = (await cursor.fetchone())[0]
            
            # Результаты квизов
            cursor = await db.execute(
                "SELECT COUNT(*) FROM quiz_results WHERE user_id = ? AND correct = TRUE", 
                (user_id,)
            )
            correct_answers = (await cursor.fetchone())[0]
            
            cursor = await db.execute(
                "SELECT COUNT(*) FROM quiz_results WHERE user_id = ? AND correct = FALSE", 
                (user_id,)
            )
            wrong_answers = (await cursor.fetchone())[0]
            
            total_answers = correct_answers + wrong_answers
            accuracy = (correct_answers / total_answers * 100) if total_answers > 0 else 0
            
            return {
                'total_words': total_words,
                'mastered_words': mastered_words,
                'correct_answers': correct_answers,
                'wrong_answers': wrong_answers,
                'accuracy': round(accuracy, 1)
            }
    
    async def mark_word_as_mastered(self, user_id: int, word: str) -> bool:
        """Отметить слово как изученное"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE user_words 
                    SET mastered = TRUE, last_reviewed = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND word = ?
                """, (user_id, word))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при отметке слова как изученного: {e}")
            return False
    
    async def get_words_for_review(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получить слова для повторения"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM user_words 
                WHERE user_id = ? AND mastered = FALSE
                ORDER BY added_at ASC 
                LIMIT ?
            """, (user_id, limit))
            
            rows = await cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    async def get_quiz_words(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Получить слова для квиза"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM user_words 
                WHERE user_id = ? 
                ORDER BY RANDOM() 
                LIMIT ?
            """, (user_id, limit))
            
            rows = await cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
