# Feature 02: Mock Replicate Integration

Реализация локального эмулятора Replicate API и интеграция с ботом через архитектуру S3-as-DB.

## Структура проекта

```
ai-shtender/
├── src/
│   ├── app.py                     # FastAPI приложение
│   ├── config.py                  # Конфигурация
│   ├── handlers/
│   │   ├── telegram_webhook.py    # POST /webhook/telegram
│   │   └── replicate_webhook.py   # POST /webhook/replicate
│   ├── services/
│   │   ├── s3_storage.py          # Работа с MinIO/S3
│   │   ├── telegram_api.py       # Telegram Bot API
│   │   └── replicate_api.py       # Replicate API
│   ├── domain/
│   │   ├── models.py              # Модели данных
│   │   └── logic.py               # Бизнес-логика
│   └── utils/
│       ├── http.py                # HTTP утилиты
│       └── images.py              # Утилиты для изображений
├── mock_replicate.py              # Эмулятор Replicate API
├── docker-compose.yml             # Docker Compose конфигурация
├── Dockerfile                     # Dockerfile для приложения
├── requirements.txt               # Зависимости Python
└── scripts/
    └── init_minio.py              # Скрипт инициализации MinIO
```

## Предварительные требования

- Docker и Docker Compose ([гайд по установке](docs/setup/docker-compose-install.md))
- Python 3.9+ (для локального запуска)
- ngrok (для туннелирования) - [гайд по настройке](docs/setup/ngrok-setup.md)
- Telegram Bot Token (от @BotFather)

## Быстрый старт

### 1. Настройка переменных окружения

Скопировать `.env.example` в `.env` и заполнить:

```bash
# Обязательные
TG_BOT_TOKEN=your_telegram_bot_token
S3_BUCKET=my-bot-bucket
S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
BASE_URL=https://your-id.ngrok-free.app

# Опциональные
MOCK_REPLICATE_URL=http://mock-replicate:8001
```

### 2. Запуск через Docker Compose

```bash
# Запустить все сервисы
docker-compose up -d

# Просмотр логов
docker-compose logs -f app
```

### 3. Настройка ngrok

См. [docs/setup/ngrok-setup.md](docs/setup/ngrok-setup.md)

1. Запустить ngrok: `ngrok http 8000`
2. Скопировать HTTPS URL в `BASE_URL` в `.env`
3. Настроить Telegram webhook

### 4. Инициализация MinIO

Бакет создается автоматически при первом запуске, или вручную:

```bash
python scripts/init_minio.py
```

Консоль MinIO: http://localhost:9001 (minioadmin/minioadmin)

## Запуск локально (без Docker)

### 1. Запустить MinIO

```bash
docker-compose up minio
```

### 2. Запустить Mock Replicate

```bash
uvicorn mock_replicate:app --host 0.0.0.0 --port 8001
```

### 3. Запустить FastAPI приложение

```bash
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

## Тестирование

1. Отправить фото боту в Telegram
2. Проверить логи:
   - Фото загружено в S3
   - Prediction создан в Mock Replicate
   - Вебхук получен и обработан
   - Результат отправлен пользователю
3. Проверить MinIO консоль:
   - `images/input/` - исходные фото
   - `tasks/` - JSON состояния задач

## API Endpoints

### FastAPI приложение (порт 8000)

- `POST /` - вебхук от Telegram (корневой путь, для совместимости)
- `POST /webhook/telegram` - вебхук от Telegram (явный путь)
- `POST /webhook/replicate` - вебхук от Replicate
- `GET /health` - проверка работоспособности

**Примечание:** Оба пути (`/` и `/webhook/telegram`) обрабатывают Telegram webhook одинаково. Можно использовать любой из них при настройке webhook в Telegram.

### Mock Replicate (порт 8001)

- `POST /v1/predictions` - создать prediction
- `GET /v1/predictions/{id}` - получить статус prediction
- `GET /health` - проверка работоспособности

## Архитектура

```
Пользователь → Telegram → FastAPI (/webhook/telegram)
                              ↓
                          MinIO (S3)
                              ↓
                      Mock Replicate
                              ↓
                      FastAPI (/webhook/replicate)
                              ↓
                          Telegram → Пользователь
```

## Документация

- [Настройка MinIO](docs/setup/minio-setup.md)
- [Настройка ngrok](docs/setup/ngrok-setup.md)
- [Установка Docker и Docker Compose](docs/setup/docker-compose-install.md)
- [Спецификация](spec/)

## Примечания

- Mock Replicate эмулирует обработку с задержкой 2-5 секунд
- Для presigned URL MinIO должен быть доступен извне (через ngrok)
- Вебхуки идемпотентны - повторные вызовы не создают дубликаты
- Все логи содержат `prediction_id` и `chat_id` для отладки
