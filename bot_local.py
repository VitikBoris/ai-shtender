"""
Локальный Telegram-бот для обработки фото (Пункт 1).
Базовый функционал: команда /start и возврат отправленного фото обратно пользователю.
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Загрузка переменных окружения из .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получение токена из переменных окружения
TELEGRAM_TOKEN = os.getenv('TG_BOT_TOKEN')

if not TELEGRAM_TOKEN:
    raise ValueError(
        "TG_BOT_TOKEN не найден в переменных окружения. "
        "Создайте файл .env и добавьте TG_BOT_TOKEN=ваш_токен"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_message = (
        "👋 Привет! Я бот для обработки изображений.\n\n"
        "📸 **Как пользоваться:**\n"
        "Просто отправьте мне фотографию, и я верну её обратно.\n\n"
        "В дальнейшем здесь будет обработка изображений через нейросети!"
    )
    
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_message,
            parse_mode='Markdown'
        )
        logger.info(f"Команда /start от пользователя {update.effective_chat.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке приветственного сообщения: {e}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фото: скачивает и отправляет то же фото обратно"""
    try:
        # Получаем фото (берем самое большое разрешение - последнее в списке)
        photo = update.message.photo[-1]
        file = await photo.get_file()
        
        logger.info(f"Получено фото от пользователя {update.effective_chat.id}, file_id: {file.file_id}")
        
        # Отправляем пользователю то же самое фото обратно
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=file.file_id,  # Используем file_id для отправки того же фото
            caption="✅ Вот ваше фото!"
        )
        
        logger.info(f"Фото успешно отправлено обратно пользователю {update.effective_chat.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}", exc_info=True)
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Произошла ошибка при обработке фото. Попробуйте еще раз."
            )
        except Exception as send_error:
            logger.error(f"Не удалось отправить сообщение об ошибке: {send_error}")


def main():
    """Главная функция для запуска бота"""
    if not TELEGRAM_TOKEN:
        logger.error("TG_BOT_TOKEN не установлен. Проверьте файл .env")
        return
    
    # Создание приложения бота
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Регистрация обработчиков
    start_handler = CommandHandler('start', start)
    photo_handler = MessageHandler(filters.PHOTO, handle_photo)
    
    application.add_handler(start_handler)
    application.add_handler(photo_handler)
    
    logger.info("Бот запущен и ожидает сообщений...")
    
    # Запуск бота в режиме polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
