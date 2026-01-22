"""
Обработчик вебхуков от Replicate (или Mock Replicate).
"""
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from src.domain import logic

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook/replicate")
async def replicate_webhook(request: Request):
    """
    Обработчик вебхуков от Replicate с результатами обработки.
    
    Вебхук должен быть идемпотентным - повторные вызовы не должны вызывать дубликаты.
    """
    try:
        webhook_data = await request.json()
        logger.info(f"Получен вебхук от Replicate: {webhook_data.get('id')}, статус: {webhook_data.get('status')}")
        
        # Обработать вебхук асинхронно
        import asyncio
        asyncio.create_task(logic.process_replicate_webhook(webhook_data))
        
        # Всегда возвращаем 200 OK, чтобы Replicate не ретраил
        return JSONResponse(content={"ok": True})
        
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука от Replicate: {e}", exc_info=True)
        # Всегда возвращаем 200 OK, чтобы Replicate не ретраил
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=200)
