# Пункт 2: Интеграция с локальным эмулятором Replicate

План: [feature-plan.md](feature-plan.md)

**Коммит:** не реализовано

## Цель

Добавить локальный HTTP-сервис, эмулирующий Replicate API (асинхронные вебхуки), и интегрировать его с ботом через архитектуру S3-as-DB.

## Задачи

1. **Настройка локальной инфраструктуры (Docker Compose)**

   - Создать `docker-compose.yml`:
     - Сервис `minio` (порт 9000 - API, 9001 - консоль)
     - Сервис `app` (FastAPI приложение, порт 8000)
   - Настроить переменные окружения для MinIO в `.env`

2. **Настройка MinIO (S3-эмулятор)**

   - Создать скрипт инициализации или инструкцию:
     - Создать бакет `my-bot-bucket`
     - Настроить структуру: `images/input/` и `tasks/`
     - (Опционально) Настроить lifecycle policy для автоочистки `tasks/` старше 1 дня

3. **Создание локального эмулятора Replicate** (файл `mock_replicate.py`)

   - FastAPI приложение с эндпоинтом `POST /v1/predictions`
   - Принимает запрос с `input.image` (URL), `webhook` (URL), `webhook_events_filter`
   - Генерирует `prediction_id` (UUID)
   - Сохраняет задачу в память/файл (для тестов)
   - Асинхронно (через `asyncio.create_task`) эмулирует обработку:
     - Имитация задержки 2-5 секунд
     - Копирование исходного изображения как "результат" (или простая трансформация)
     - Отправка POST-запроса на указанный `webhook` с данными:
       ```json
       {
         "id": "prediction_id",
         "status": "succeeded",
         "output": "https://url-to-result.jpg"
       }
       ```

4. **Обновление бота для работы с S3 и вебхуками**

   - Миграция с `python-telegram-bot` (polling) на FastAPI (webhook-режим)
   - Создать `main.py` (FastAPI) с двумя эндпоинтами:
     - `POST /webhook/telegram`: обработка сообщений от Telegram
     - `POST /webhook/replicate`: обработка колбэков от эмулятора Replicate
   - В `handler.py` (или модуль внутри `main.py`):
     - При получении фото: скачать через Telegram API, загрузить в S3 (`images/input/{uuid}.jpg`)
     - Генерировать presigned URL для S3-файла (срок действия 1 час)
     - Отправить запрос в эмулятор Replicate (`mock_replicate.py`) с `webhook: BASE_URL/webhook/replicate`
     - Сохранить состояние в S3: `tasks/{prediction_id}.json` с `{"chat_id": 123}`
     - Отправить пользователю: "Задачу принял, ожидайте"
   - В `callback.py` (или модуль внутри `main.py`):
     - При получении вебхука от эмулятора: извлечь `prediction_id` и `status`
     - Прочитать `tasks/{prediction_id}.json` из S3, получить `chat_id`
     - Если `status == "succeeded"`: отправить фото через Telegram `sendPhoto` (URL из `output`)
     - Если `status == "failed"`: отправить сообщение об ошибке
     - (Опционально) Удалить `tasks/{prediction_id}.json`

5. **Настройка ngrok для локальной разработки**

   - Инструкция по установке и запуску `ngrok http 8000`
   - Обновление `BASE_URL` в `.env` с URL от ngrok
   - Настройка Telegram webhook: `https://api.telegram.org/bot{TOKEN}/setWebhook?url={BASE_URL}/webhook/telegram`
   
   **Зачем нужен ngrok?**
   
   Telegram Bot API и Replicate API отправляют webhook-и на ваш сервер по HTTPS. Локальный сервер (`localhost:8000`) недоступен из интернета. Ngrok создает публичный HTTPS-туннель к локальному серверу, позволяя принимать webhook-и от внешних сервисов во время локальной разработки.

6. **Работа с S3 (boto3)**

   - Настроить клиент boto3 с `endpoint_url=http://minio:9000` (или `http://localhost:9000` для локальных вызовов)
   - Реализовать функции: `upload_to_s3()`, `download_from_s3()`, `generate_presigned_url()`, `save_task_state()`, `load_task_state()`

## Файлы

- `docker-compose.yml`
- `main.py` (FastAPI приложение)
- `mock_replicate.py` (эмулятор Replicate)
- `s3_client.py` (обертка для boto3)
- `.env` (обновленный с S3 настройками и BASE_URL)
- `requirements.txt` (обновленный: `fastapi`, `uvicorn`, `boto3`, `python-telegram-bot`)

## Тестирование

- Запуск `docker-compose up`
- Проверка MinIO консоли (localhost:9001)
- Отправка фото боту и отслеживание потока: фото → S3 → эмулятор → вебхук → результат
