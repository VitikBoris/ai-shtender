"""
Обработчик вебхуков от Telegram.
"""
import logging
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.domain import logic
from src.services import telegram_api

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


async def process_telegram_update(update_data: dict):
    """
    Обработать обновление от Telegram.
    
    Args:
        update_data: Данные Update от Telegram API
    """
    try:
        # Обработка callback query (нажатие кнопок)
        if "callback_query" in update_data:
            callback_query = update_data["callback_query"]
            logger.info(f"Получен callback_query: {callback_query.get('data')}")
            # TODO: Реализовать обработку callback queries
            return
        
        # Обработка сообщений
        if "message" in update_data:
            message = update_data["message"]
            
            # Обработка команд
            if "text" in message:
                text = message["text"]
                chat_id = message.get("chat", {}).get("id")
                
                if text == "/start":
                    await handle_start_command(chat_id)
                    return
                elif text == "/menu":
                    await handle_menu_command(chat_id)
                    return
                else:
                    # Текстовое сообщение без команды
                    await handle_text_message(chat_id)
                    return
            
            # Обработка фото
            if "photo" in message:
                await logic.process_telegram_photo(update_data)
                return
            
            # Обработка документов (несжатые изображения)
            if "document" in message:
                await logic.process_telegram_document(update_data)
                return
        
        logger.warning(f"Неизвестный тип обновления: {update_data.keys()}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке обновления от Telegram: {e}", exc_info=True)


async def handle_start_command(chat_id: int):
    """Обработка команды /start."""
    welcome_text = (
        "👋 Привет! Я бот для обработки изображений.\n\n"
        "Отправьте мне фото, и я обработаю его для вас.\n"
        "Используйте /menu для выбора режима обработки."
    )
    
    await telegram_api.send_message(chat_id, welcome_text)
    logger.info(f"Отправлено приветствие пользователю {chat_id}")


async def handle_menu_command(chat_id: int):
    """Обработка команды /menu."""
    # TODO: Реализовать меню с inline keyboard
    menu_text = (
        "📋 Меню режимов обработки:\n\n"
        "Режимы будут доступны в следующей версии.\n"
        "Пока используется режим по умолчанию."
    )
    
    await telegram_api.send_message(chat_id, menu_text)
    logger.info(f"Отправлено меню пользователю {chat_id}")


async def handle_text_message(chat_id: int):
    """Обработка текстового сообщения."""
    text = (
        "Пожалуйста, отправьте фото для обработки.\n"
        "Используйте /menu для выбора режима."
    )
    
    await telegram_api.send_message(chat_id, text)
    logger.info(f"Отправлена подсказка пользователю {chat_id}")
