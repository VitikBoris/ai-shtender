"""
Сервис для взаимодействия с Telegram Bot API.
"""
import logging
from typing import Dict, Any, Optional
import httpx

from src.config import config
from src.utils.http import make_request

logger = logging.getLogger(__name__)

# Базовый URL для Telegram Bot API
TELEGRAM_API_BASE = "https://api.telegram.org/bot"


async def send_message(chat_id: int, text: str, parse_mode: Optional[str] = None) -> Dict[str, Any]:
    """
    Отправить текстовое сообщение пользователю.
    
    Args:
        chat_id: ID чата
        text: Текст сообщения
        parse_mode: Режим парсинга (HTML, Markdown, MarkdownV2)
        
    Returns:
        Ответ от Telegram API
    """
    url = f"{TELEGRAM_API_BASE}{config.TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    try:
        response = await make_request(
            "POST",
            url,
            json=payload,
            timeout=10.0
        )
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")
        raise


async def send_photo(
    chat_id: int,
    photo: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Отправить фото пользователю.
    
    Args:
        chat_id: ID чата
        photo: URL или file_id фото
        caption: Подпись к фото
        parse_mode: Режим парсинга (HTML, Markdown, MarkdownV2)
        
    Returns:
        Ответ от Telegram API
    """
    url = f"{TELEGRAM_API_BASE}{config.TG_BOT_TOKEN}/sendPhoto"
    
    # Если photo - это URL (начинается с http:// или https://), 
    # скачиваем изображение и отправляем как файл через multipart/form-data
    # Это необходимо, т.к. Telegram не может получить доступ к presigned URL от MinIO
    if photo.startswith(("http://", "https://")):
        try:
            # Скачать изображение
            async with httpx.AsyncClient(timeout=30.0) as client:
                image_response = await client.get(photo)
                image_response.raise_for_status()
                image_data = image_response.content
                image_content_type = image_response.headers.get("content-type", "image/jpeg")
            
            # Определить имя файла из URL или использовать дефолтное
            filename = "photo.jpg"
            if ".jpg" in photo.lower() or ".jpeg" in photo.lower():
                filename = "photo.jpg"
            elif ".png" in photo.lower():
                filename = "photo.png"
            
            # Отправить через multipart/form-data
            files = {
                "photo": (filename, image_data, image_content_type)
            }
            data = {
                "chat_id": chat_id
            }
            if caption:
                data["caption"] = caption
            if parse_mode:
                data["parse_mode"] = parse_mode
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, files=files, data=data)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Ошибка при отправке фото по URL в Telegram: {e}")
            raise
    else:
        # Если это file_id, отправляем через JSON как обычно
        payload = {
            "chat_id": chat_id,
            "photo": photo
        }
        if caption:
            payload["caption"] = caption
        if parse_mode:
            payload["parse_mode"] = parse_mode
        
        try:
            response = await make_request(
                "POST",
                url,
                json=payload,
                timeout=10.0
            )
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка при отправке фото в Telegram: {e}")
            raise


async def get_file_info(file_id: str) -> Dict[str, Any]:
    """
    Получить информацию о файле по file_id.
    
    Args:
        file_id: ID файла в Telegram
        
    Returns:
        Информация о файле (file_path, file_size, etc.)
    """
    url = f"{TELEGRAM_API_BASE}{config.TG_BOT_TOKEN}/getFile"
    payload = {
        "file_id": file_id
    }
    
    try:
        response = await make_request(
            "POST",
            url,
            json=payload,
            timeout=10.0
        )
        data = response.json()
        if data.get("ok"):
            return data.get("result", {})
        else:
            raise ValueError(f"Telegram API вернул ошибку: {data.get('description')}")
    except Exception as e:
        logger.error(f"Ошибка при получении информации о файле: {e}")
        raise


async def download_file(file_path: str) -> bytes:
    """
    Скачать файл из Telegram по file_path.
    
    Args:
        file_path: Путь к файлу (из get_file_info)
        
    Returns:
        Байты файла
    """
    url = f"https://api.telegram.org/file/bot{config.TG_BOT_TOKEN}/{file_path}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
    except Exception as e:
        logger.error(f"Ошибка при скачивании файла из Telegram: {e}")
        raise


async def answer_callback_query(
    callback_query_id: str,
    text: Optional[str] = None,
    show_alert: bool = False
) -> Dict[str, Any]:
    """
    Ответить на callback query (убрать "часики" у кнопки).
    
    Args:
        callback_query_id: ID callback query
        text: Текст ответа (опционально)
        show_alert: Показать alert вместо уведомления
        
    Returns:
        Ответ от Telegram API
    """
    url = f"{TELEGRAM_API_BASE}{config.TG_BOT_TOKEN}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_query_id,
        "show_alert": show_alert
    }
    if text:
        payload["text"] = text
    
    try:
        response = await make_request(
            "POST",
            url,
            json=payload,
            timeout=10.0
        )
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка при ответе на callback query: {e}")
        raise
