# 7. Локальная разработка

## Концепция

Вместо Cloud Functions — **FastAPI** (вебхуки). Вместо Yandex Object Storage — **MinIO** (S3-совместимый).

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

### 2. S3-as-DB с MinIO

- `endpoint_url` из `.env` (для MinIO).
- Запись: `s3.put_object(..., Key=f"tasks/{prediction_id}.json", Body=json.dumps(state))`
- Чтение: `s3.get_object(..., Key=f"tasks/{prediction_id}.json")`

### 3. Фото для Replicate

Для Presigned URL MinIO должен быть доступен снаружи. Упрощение: можно временно отдавать Replicate прямую ссылку (например, ImgBB) вместо S3.

## План по шагам

1. `docker-compose up minio` → создать бакет `my-bot-bucket` в `localhost:9001`.
2. **`/webhook/telegram`:** приём сообщения, загрузка в MinIO, запрос в Replicate с `webhook: BASE_URL/webhook/replicate`.
3. **`/webhook/replicate`:** приём, чтение `tasks/{prediction_id}.json`, ответ в Telegram.
4. Тест: отправить фото боту, смотреть логи FastAPI и объекты в MinIO.
