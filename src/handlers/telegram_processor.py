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

# Кнопки меню: Детализация (обработка фото), Создание штендера (лицо + PDF)
MENU_INLINE_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "🖼 Детализация", "callback_data": "mode=detailization"},
            {"text": "📋 Создание штендера", "callback_data": "mode=shtender"},
        ],
        [{"text": "« Назад", "callback_data": "action=back"}],
    ]
}


async def process_telegram_update(update_data: Dict[str, Any]) -> None:
    """
    Обработать обновление от Telegram.

    Args:
        update_data: Данные Update от Telegram API
    """
    try:
        # Обработка нажатий на кнопки меню (callback_query)
        if "callback_query" in update_data:
            await handle_callback_query(update_data["callback_query"])
            return

        # Обработка сообщений
        if "message" in update_data:
            message = update_data["message"]

            # Обработка команд
            if "text" in message:
                text = (message.get("text") or "").strip()
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
        "Выберите режим в меню: /menu\n"
        "• **Детализация** — улучшение фото (реставрация).\n"
        "• **Создание штендера** — распознавание лица и генерация PDF-штендера.\n\n"
        "Отправьте фото после выбора режима."
    )
    await telegram_api.send_message(chat_id, welcome_text, parse_mode="Markdown")
    logger.info("Отправлено приветствие пользователю %s", chat_id)


async def handle_menu_command(chat_id: int) -> None:
    """Показать меню с двумя кнопками: Детализация и Создание штендера."""
    text = "Выберите режим:"
    await telegram_api.send_message(
        chat_id,
        text,
        reply_markup=MENU_INLINE_KEYBOARD,
    )
    logger.info("Отправлено меню пользователю %s", chat_id)


async def handle_callback_query(callback: Dict[str, Any]) -> None:
    """Обработка нажатия на кнопку меню (callback_query)."""
    callback_id = callback.get("id")
    data = callback.get("data", "")
    message = callback.get("message") or {}
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    if not callback_id or not chat_id:
        logger.warning("callback_query без id или chat_id: %s", callback)
        return

    await telegram_api.answer_callback_query(callback_id)

    if data == "action=back":
        await telegram_api.edit_message_reply_markup(
            chat_id,
            message_id,
            reply_markup={"inline_keyboard": []},
        )
        logger.info("Меню закрыто пользователем %s", chat_id)
        return

    if data == "mode=detailization":
        s3_storage.save_user_state(chat_id, {"mode": "restoration"})
        await telegram_api.send_message(chat_id, "✅ Выбран режим: **Детализация**. Отправьте фото для обработки.", parse_mode="Markdown")
        logger.info("Пользователь %s выбрал режим: детализация", chat_id)
        return
    if data == "mode=shtender":
        s3_storage.save_user_state(chat_id, {"mode": "shtender"})
        await telegram_api.send_message(chat_id, "✅ Выбран режим: **Создание штендера**. Отправьте фото с лицом для генерации PDF.", parse_mode="Markdown")
        logger.info("Пользователь %s выбрал режим: штендер", chat_id)
        return

    logger.warning("Неизвестный callback_data: %s", data)


async def handle_text_message(chat_id: int) -> None:
    """Обработка текстового сообщения."""
    text = (
        "Отправьте фото для обработки или откройте меню: /menu"
    )
    await telegram_api.send_message(chat_id, text)
    logger.info("Отправлена подсказка пользователю %s", chat_id)
