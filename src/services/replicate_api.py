"""
Сервис для взаимодействия с Replicate API (или Mock Replicate).
"""
import logging
from typing import Optional
import httpx

from src.config import config
from src.utils.http import make_request

logger = logging.getLogger(__name__)


async def create_prediction(
    image_url: str,
    webhook_url: str,
    model: Optional[str] = None,
    webhook_events_filter: Optional[list] = None
) -> dict:
    """
    Создать prediction в Replicate (или Mock Replicate).
    
    Args:
        image_url: URL изображения для обработки
        webhook_url: URL для вебхука с результатом
        model: Модель Replicate (опционально, для реального Replicate)
        webhook_events_filter: Список событий для вебхука (по умолчанию ["completed"])
        
    Returns:
        Ответ от API с prediction_id и статусом
    """
    if webhook_events_filter is None:
        webhook_events_filter = ["completed"]
    
    # Определяем URL API (Mock Replicate или реальный Replicate)
    if config.MOCK_REPLICATE_URL:
        api_url = f"{config.MOCK_REPLICATE_URL}/v1/predictions"
        logger.info(f"Используется Mock Replicate: {api_url}")
        payload = {
            "input": {
                "image": image_url
            },
            "webhook": webhook_url,
            "webhook_events_filter": webhook_events_filter
        }
        headers = {}
    else:
        # Реальный Replicate API
        logger.warning(
            "MOCK_REPLICATE_URL не установлен. Попытка использовать реальный Replicate API. "
            "Для локальной разработки рекомендуется установить MOCK_REPLICATE_URL=http://mock-replicate:8001"
        )
        api_url = "https://api.replicate.com/v1/predictions"
        if not model:
            raise ValueError(
                "Для реального Replicate API требуется указать модель. "
                "Или установите MOCK_REPLICATE_URL=http://mock-replicate:8001 в .env для локальной разработки"
            )
        if not config.REPLICATE_API_TOKEN:
            raise ValueError(
                "Для реального Replicate API требуется REPLICATE_API_TOKEN. "
                "Или установите MOCK_REPLICATE_URL=http://mock-replicate:8001 в .env для локальной разработки"
            )
        
        payload = {
            "version": model,  # В реальном API это version, а не model
            "input": {
                "image": image_url
            },
            "webhook": webhook_url,
            "webhook_events_filter": webhook_events_filter
        }
        headers = {
            "Authorization": f"Token {config.REPLICATE_API_TOKEN}",
            "Content-Type": "application/json"
        }
    
    try:
        logger.debug(f"Отправка запроса к {api_url}")
        response = await make_request(
            "POST",
            api_url,
            json=payload,
            headers=headers,
            timeout=15.0
        )
        data = response.json()
        logger.info(f"Prediction создан: {data.get('id')}, статус: {data.get('status')}")
        return data
    except Exception as e:
        error_msg = str(e)
        if "name resolution" in error_msg.lower() or "temporary failure" in error_msg.lower():
            logger.error(
                f"Ошибка DNS при подключении к {api_url}. "
                f"Проверьте, что MOCK_REPLICATE_URL установлен правильно в .env: "
                f"MOCK_REPLICATE_URL=http://mock-replicate:8001"
            )
        else:
            logger.error(f"Ошибка при создании prediction в Replicate: {e}")
        raise
