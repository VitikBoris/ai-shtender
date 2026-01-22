"""
Скрипт для автоматической инициализации MinIO бакета.
Создает бакет и проверяет доступность.
"""
import sys
import os

# Добавить корневую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import config
from src.services import s3_storage
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_minio():
    """Инициализировать MinIO: проверить/создать бакет."""
    try:
        logger.info(f"Инициализация MinIO бакета: {config.S3_BUCKET}")
        logger.info(f"S3 endpoint: {config.S3_ENDPOINT_URL}")
        
        # Получить клиент (это автоматически создаст бакет, если его нет)
        client = s3_storage.get_s3_client()
        
        # Проверить доступность
        try:
            client.head_bucket(Bucket=config.S3_BUCKET)
            logger.info(f"✅ Бакет {config.S3_BUCKET} существует и доступен")
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке бакета: {e}")
            return False
        
        logger.info("✅ MinIO инициализирован успешно")
        logger.info(f"Консоль MinIO: http://localhost:9001 (minioadmin/minioadmin)")
        logger.info(f"API MinIO: http://localhost:9000")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации MinIO: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = init_minio()
    sys.exit(0 if success else 1)
