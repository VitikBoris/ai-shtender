"""
Конфигурация приложения - чтение и валидация переменных окружения.
"""
import os
import logging
from typing import Optional, List
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Конфигурация приложения из переменных окружения."""
    
    # Telegram
    TG_BOT_TOKEN: str
    
    # S3 / MinIO
    S3_BUCKET: str
    S3_ENDPOINT_URL: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    S3_FORCE_PATH_STYLE: bool = True
    S3_USE_SSL: bool = False
    S3_PRESIGN_EXPIRES_SECONDS: int = 3600
    
    # Webhook
    BASE_URL: str
    MOCK_REPLICATE_URL: Optional[str] = None
    
    # Replicate (опционально, для реального API)
    REPLICATE_API_TOKEN: Optional[str] = None
    REPLICATE_MODEL_VERSION: Optional[str] = None
    
    # Лимиты
    MAX_IMAGE_MB: int = 10
    ALLOWED_IMAGE_MIME: List[str] = ["image/jpeg", "image/png"]
    DEFAULT_MODE: str = "process_photo"
    
    # Логирование
    LOG_LEVEL: str = "INFO"
    
    def __init__(self):
        """Инициализация конфигурации с валидацией обязательных переменных."""
        # Обязательные переменные
        self.TG_BOT_TOKEN = self._get_required("TG_BOT_TOKEN")
        self.S3_BUCKET = self._get_required("S3_BUCKET")
        self.S3_ENDPOINT_URL = self._get_required("S3_ENDPOINT_URL")
        self.AWS_ACCESS_KEY_ID = self._get_required("AWS_ACCESS_KEY_ID")
        self.AWS_SECRET_ACCESS_KEY = self._get_required("AWS_SECRET_ACCESS_KEY")
        self.BASE_URL = self._get_required("BASE_URL")
        
        # Опциональные с дефолтами
        self.S3_FORCE_PATH_STYLE = self._get_bool("S3_FORCE_PATH_STYLE", True)
        self.S3_USE_SSL = self._get_bool("S3_USE_SSL", False)
        self.S3_PRESIGN_EXPIRES_SECONDS = self._get_int("S3_PRESIGN_EXPIRES_SECONDS", 3600)
        self.MAX_IMAGE_MB = self._get_int("MAX_IMAGE_MB", 10)
        self.DEFAULT_MODE = os.getenv("DEFAULT_MODE", "process_photo")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.MOCK_REPLICATE_URL = os.getenv("MOCK_REPLICATE_URL")
        self.REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
        # В реальном Replicate API требуется именно version id модели
        self.REPLICATE_MODEL_VERSION = os.getenv("REPLICATE_MODEL_VERSION")
        
        # Разбор ALLOWED_IMAGE_MIME
        mime_str = os.getenv("ALLOWED_IMAGE_MIME", "image/jpeg,image/png")
        self.ALLOWED_IMAGE_MIME = [m.strip() for m in mime_str.split(",")]
        
        logger.info("Конфигурация загружена успешно")
    
    def _get_required(self, key: str) -> str:
        """Получить обязательную переменную окружения."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Обязательная переменная окружения {key} не установлена")
        return value
    
    def _get_bool(self, key: str, default: bool) -> bool:
        """Получить булеву переменную окружения."""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ("1", "true", "yes", "on")
    
    def _get_int(self, key: str, default: int) -> int:
        """Получить целочисленную переменную окружения."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logger.warning(f"Не удалось преобразовать {key}={value} в int, используется дефолт {default}")
            return default


# Глобальный экземпляр конфигурации
config = Config()
