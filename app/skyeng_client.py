import httpx
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

BASE = "https://dictionary.skyeng.ru/api/public/v1"


class SkyengClient:
    def __init__(self, timeout: float = 10.0):
        self._client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    async def search_words(self, query: str) -> List[Dict]:
        """
        Возвращает список словарных статей. Каждая содержит meaningId-ы.
        GET /words/search?q=...
        """
        try:
            url = f"{BASE}/words/search"
            params = {"search": query, "q": query}
            logger.info(f"Запрос к Skyeng API: {url} с параметрами {params}")
            
            r = await self._client.get(url, params=params)
            r.raise_for_status()
            
            result = r.json() or []
            logger.info(f"Получен ответ от Skyeng API: {len(result)} слов")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при поиске слов '{query}': {e}")
            raise

    async def get_meanings(self, meaning_ids: List[int]) -> List[Dict]:
        """
        Возвращает подробные значения по meaning_id (переводы, транскрипция, звук, примеры).
        GET /meanings?ids=1,2,3
        """
        if not meaning_ids:
            return []
            
        try:
            url = f"{BASE}/meanings"
            params = {"ids": ",".join(map(str, meaning_ids))}
            logger.info(f"Запрос деталей: {url} с параметрами {params}")
            
            r = await self._client.get(url, params=params)
            r.raise_for_status()
            
            result = r.json() or []
            logger.info(f"Получены детали для {len(result)} значений")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении деталей для {meaning_ids}: {e}")
            raise

    async def aclose(self):
        await self._client.aclose()
