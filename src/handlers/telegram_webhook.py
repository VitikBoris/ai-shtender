"""
Обработчик вебхуков от Telegram.
"""
import logging
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.handlers.telegram_processor import process_telegram_update

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Обработчик вебхуков от Telegram.
    
    Обрабатывает Update от Telegram API:
    - команды (/start, /menu)
    - сообщения с фото
    - callback queries
    """
    try:
        update_data = await request.json()
        logger.info(f"Получен Update от Telegram: {update_data.get('update_id')}")
        
        # Обработать обновление асинхронно, чтобы быстро ответить Telegram
        asyncio.create_task(process_telegram_update(update_data))
        
        # Всегда возвращаем 200 OK быстро, чтобы Telegram не ретраил
        return JSONResponse(content={"ok": True})
        
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука от Telegram: {e}", exc_info=True)
        # Всегда возвращаем 200 OK, чтобы Telegram не ретраил
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=200)
