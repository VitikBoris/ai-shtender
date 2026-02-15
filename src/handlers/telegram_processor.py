"""
Логика обработки Update от Telegram без зависимостей от FastAPI.

Этот модуль нужен, чтобы Yandex Cloud Function (`handler.py`) мог импортировать
обработчик без подтягивания `fastapi` (которого нет в requirements.functions.txt).
"""

import logging
from typing import Any, Dict

from src.domain import logic
from src.services import telegram_api, s3_storage

logger = logging.getLogger(__name__)

# InlineKeyboard для /menu: три режима + кнопка «Назад»
MENU_INLINE_KEYBOARD = {
    "inline_keyboard": [
        [{"text": "Очень хорошая детальная реставрация", "callback_data": "mode=restoration"}],
        [{"text": "Просто апскейл", "callback_data": "mode=upscale"}],
        [{"text": "Только рамка (стиль ветерана)", "callback_data": "mode=frame_veteran"}],
        [{"text": "Назад", "callback_data": "action=back"}],
    ]
}

MODE_LABELS = {
    "restoration": "Очень хорошая детальная реставрация",
    "upscale": "Просто апскейл",
    "frame_veteran": "Только рамка (стиль ветерана)",
}


async def process_telegram_update(update_data: Dict[str, Any]) -> None:
    """
    Обработать обновление от Telegram.

    Args:
        update_data: Данные Update от Telegram API
    """
    try:
        # Обработка callback query (нажатие кнопок меню)
        if "callback_query" in update_data:
            await handle_callback_query(update_data["callback_query"])
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
                if text == "/menu":
                    await handle_menu_command(chat_id)
                    return

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

        logger.warning("Неизвестный тип обновления: %s", list(update_data.keys()))
    except Exception as e:
        logger.error("Ошибка при обработке обновления от Telegram: %s", e, exc_info=True)


async def handle_start_command(chat_id: int) -> None:
    """Обработка команды /start."""
    welcome_text = (
        "👋 Привет! Я бот для обработки изображений.\n\n"
        "Отправьте мне фото, и я обработаю его для вас.\n"
        "Используйте /menu для выбора режима обработки."
    )

    await telegram_api.send_message(chat_id, welcome_text)
    logger.info("Отправлено приветствие пользователю %s", chat_id)


async def handle_menu_command(chat_id: int) -> None:
    """Обработка команды /menu: сообщение с InlineKeyboard (4 кнопки)."""
    menu_text = (
        "📋 Выберите режим обработки фото:"
    )
    await telegram_api.send_message(
        chat_id,
        menu_text,
        reply_markup=MENU_INLINE_KEYBOARD,
    )
    logger.info("Отправлено меню пользователю %s", chat_id)


async def handle_callback_query(callback_query: Dict[str, Any]) -> None:
    """Обработка нажатия кнопки меню: выбор режима или «Назад»."""
    callback_query_id = callback_query.get("id")
    data = callback_query.get("data") or ""
    message = callback_query.get("message") or {}
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    if not callback_query_id or not chat_id or message_id is None:
        logger.warning("Неполные данные callback_query: %s", callback_query)
        return

    # Всегда отвечаем на callback, чтобы убрать «часики»
    try:
        if data == "action=back":
            await telegram_api.answer_callback_query(callback_query_id)
            await telegram_api.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup={"inline_keyboard": []},
            )
            logger.info("Пользователь %s закрыл меню (Назад)", chat_id)
            return

        if data in ("mode=restoration", "mode=upscale", "mode=frame_veteran"):
            mode_value = data.split("=", 1)[1]
            await telegram_api.answer_callback_query(callback_query_id)
            s3_storage.save_user_state(chat_id, {"mode": mode_value})
            label = MODE_LABELS.get(mode_value, mode_value)
            await telegram_api.send_message(
                chat_id,
                f"✅ Выбран режим: {label}",
            )
            logger.info("Пользователь %s выбрал режим: %s", chat_id, mode_value)
            return
    except Exception as e:
        logger.error("Ошибка при обработке callback_query: %s", e, exc_info=True)
        try:
            await telegram_api.answer_callback_query(
                callback_query_id,
                text="Произошла ошибка. Попробуйте ещё раз.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    logger.warning("Неизвестный callback_data: %s", data)
    await telegram_api.answer_callback_query(callback_query_id)


async def handle_text_message(chat_id: int) -> None:
    """Обработка текстового сообщения."""
    text = (
        "Пожалуйста, отправьте фото для обработки.\n"
        "Используйте /menu для выбора режима."
    )

    await telegram_api.send_message(chat_id, text)
    logger.info("Отправлена подсказка пользователю %s", chat_id)

