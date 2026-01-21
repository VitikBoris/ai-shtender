# 9. Промпты для ИИ-разработчика

## Локальный FastAPI

> Напиши локальное приложение на **FastAPI** с двумя роутами: `/webhook/telegram` и `/webhook/replicate`. Используй **boto3** для хранения состояния в S3 (локальный MinIO) по пути `tasks/{prediction_id}.json`.
>
> Логика:
> 1. При получении фото от TG: скачать, положить в S3, отправить запрос в Replicate.
> 2. При вебхуке от Replicate: взять из S3 `tasks/{prediction_id}.json`, прочитать `chat_id`, отправить результат в Telegram.
>
> `endpoint_url` для S3 брать из конфига (совместимость с MinIO).

---

## Yandex Cloud Functions

> Напиши код на Python для **Yandex Cloud Functions** — Telegram-бот для обработки фото через Replicate.
>
> - **boto3** для Yandex Object Storage (S3). Без БД: состояние в `tasks/{prediction_id}.json` с `{"chat_id": 123}`.
> - **handler.py:** скачать фото → S3 → Presigned URL → Replicate с webhook URL → сохранить стейт в S3.
> - **callback.py:** прочитать стейт из S3 по `prediction_id` → отправить результат в Telegram.
> - **requests** для HTTP. Обработка ошибок и логирование.
