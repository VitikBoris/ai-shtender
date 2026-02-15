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


async def send_message(
    chat_id: int,
    text: str,
    parse_mode: Optional[str] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Отправить текстовое сообщение пользователю.

    Args:
        chat_id: ID чата
        text: Текст сообщения
        parse_mode: Режим парсинга (HTML, Markdown, MarkdownV2)
        reply_markup: InlineKeyboardMarkup или другая разметка (dict для JSON)

    Returns:
        Ответ от Telegram API
    """
    url = f"{TELEGRAM_API_BASE}{config.TG_BOT_TOKEN}/sendMessage"
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        response = await make_request(
            "POST",
            url,
            json=payload,
            timeout=10.0,
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
            # Важно: многие CDN/хранилища отдают 302/301 на реальный файл.
            # По умолчанию httpx НЕ следует редиректам, из-за чего можно скачать не картинку,
            # а HTML/redirect-заглушку, и Telegram вернет 400 на sendPhoto.
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                image_response = await client.get(photo)
                image_response.raise_for_status()
                image_data = image_response.content
                image_content_type = (image_response.headers.get("content-type") or "").split(";")[0].strip().lower()
                if not image_content_type:
                    image_content_type = "application/octet-stream"
            
            # Определить имя файла из URL или использовать дефолтное
            filename = "photo.jpg"
            if ".jpg" in photo.lower() or ".jpeg" in photo.lower():
                filename = "photo.jpg"
            elif ".png" in photo.lower():
                filename = "photo.png"

            # Если формат/размер подозрительные — отправим как документ (Telegram менее строгий).
            size_mb = len(image_data) / (1024 * 1024) if image_data else 0.0
            should_send_as_document = False
            if image_content_type not in ("image/jpeg", "image/png"):
                # Входные форматы у нас ограничены, а вот выход Replicate может быть разным.
                should_send_as_document = True
            if size_mb > float(config.MAX_IMAGE_MB):
                should_send_as_document = True

            if should_send_as_document:
                return await send_document_bytes(
                    chat_id=chat_id,
                    document=image_data,
                    filename=filename,
                    caption=caption,
                    parse_mode=parse_mode,
                    content_type=image_content_type,
                )
            
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
                try:
                    response = await client.post(url, files=files, data=data)
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    # Если Telegram не принял "photo" (400), попробуем отправить тем же контентом как документ.
                    if e.response is not None and e.response.status_code == 400:
                        logger.error(
                            "Telegram sendPhoto вернул 400. Ответ: %s",
                            (e.response.text or "").strip()
                        )
                        return await send_document_bytes(
                            chat_id=chat_id,
                            document=image_data,
                            filename=filename,
                            caption=caption,
                            parse_mode=parse_mode,
                            content_type=image_content_type,
                        )
                    raise
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


async def send_document_bytes(
    chat_id: int,
    document: bytes,
    filename: str = "file",
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    content_type: str = "application/octet-stream",
) -> Dict[str, Any]:
    """
    Отправить файл пользователю как документ (multipart/form-data).
    Используется как fallback, когда sendPhoto не принимает содержимое.
    """
    url = f"{TELEGRAM_API_BASE}{config.TG_BOT_TOKEN}/sendDocument"

    files = {
        "document": (filename, document, content_type)
    }
    data: Dict[str, Any] = {
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


async def edit_message_reply_markup(
    chat_id: int,
    message_id: int,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Изменить разметку (клавиатуру) у сообщения. Пустой reply_markup убирает кнопки.

    Args:
        chat_id: ID чата
        message_id: ID сообщения
        reply_markup: Новая разметка или None (убрать кнопки)

    Returns:
        Ответ от Telegram API
    """
    url = f"{TELEGRAM_API_BASE}{config.TG_BOT_TOKEN}/editMessageReplyMarkup"
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    try:
        response = await make_request(
            "POST",
            url,
            json=payload,
            timeout=10.0,
        )
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка при изменении разметки сообщения в Telegram: {e}")
        raise
