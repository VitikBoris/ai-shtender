"""
Утилиты для работы с изображениями: валидация, выбор размера.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def get_largest_photo(photo_sizes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Выбрать фото максимального размера из массива размеров.
    
    Args:
        photo_sizes: Массив объектов с размерами фото от Telegram API
        
    Returns:
        Объект с максимальным размером (обычно последний в массиве)
    """
    if not photo_sizes:
        raise ValueError("Массив размеров фото пуст")
    
    # Обычно Telegram возвращает размеры в порядке возрастания,
    # последний элемент - самый большой
    largest = photo_sizes[-1]
    logger.debug(f"Выбран размер фото: {largest.get('width')}x{largest.get('height')}, file_id: {largest.get('file_id')}")
    return largest


def validate_image_mime(mime_type: str, allowed_mimes: List[str]) -> bool:
    """
    Проверить, разрешен ли MIME-тип изображения.
    
    Args:
        mime_type: MIME-тип для проверки
        allowed_mimes: Список разрешенных MIME-типов
        
    Returns:
        True если разрешен, False иначе
    """
    if not mime_type:
        return False
    
    mime_lower = mime_type.lower().strip()
    allowed_lower = [m.lower().strip() for m in allowed_mimes]
    
    is_allowed = mime_lower in allowed_lower
    if not is_allowed:
        logger.warning(f"MIME-тип {mime_type} не разрешен. Разрешенные: {allowed_mimes}")
    
    return is_allowed


def validate_image_size(size_bytes: int, max_mb: int) -> bool:
    """
    Проверить, не превышает ли размер файла максимальный лимит.
    
    Args:
        size_bytes: Размер файла в байтах
        max_mb: Максимальный размер в мегабайтах
        
    Returns:
        True если размер в пределах лимита, False иначе
    """
    max_bytes = max_mb * 1024 * 1024
    
    if size_bytes > max_bytes:
        size_mb = size_bytes / (1024 * 1024)
        logger.warning(f"Размер файла {size_mb:.2f} MB превышает лимит {max_mb} MB")
        return False
    
    return True
