# Пункт 3: Интеграция с реальным Replicate

План: [feature-plan.md](feature-plan.md)

**Коммит:** не реализовано

## Цель

Заменить локальный эмулятор на реальный Replicate API, сохранив архитектуру с S3-as-DB.

## Задачи

1. **Получение токена Replicate**

   - Регистрация на Replicate, получение `REPLICATE_API_TOKEN`
   - Добавление токена в `.env`

2. **Выбор модели Replicate**

   - Определить модель для обработки изображений (например, `sczhou/codeformer` для восстановления фото)
   - Документировать параметры модели в коде

3. **Обновление кода для работы с Replicate API**

   - В `handler.py`: заменить вызов эмулятора на реальный Replicate API
     - Использовать `requests.post()` к `https://api.replicate.com/v1/predictions`
     - Заголовки: `Authorization: Token {REPLICATE_API_TOKEN}`
     - Тело запроса:
       ```json
       {
         "version": "model_version_id",
         "input": {"image": presigned_url, ...},
         "webhook": "https://BASE_URL/webhook/replicate",
         "webhook_events_filter": ["completed"]
       }
       ```

   - `callback.py` остается без изменений (обрабатывает те же данные от Replicate)

4. **Обработка ошибок и edge cases**

   - Обработка таймаутов Replicate
   - Обработка ошибок API Replicate (401, 429, 500)
   - Логирование для отладки
   - Обработка случая, когда `tasks/{prediction_id}.json` не найден в S3 (редкий кейс)

5. **Обновление presigned URL для S3**

   - Убедиться, что presigned URL доступен из интернета (необходимо для Replicate)
   - Если используется локальный MinIO: настроить ngrok для MinIO или использовать публичный S3 для тестов

## Файлы

- `handler.py` (обновлен)
- `.env` (добавлен `REPLICATE_API_TOKEN`)
- `requirements.txt` (добавлен `replicate` опционально, или использовать `requests`)

## Тестирование

- Проверка работы с реальным Replicate
- Мониторинг вебхуков от Replicate
- Проверка сохранения/загрузки состояния в S3
