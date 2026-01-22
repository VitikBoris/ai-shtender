"""
Локальный эмулятор Replicate API для разработки и тестирования.
"""
import asyncio
import logging
import uuid
import random
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import httpx
from PIL import Image
import io
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mock Replicate API")

# Хранилище задач в памяти (в проде можно использовать БД)
tasks: Dict[str, Dict[str, Any]] = {}


async def process_image_async(
    prediction_id: str,
    image_url: str,
    webhook_url: str
):
    """
    Асинхронная обработка изображения (эмуляция).
    
    Args:
        prediction_id: ID предсказания
        image_url: URL исходного изображения
        webhook_url: URL для отправки вебхука
    """
    try:
        # Имитация задержки обработки (2-5 секунд)
        delay = random.uniform(2.0, 5.0)
        logger.info(f"Prediction {prediction_id}: имитация обработки, задержка {delay:.1f}с")
        await asyncio.sleep(delay)
        
        # Обновить статус на processing
        if prediction_id in tasks:
            tasks[prediction_id]["status"] = "processing"
        
        # Скачать исходное изображение
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            image_data = response.content
            
            # Простая трансформация: можно просто вернуть исходное изображение
            # или применить простую обработку через PIL
            image = Image.open(io.BytesIO(image_data))
            
            # Для эмуляции можно просто вернуть исходное изображение
            # Или применить простую трансформацию (например, изменение размера)
            # Здесь просто используем исходное изображение
            
            # Сохранить результат во временный файл или загрузить куда-то
            # Для простоты эмуляции вернем исходный URL
            # В реальном сценарии нужно загрузить результат в S3 или другой хостинг
            
            output_url = image_url  # В эмуляции возвращаем исходный URL
            
            # Обновить статус на succeeded
            if prediction_id in tasks:
                tasks[prediction_id]["status"] = "succeeded"
                tasks[prediction_id]["output"] = output_url
            
            # Отправить вебхук
            webhook_data = {
                "id": prediction_id,
                "status": "succeeded",
                "output": output_url
            }
            
            logger.info(f"Prediction {prediction_id}: отправка вебхука на {webhook_url}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(webhook_url, json=webhook_data)
                    response.raise_for_status()
                    logger.info(f"Вебхук успешно отправлен для {prediction_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке вебхука для {prediction_id}: {e}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке изображения для {prediction_id}: {e}")
            # Обновить статус на failed
            if prediction_id in tasks:
                tasks[prediction_id]["status"] = "failed"
                tasks[prediction_id]["error"] = {"message": str(e)}
            
            # Отправить вебхук с ошибкой
            webhook_data = {
                "id": prediction_id,
                "status": "failed",
                "error": {"message": str(e)}
            }
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.post(webhook_url, json=webhook_data)
            except Exception as webhook_error:
                logger.error(f"Ошибка при отправке вебхука с ошибкой: {webhook_error}")
    
    except Exception as e:
        logger.error(f"Критическая ошибка при обработке {prediction_id}: {e}", exc_info=True)


@app.post("/v1/predictions")
async def create_prediction(request: Dict[str, Any]):
    """
    Создать prediction (эмуляция Replicate API).
    
    Принимает:
    - input.image: URL изображения
    - webhook: URL для вебхука
    - webhook_events_filter: список событий
    """
    try:
        input_data = request.get("input", {})
        image_url = input_data.get("image")
        webhook_url = request.get("webhook")
        webhook_events_filter = request.get("webhook_events_filter", ["completed"])
        
        if not image_url:
            raise HTTPException(status_code=400, detail="input.image обязателен")
        
        if not webhook_url:
            raise HTTPException(status_code=400, detail="webhook обязателен")
        
        # Генерировать prediction_id
        prediction_id = str(uuid.uuid4())
        
        # Сохранить задачу
        tasks[prediction_id] = {
            "id": prediction_id,
            "status": "starting",
            "input": input_data,
            "webhook": webhook_url,
            "webhook_events_filter": webhook_events_filter,
            "created_at": None
        }
        
        logger.info(f"Создан prediction {prediction_id} для изображения {image_url}")
        
        # Запустить асинхронную обработку
        asyncio.create_task(process_image_async(prediction_id, image_url, webhook_url))
        
        # Вернуть ответ сразу
        return JSONResponse(content={
            "id": prediction_id,
            "status": "starting",
            "input": input_data,
            "webhook": webhook_url,
            "webhook_events_filter": webhook_events_filter
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании prediction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/predictions/{prediction_id}")
async def get_prediction(prediction_id: str):
    """
    Получить статус prediction (опционально, для проверки).
    """
    if prediction_id not in tasks:
        raise HTTPException(status_code=404, detail="Prediction не найден")
    
    return JSONResponse(content=tasks[prediction_id])


@app.get("/health")
async def health_check():
    """Проверка работоспособности."""
    return JSONResponse(content={"status": "ok", "service": "mock-replicate"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
