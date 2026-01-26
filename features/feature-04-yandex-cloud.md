# Пункт 4: Интеграция с Yandex Cloud

План: [feature-plan.md](feature-plan.md)

**Коммит:** не реализовано

## Цель

Перенести приложение на Yandex Cloud: Cloud Functions, API Gateway, Object Storage.

## Задачи

1. **Подготовка инфраструктуры Yandex Cloud**

   - Создать сервисный аккаунт с ролями: `storage.editor`, `serverless.functions.invoker`
   - Создать статический ключ доступа (Access Key ID и Secret Access Key)
   - Создать бакет Object Storage с именем (например, `ai-shtender-bucket`)
   - Настроить lifecycle policy для `tasks/` (удаление файлов старше 1 дня)
   - Создать Lockbox секрет для токенов (опционально, или использовать переменные окружения функций)

2. **Подготовка кода для Cloud Functions**

   - Разделить `main.py` на две функции:
     - `handler.py` → функция `fn-handler` (обработка Telegram webhook)
     - `callback.py` → функция `fn-callback` (обработка Replicate webhook)
   - Адаптировать код для формата Cloud Functions:
     - Точка входа: `def handler(event, context)`
     - Парсинг HTTP-запроса из `event`
     - Возврат HTTP-ответа в формате YC
   - Обновить S3 клиент: `endpoint_url=https://storage.yandexcloud.net`

3. **Создание API Gateway конфигурации**

   - Создать `openapi.yaml` (OpenAPI спецификация):
     - `POST /webhook/telegram` → интеграция с `fn-handler`
     - `POST /webhook/replicate` → интеграция с `fn-callback`
   - Настроить CORS при необходимости

4. **Деплой функций**

   - Создать `requirements.txt` для Cloud Functions (только необходимые зависимости)
   - Упаковать код в ZIP-архивы (или использовать YC CLI)
   - Создать функции через YC CLI или консоль:
     - `fn-handler`: runtime Python 3.9+, таймаут ~30 секунд, память 256MB
     - `fn-callback`: runtime Python 3.9+, таймаут ~30 секунд, память 256MB
   - Настроить переменные окружения функций:
     - `TG_BOT_TOKEN`
     - `REPLICATE_API_TOKEN`
     - `S3_BUCKET`
     - `AWS_ACCESS_KEY_ID`
     - `AWS_SECRET_ACCESS_KEY`
     - `S3_ENDPOINT_URL=https://storage.yandexcloud.net`

5. **Настройка API Gateway**

   - Развернуть API Gateway с использованием `openapi.yaml`
   - Получить публичный URL API Gateway
   - Обновить Telegram webhook: `https://api.telegram.org/bot{TOKEN}/setWebhook?url={API_GATEWAY_URL}/webhook/telegram`
   - Обновить webhook URL в коде `handler.py` для Replicate: `{API_GATEWAY_URL}/webhook/replicate`

6. **Тестирование в облаке**

   - Проверка работы эндпоинтов через API Gateway
   - Отправка фото боту и отслеживание через Cloud Logging
   - Проверка сохранения файлов в Object Storage
   - Проверка lifecycle policy (опционально, через искусственное старение файлов)

7. **Мониторинг и логирование**

   - Настройка Cloud Logging для функций
   - Мониторинг метрик функций (вызовы, ошибки, длительность)

## Файлы

- `handler.py` (адаптирован для Cloud Functions)
- `callback.py` (адаптирован для Cloud Functions)
- `openapi.yaml` (конфигурация API Gateway)
- `requirements.txt` (для Cloud Functions)
- `.yc/` (опционально: конфигурация YC CLI)

## Дополнительные материалы

- Инструкция по настройке Yandex Cloud (создание сервисного аккаунта, бакета, функций)
- Скрипты деплоя (опционально)
