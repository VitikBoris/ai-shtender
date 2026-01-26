# 7. Локальная разработка

## Концепция

Вместо Cloud Functions — **FastAPI** (вебхуки). Для S3 можно использовать:
- **Yandex Object Storage** (рекомендуется, начиная с feature-2.5) — публичный доступ к presigned URL
- **MinIO** (эмулятор, для ранних этапов разработки) — требует настройки туннеля для presigned URL

> **Гайды по установке:** См. [docs/setup/](../docs/setup/) для инструкций по установке Docker, MinIO, ngrok и YC CLI.

## Docker Compose

```yaml
services:
  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"

  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - minio
```

## Структура кода проекта

Единая структура для локальной разработки и Yandex Cloud Functions. Общая логика в `src/`, точки входа для YC — в `yc_functions/`.

```
ai-shtender/
├── src/
│   ├── app.py                     # создание FastAPI, подключение роутов
│   ├── config.py                  # чтение env + дефолты + валидация
│   ├── handlers/
│   │   ├── telegram_webhook.py    # POST /webhook/telegram
│   │   └── replicate_webhook.py   # POST /webhook/replicate
│   ├── services/
│   │   ├── s3_storage.py          # put/get, presign, json state
│   │   ├── telegram_api.py        # sendMessage/sendPhoto/getFile
│   │   └── replicate_api.py       # create_prediction, parse webhook
│   ├── domain/
│   │   ├── models.py              # TaskState, enums статусов/режимов
│   │   └── logic.py               # бизнес-логика (orchestration)
│   └── utils/
│       ├── http.py                # retry/backoff, timeouts
│       └── images.py              # mime/size checks, выбор лучшего photo_size
├── yc_functions/
│   ├── handler/main.py            # entrypoint для fn-handler → вызывает src/domain
│   └── callback/main.py           # entrypoint для fn-callback → вызывает src/domain
├── requirements.txt
├── .env
├── docker-compose.yml
└── tests/
    ├── test_logic.py
    └── test_handlers.py
```

- `src/domain/logic.py` — оркестрация шагов (что делать).
- `handlers/*` — приём HTTP и возврат ответа.
- `services/*` — интеграции (S3, Telegram, Replicate).
- `yc_functions/*` — тонкие адаптеры под формат Yandex Cloud.

## Этапы

### 1. Туннель (ngrok)

`ngrok http 8000` → `BASE_URL` в `.env`.

### 2. S3-as-DB с Yandex Object Storage (рекомендуется)

- Настроить YC CLI (см. [docs/setup/yc-cli-setup.md](../docs/setup/yc-cli-setup.md))
- Создать бакет через CLI или PowerShell скрипт (см. [feature-2.5-yandex-s3.md](../../features/feature-2.5-yandex-s3.md))
- `endpoint_url=https://storage.yandexcloud.net` в `.env`
- Запись: `s3.put_object(..., Key=f"tasks/{prediction_id}.json", Body=json.dumps(state))`
- Чтение: `s3.get_object(..., Key=f"tasks/{prediction_id}.json")`
- Presigned URL доступен из интернета автоматически

### 2.1. S3-as-DB с MinIO (альтернатива)

- `endpoint_url` из `.env` (для MinIO: `http://minio:9000`).
- Запись: `s3.put_object(..., Key=f"tasks/{prediction_id}.json", Body=json.dumps(state))`
- Чтение: `s3.get_object(..., Key=f"tasks/{prediction_id}.json")`

### 3. Фото для Replicate

**С Yandex Object Storage:** Presigned URL доступен из интернета автоматически, дополнительная настройка не требуется.

**С MinIO:** Для Presigned URL MinIO должен быть доступен снаружи (требуется ngrok для MinIO). Упрощение: можно временно отдавать Replicate прямую ссылку (например, ImgBB) вместо S3.

## План по шагам

**Вариант A: С Yandex Object Storage (рекомендуется)**

1. Установить и настроить YC CLI (см. [docs/setup/yc-cli-setup.md](../docs/setup/yc-cli-setup.md))
2. Создать бакет через CLI или PowerShell скрипт (см. [feature-2.5-yandex-s3.md](../../features/feature-2.5-yandex-s3.md))
3. Настроить `.env` с параметрами Yandex Object Storage
4. **`/webhook/telegram`:** приём сообщения, загрузка в S3, запрос в Replicate с `webhook: BASE_URL/webhook/replicate`
5. **`/webhook/replicate`:** приём, чтение `tasks/{prediction_id}.json`, ответ в Telegram
6. Тест: отправить фото боту, смотреть логи FastAPI и объекты в S3

**Вариант B: С MinIO (для ранних этапов)**

1. `docker-compose up minio` → создать бакет `ai-shtender-bucket` в `localhost:9001`
2. **`/webhook/telegram`:** приём сообщения, загрузка в MinIO, запрос в Replicate с `webhook: BASE_URL/webhook/replicate`
3. **`/webhook/replicate`:** приём, чтение `tasks/{prediction_id}.json`, ответ в Telegram
4. Тест: отправить фото боту, смотреть логи FastAPI и объекты в MinIO
