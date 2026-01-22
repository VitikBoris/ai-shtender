"""
Утилиты для HTTP-запросов: ретраи, таймауты, backoff.
"""
import asyncio
import logging
import time
from typing import Callable, Any, Optional
from functools import wraps
import httpx

logger = logging.getLogger(__name__)


def retry_request(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    retry_on: tuple = (429, 500, 502, 503, 504)
):
    """
    Декоратор для повторных попыток HTTP-запросов с экспоненциальным backoff.
    
    Args:
        max_retries: Максимальное количество попыток
        backoff_factor: Множитель для задержки между попытками
        retry_on: Кортеж HTTP статус-кодов, при которых нужно повторять запрос
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in retry_on:
                        last_exception = e
                        if attempt < max_retries - 1:
                            wait_time = backoff_factor * (2 ** attempt)
                            logger.warning(
                                f"HTTP {e.response.status_code} при вызове {func.__name__}, "
                                f"попытка {attempt + 1}/{max_retries}, повтор через {wait_time:.1f}с"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                    raise
                except (httpx.RequestError, httpx.TimeoutException) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.warning(
                            f"Ошибка сети при вызове {func.__name__}, "
                            f"попытка {attempt + 1}/{max_retries}, повтор через {wait_time:.1f}с: {e}"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    raise
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


async def make_request(
    method: str,
    url: str,
    timeout: float = 10.0,
    max_retries: int = 3,
    **kwargs
) -> httpx.Response:
    """
    Выполнить HTTP-запрос с таймаутом и автоматическими ретраями.
    
    Args:
        method: HTTP метод (GET, POST, etc.)
        url: URL для запроса
        timeout: Таймаут в секундах
        max_retries: Максимальное количество попыток
        **kwargs: Дополнительные аргументы для httpx (headers, json, data, etc.)
        
    Returns:
        Response объект от httpx
    """
    @retry_request(max_retries=max_retries)
    async def _request():
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
    
    return await _request()
