"""
Бизнес-логика обработки фото и вебхуков.
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import mimetypes

import httpx

from src.config import config
from src.domain.models import TaskState, TaskStatus, BotMode
from src.services import s3_storage, telegram_api, replicate_api
from src.utils.images import get_largest_photo, validate_image_mime, validate_image_size

logger = logging.getLogger(__name__)


async def process_telegram_image(
    update_data: Dict[str, Any],
    file_id: Optional[str] = None,
    file_size: Optional[int] = None,
    file_name: Optional[str] = None,
    mime_type: Optional[str] = None
) -> None:
    """
    Обработать изображение от пользователя: скачать, загрузить в S3, отправить в Replicate.
    Универсальная функция для обработки как фото, так и документов-изображений.
    
    Args:
        update_data: Данные Update от Telegram API
        file_id: ID файла (если уже известен, например из document)
        file_size: Размер файла (если уже известен)
        file_name: Имя файла (для документов)
        mime_type: MIME-тип файла (для документов)
    """
    try:
        message = update_data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        message_id = message.get("message_id")
        
        if not chat_id or not user_id:
            logger.error("Не удалось извлечь chat_id или user_id из сообщения")
            return
        
        # Если file_id не передан, попробовать извлечь из фото
        if not file_id:
            photos = message.get("photo", [])
            if not photos:
                logger.warning(f"Сообщение от {chat_id} не содержит фото")
                await telegram_api.send_message(
                    chat_id,
                    "Пожалуйста, отправьте фото для обработки."
                )
                return
            
            largest_photo = get_largest_photo(photos)
            file_id = largest_photo.get("file_id")
            file_size = largest_photo.get("file_size", 0)
        
        logger.info(f"Обработка изображения от пользователя {user_id} (chat {chat_id}), file_id: {file_id}")
        
        # Скачать файл через Telegram API
        file_info = await telegram_api.get_file_info(file_id)
        file_path = file_info.get("file_path")
        actual_file_size = file_info.get("file_size", file_size)
        
        # Проверить размер
        if not validate_image_size(actual_file_size, config.MAX_IMAGE_MB):
            await telegram_api.send_message(
                chat_id,
                f"Размер файла превышает лимит {config.MAX_IMAGE_MB} MB. Пожалуйста, отправьте файл меньшего размера."
            )
            return
        
        # Скачать файл
        file_data = await telegram_api.download_file(file_path)
        
        # Определить MIME-тип (если не передан)
        if not mime_type:
            # Сначала попробовать из file_name (для документов)
            if file_name:
                mime_type, _ = mimetypes.guess_type(file_name)
            
            # Если не получилось, попробовать из file_path
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(file_path or "")
            
            # Если все еще не получилось, определить по расширению
            if not mime_type:
                if file_path and file_path.lower().endswith(('.jpg', '.jpeg')):
                    mime_type = "image/jpeg"
                elif file_path and file_path.lower().endswith('.png'):
                    mime_type = "image/png"
                elif file_name:
                    if file_name.lower().endswith(('.jpg', '.jpeg')):
                        mime_type = "image/jpeg"
                    elif file_name.lower().endswith('.png'):
                        mime_type = "image/png"
                else:
                    mime_type = "image/jpeg"  # Дефолт
        
        # Проверить MIME-тип
        if not validate_image_mime(mime_type, config.ALLOWED_IMAGE_MIME):
            await telegram_api.send_message(
                chat_id,
                f"Неподдерживаемый формат изображения. Разрешены: {', '.join(config.ALLOWED_IMAGE_MIME)}"
            )
            return
        
        # Генерировать UUID для имени файла
        file_uuid = str(uuid.uuid4())
        now = datetime.utcnow()
        date_path = f"{now.year}/{now.month:02d}/{now.day:02d}"
        
        # Определить расширение из MIME-типа или имени файла
        if mime_type == "image/jpeg":
            extension = ".jpg"
        elif mime_type == "image/png":
            extension = ".png"
        elif file_name:
            # Попробовать извлечь расширение из имени файла
            if file_name.lower().endswith(('.jpg', '.jpeg')):
                extension = ".jpg"
            elif file_name.lower().endswith('.png'):
                extension = ".png"
            else:
                extension = ".jpg"  # Дефолт
        else:
            extension = ".jpg"  # Дефолт
        
        s3_key = f"images/input/{date_path}/{file_uuid}{extension}"
        
        # Загрузить в S3
        s3_storage.upload_to_s3(
            bucket=config.S3_BUCKET,
            key=s3_key,
            data=file_data,
            content_type=mime_type
        )
        logger.info(f"Фото загружено в S3: {s3_key}")
        
        # Генерировать presigned URL
        presigned_url = s3_storage.generate_presigned_url(
            bucket=config.S3_BUCKET,
            key=s3_key,
            expires_in=config.S3_PRESIGN_EXPIRES_SECONDS
        )
        
        # Определить режим: из users/{chat_id}.json или дефолт из конфига
        user_state = s3_storage.load_user_state(chat_id)
        mode_str = (user_state or {}).get("mode") or config.DEFAULT_MODE
        try:
            mode = BotMode(mode_str)
        except ValueError:
            mode = BotMode(config.DEFAULT_MODE)
        
        # Создать prediction в Mock Replicate
        webhook_url = f"{config.BASE_URL}/webhook/replicate"
        
        try:
            # В real-режиме Replicate требует version id модели. В mock-режиме параметр игнорируется.
            prediction_response = await replicate_api.create_prediction(
                image_url=presigned_url,
                webhook_url=webhook_url,
                model=config.REPLICATE_MODEL_VERSION,
                webhook_events_filter=["completed"]
            )
            prediction_id = prediction_response.get("id")
            
            if not prediction_id:
                raise ValueError("Replicate API не вернул prediction_id")
            
            logger.info(f"Prediction создан: {prediction_id}")
        except Exception as e:
            # Более понятные сообщения для типовых ошибок реального Replicate
            user_message = "Произошла ошибка при отправке задачи на обработку. Попробуйте позже."
            if isinstance(e, ValueError):
                # Например: не задан REPLICATE_API_TOKEN или REPLICATE_MODEL_VERSION
                user_message = "Сервис обработки не настроен. Сообщите администратору (Replicate config)."
            elif isinstance(e, httpx.HTTPStatusError):
                status = e.response.status_code
                if status in (401, 403):
                    user_message = "Сервис обработки недоступен из‑за ошибки авторизации. Попробуйте позже."
                elif status == 429:
                    user_message = "Слишком много запросов к сервису обработки. Попробуйте чуть позже."
                elif 500 <= status <= 599:
                    user_message = "Сервис обработки временно недоступен. Попробуйте позже."

            logger.error(
                f"Ошибка при создании prediction (chat_id={chat_id}, user_id={user_id}): {e}",
                exc_info=True
            )
            await telegram_api.send_message(
                chat_id,
                user_message
            )
            return
        
        # Сохранить состояние задачи в S3
        task_state = TaskState(
            prediction_id=prediction_id,
            chat_id=chat_id,
            user_id=user_id,
            mode=mode,
            input_s3_key=s3_key,
            status=TaskStatus.QUEUED,
            telegram={
                "file_id": file_id,
                "message_id": message_id
            },
            input={
                "s3_key": s3_key,
                "mime": mime_type,
                "size_bytes": actual_file_size
            }
        )
        
        s3_storage.save_task_state(prediction_id, task_state.to_dict())
        logger.info(f"Состояние задачи сохранено: {prediction_id}")
        
        # Отправить пользователю подтверждение
        await telegram_api.send_message(
            chat_id,
            "✅ Принял. Обрабатываю изображение, ожидайте результат..."
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}", exc_info=True)
        # Попытаться отправить сообщение об ошибке пользователю
        try:
            message = update_data.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            if chat_id:
                await telegram_api.send_message(
                    chat_id,
                    "❌ Произошла ошибка при обработке фото. Попробуйте еще раз."
                )
        except:
            pass


async def process_telegram_photo(update_data: Dict[str, Any]) -> None:
    """
    Обработать фото от пользователя (обертка для обратной совместимости).
    
    Args:
        update_data: Данные Update от Telegram API
    """
    await process_telegram_image(update_data)


async def process_telegram_document(update_data: Dict[str, Any]) -> None:
    """
    Обработать документ-изображение от пользователя.
    
    Args:
        update_data: Данные Update от Telegram API
    """
    try:
        message = update_data.get("message", {})
        document = message.get("document", {})
        
        if not document:
            return
        
        # Проверить, что это изображение
        doc_mime_type = document.get("mime_type", "")
        doc_file_name = document.get("file_name", "")
        
        # Список разрешенных MIME-типов изображений
        image_mime_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        
        is_image = False
        if doc_mime_type and doc_mime_type.lower() in image_mime_types:
            is_image = True
        elif doc_file_name:
            file_ext = doc_file_name.lower()
            is_image = any(file_ext.endswith(ext) for ext in image_extensions)
        
        if not is_image:
            logger.info(f"Получен документ, но не изображение: {doc_mime_type} от {message.get('chat', {}).get('id')}")
            return
        
        # Извлечь данные документа
        file_id = document.get("file_id")
        file_size = document.get("file_size", 0)
        
        logger.info(f"Обработка документа-изображения: {doc_file_name}, file_id: {file_id}")
        
        # Использовать универсальную функцию обработки
        await process_telegram_image(
            update_data,
            file_id=file_id,
            file_size=file_size,
            file_name=doc_file_name,
            mime_type=doc_mime_type
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке документа-изображения: {e}", exc_info=True)
        try:
            message = update_data.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            if chat_id:
                await telegram_api.send_message(
                    chat_id,
                    "❌ Произошла ошибка при обработке изображения. Попробуйте еще раз."
                )
        except:
            pass


async def process_replicate_webhook(webhook_data: Dict[str, Any]) -> None:
    """
    Обработать вебхук от Replicate: получить результат и отправить пользователю.
    
    Args:
        webhook_data: Данные вебхука от Replicate
    """
    try:
        prediction_id = webhook_data.get("id")
        status = webhook_data.get("status")
        
        if not prediction_id:
            logger.error("Вебхук от Replicate не содержит prediction_id")
            return
        
        logger.info(f"Обработка вебхука для prediction {prediction_id}, статус: {status}")
        
        # Загрузить состояние задачи из S3
        task_dict = s3_storage.load_task_state(prediction_id)
        if not task_dict:
            logger.warning(f"Состояние задачи не найдено для prediction {prediction_id}, возможно уже обработано")
            return
        
        task_state = TaskState.from_dict(task_dict)
        
        # Проверка идемпотентности: если уже обработано, просто вернуть 200
        if task_state.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED):
            logger.info(f"Задача {prediction_id} уже обработана (статус: {task_state.status}), пропускаем")
            return
        
        # Обновить статус
        if status == "succeeded":
            task_state.update_status(TaskStatus.SUCCEEDED)
        elif status == "failed":
            task_state.update_status(TaskStatus.FAILED)
        elif status == "processing":
            task_state.update_status(TaskStatus.PROCESSING)
        
        # Обработать результат
        if status == "succeeded":
            output = webhook_data.get("output")
            if not output:
                logger.error(f"Вебхук succeeded, но output отсутствует для {prediction_id}")
                task_state.error = {"message": "Результат обработки отсутствует"}
                await telegram_api.send_message(
                    task_state.chat_id,
                    "❌ Ошибка: результат обработки не получен."
                )
            else:
                # output может быть строкой (URL) или массивом
                if isinstance(output, list) and len(output) > 0:
                    output_url = output[0]
                elif isinstance(output, str):
                    output_url = output
                else:
                    output_url = str(output)
                
                task_state.result = {
                    "output_url": output_url
                }
                
                # Отправить фото пользователю
                await telegram_api.send_photo(
                    chat_id=task_state.chat_id,
                    photo=output_url,
                    caption="✅ Обработка завершена!"
                )
                logger.info(f"Результат отправлен пользователю {task_state.chat_id}")
        
        elif status == "failed":
            error_info = webhook_data.get("error", "Неизвестная ошибка")
            error_message = error_info if isinstance(error_info, str) else error_info.get("message", "Неизвестная ошибка")
            
            task_state.error = {
                "message": error_message
            }
            
            # Отправить сообщение об ошибке пользователю (без технических деталей)
            await telegram_api.send_message(
                task_state.chat_id,
                "❌ Произошла ошибка при обработке изображения. Попробуйте еще раз."
            )
            logger.warning(f"Обработка завершилась ошибкой для {prediction_id}: {error_message}")
        
        # Обновить состояние в S3
        task_state.updated_at = datetime.utcnow()
        s3_storage.save_task_state(prediction_id, task_state.to_dict())
        logger.info(f"Состояние задачи обновлено: {prediction_id}, статус: {status}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука от Replicate: {e}", exc_info=True)
