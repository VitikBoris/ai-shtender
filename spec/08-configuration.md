# 8. Конфигурация

Конфигурация покрывает:

- Telegram Bot API;
- Replicate API и модель/версия;
- S3 (Yandex Object Storage / MinIO);
- Base URL для вебхуков;
- режимы и лимиты.

---

## 8.1. Обязательные переменные

### Telegram

| Переменная | Назначение |
|------------|------------|
| `TG_BOT_TOKEN` | Токен бота |

### Replicate

| Переменная | Назначение |
|------------|------------|
| `REPLICATE_API_TOKEN` | Токен API |
| `REPLICATE_MODEL` | Модель, напр. `owner/model` |
| `REPLICATE_VERSION` | Версия модели (хэш/идентификатор) |
| `REPLICATE_WEBHOOK_EVENTS` | По умолчанию `completed` (или список) |

### Webhook

| Переменная | Назначение |
|------------|------------|
| `BASE_URL` | Публичный базовый URL (ngrok локально, API Gateway в проде) |
| `REPLICATE_WEBHOOK_SECRET` | (Рекомендуется) Секрет для проверки входящих вебхуков Replicate |

### S3

| Переменная | Назначение |
|------------|------------|
| `S3_BUCKET` | Имя бакета |
| `S3_ENDPOINT_URL` | `https://storage.yandexcloud.net` (prod/Yandex Object Storage) или `http://minio:9000` (local MinIO) |
| `AWS_ACCESS_KEY_ID` | Ключ доступа (Access Key ID для Yandex Object Storage или minioadmin для MinIO) |
| `AWS_SECRET_ACCESS_KEY` | Секрет (Secret Access Key для Yandex Object Storage или minioadmin для MinIO) |

---

## 8.2. Рекомендуемые переменные

### S3 / MinIO

| Переменная | Назначение | Пример |
|------------|------------|--------|
| `S3_REGION` | Регион (если нужен) | пусто или `ru-central1` |
| `S3_FORCE_PATH_STYLE` | `1` для MinIO | `1` |
| `S3_USE_SSL` | HTTPS для S3 | `0` (MinIO), `1` (YC) |
| `S3_PRESIGN_EXPIRES_SECONDS` | TTL presigned URL | `3600` |

### Лимиты

| Переменная | Назначение | Пример |
|------------|------------|--------|
| `MAX_IMAGE_MB` | Макс. размер фото (MB) | `10` |
| `ALLOWED_IMAGE_MIME` | Разрешённые MIME | `image/jpeg,image/png` |

### Поведение

| Переменная | Назначение | Пример |
|------------|------------|--------|
| `DEFAULT_MODE` | Режим по умолчанию | `process_photo` |
| `LOG_LEVEL` | Уровень логов | `INFO` |

---

## 8.3. Yandex Cloud (Env Vars)

Те же переменные, значения для prod:

- `S3_ENDPOINT_URL=https://storage.yandexcloud.net`
- `BASE_URL` — URL API Gateway (или домен перед ним)
- Секреты — через Lockbox или env при деплое

---

## 8.4. Локально (.env)

### Вариант A: С Yandex Object Storage (рекомендуется)

```env
TG_BOT_TOKEN=...

REPLICATE_API_TOKEN=...
REPLICATE_MODEL=owner/model
REPLICATE_VERSION=model_version_hash
REPLICATE_WEBHOOK_SECRET=change_me

S3_BUCKET=ai-shtender-bucket
S3_ENDPOINT_URL=https://storage.yandexcloud.net
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
S3_FORCE_PATH_STYLE=0
S3_USE_SSL=1
S3_PRESIGN_EXPIRES_SECONDS=3600

BASE_URL=https://your-id.ngrok-free.app

DEFAULT_MODE=process_photo
MAX_IMAGE_MB=10
ALLOWED_IMAGE_MIME=image/jpeg,image/png
LOG_LEVEL=INFO
```

### Вариант B: С MinIO (для ранних этапов)

```env
TG_BOT_TOKEN=...

REPLICATE_API_TOKEN=...
REPLICATE_MODEL=owner/model
REPLICATE_VERSION=model_version_hash
REPLICATE_WEBHOOK_SECRET=change_me

S3_BUCKET=ai-shtender-bucket
S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_FORCE_PATH_STYLE=1
S3_USE_SSL=0
S3_PRESIGN_EXPIRES_SECONDS=3600

BASE_URL=https://your-id.ngrok-free.app

DEFAULT_MODE=process_photo
MAX_IMAGE_MB=10
ALLOWED_IMAGE_MIME=image/jpeg,image/png
LOG_LEVEL=INFO
```

---

## 8.5. Примечания

- Для **MinIO** обычно нужен `S3_FORCE_PATH_STYLE=1` (иначе возможны ошибки адресации бакета).
- Для **Yandex Object Storage** используйте `S3_FORCE_PATH_STYLE=0` и `S3_USE_SSL=1`.
- Для **boto3** указывать `endpoint_url=os.getenv('S3_ENDPOINT_URL')` при создании клиента.
- Таймауты HTTP (Telegram, Replicate) задавать явно в коде/конфиге.
- Секреты не коммитить: `.env` в `.gitignore`; в prod — Lockbox или аналог.
- Начиная с feature-2.5 рекомендуется использовать Yandex Object Storage для локальной разработки (см. [feature-2.5-yandex-s3.md](../../features/feature-2.5-yandex-s3.md)).
