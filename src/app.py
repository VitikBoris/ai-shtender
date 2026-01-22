"""
FastAPI приложение - точка входа для локальной разработки.
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import config
from src.handlers import telegram_webhook, replicate_webhook

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создание FastAPI приложения
app = FastAPI(
    title="Telegram Bot (S3-as-DB)",
    description="Бэкенд для Telegram-бота с обработкой изображений через Replicate",
    version="1.0.0"
)

# Настройка CORS (если нужно)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В проде указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request, call_next):
    """Логирование всех HTTP-запросов."""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - {response.status_code}")
    return response


# Health check endpoint
@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса."""
    return JSONResponse(content={
        "status": "ok",
        "service": "telegram-bot"
    })


# Корневой endpoint для Telegram webhook (совместимость)
# Поддерживает как /, так и /webhook/telegram
@app.post("/")
async def root_webhook(request: Request):
    """Обработчик для корневого пути - перенаправляет на telegram webhook."""
    return await telegram_webhook.telegram_webhook(request)


# Подключение роутов
app.include_router(telegram_webhook.router)
app.include_router(replicate_webhook.router)


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения."""
    logger.info("Приложение запущено")
    logger.info(f"S3 endpoint: {config.S3_ENDPOINT_URL}")
    logger.info(f"S3 bucket: {config.S3_BUCKET}")
    logger.info(f"Base URL: {config.BASE_URL}")
    
    # Проверка конфигурации Replicate
    if config.MOCK_REPLICATE_URL:
        logger.info(f"Mock Replicate URL: {config.MOCK_REPLICATE_URL}")
    else:
        logger.warning(
            "MOCK_REPLICATE_URL не установлен. "
            "Для локальной разработки рекомендуется установить в .env: "
            "MOCK_REPLICATE_URL=http://mock-replicate:8001"
        )
        if not config.REPLICATE_API_TOKEN:
            logger.warning(
                "REPLICATE_API_TOKEN также не установлен. "
                "Приложение не сможет создавать predictions. "
                "Установите MOCK_REPLICATE_URL или REPLICATE_API_TOKEN в .env"
            )


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке приложения."""
    logger.info("Приложение остановлено")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
