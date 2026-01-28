# AI Shtender - Telegram бот для обработки изображений

Проект представляет собой Telegram-бота для обработки изображений с использованием архитектуры S3-as-DB и интеграцией с Replicate API (или его эмулятором).

## Содержание

- [Пункт 1: Локальный бот с базовыми командами](#пункт-1-локальный-бот-с-базовыми-командами)
- [Feature 02: Mock Replicate Integration](#feature-02-mock-replicate-integration)

---

# Пункт 1: Локальный бот с базовыми командами

## Установка и настройка

### 1. Установите зависимости

```bash
pip install -r requirements.txt
```

### 2. Создайте файл `.env`

Создайте файл `.env` в корне проекта со следующим содержимым:

```env
TG_BOT_TOKEN=ваш_токен_бота
```

**Как получить токен:**
1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен в файл `.env`

### 3. Запустите бота

```bash
python bot_local.py
```

После запуска вы увидите сообщение: `Бот запущен и ожидает сообщений...`

## Тестирование

1. Найдите вашего бота в Telegram по имени, которое вы указали при создании
2. Отправьте команду `/start` - бот ответит приветственным сообщением
3. Отправьте боту любое фото - он вернет то же фото обратно

## Структура файлов

- `bot_local.py` - основной файл бота
- `requirements.txt` - зависимости Python
- `.env` - переменные окружения (токены) - **не коммитится в git**
- `.gitignore` - исключения для git

## Что реализовано

✅ Команда `/start` с приветственным сообщением  
✅ Обработчик фото, который возвращает то же фото обратно  
✅ Базовая обработка ошибок и логирование  
✅ Использование переменных окружения для токена

---

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
│   │   ├── telegram_api.py        # Telegram Bot API
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

### Шаг 1: Настройка .env

Создайте файл `.env` в корне проекта:

```env
TG_BOT_TOKEN=your_telegram_bot_token_here
S3_BUCKET=ai-shtender-bucket
S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_FORCE_PATH_STYLE=1
S3_USE_SSL=0
S3_PRESIGN_EXPIRES_SECONDS=3600
BASE_URL=https://your-id.ngrok-free.app
MOCK_REPLICATE_URL=http://mock-replicate:8001
REPLICATE_API_TOKEN=
REPLICATE_MODEL_VERSION=
MAX_IMAGE_MB=10
ALLOWED_IMAGE_MIME=image/jpeg,image/png
DEFAULT_MODE=process_photo
LOG_LEVEL=INFO
```

#### Режимы работы Replicate (mock vs real)

- **Mock (локальный эмулятор)**:
  - Установить `MOCK_REPLICATE_URL=http://mock-replicate:8001`
  - Запуск через профиль compose:
    - `docker compose --profile mock up -d`
    - или `docker-compose --profile mock up -d`
- **Real (настоящий Replicate API)**:
  - Убрать/не задавать `MOCK_REPLICATE_URL`
  - Задать:
    - `REPLICATE_API_TOKEN` — токен Replicate
    - `REPLICATE_MODEL_VERSION` — **version id** модели в Replicate (именно version, не имя модели)
  - Запуск:
    - `docker compose up -d`
    - или `docker-compose up -d`

Важно для real режима:
- `BASE_URL` должен быть публичным HTTPS адресом (куда Replicate сможет доставить вебхук на `/webhook/replicate`).
- Presigned URL на входное изображение из S3 должен быть доступен из интернета (для этого в проекте используется Yandex Object Storage — см. `features/feature-2.5-yandex-s3.md`).

Проверки (быстрые sanity checks):
- **Проверка, что вебхук доступен снаружи**: откройте в браузере `BASE_URL/health` (должен вернуть `{"status":"ok",...}`).
- **Проверка presigned URL**: сгенерируйте presigned URL (приложение делает это автоматически при получении фото) и убедитесь, что он открывается в браузере/`curl` без VPN и без доступа к вашей локальной сети.

### Шаг 2: Запуск сервисов

```bash
# Запустить все сервисы
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```

Сервисы:
- MinIO: http://localhost:9001 (minioadmin/minioadmin)
- FastAPI: http://localhost:8000
- Mock Replicate: http://localhost:8001 (только если запускали с `--profile mock`)

### Шаг 3: Настройка ngrok

1. В отдельном терминале:
   ```bash
   ngrok http 8000
   ```

2. Скопировать HTTPS URL (например: `https://abc123.ngrok-free.app`)

3. Обновить `.env`:
   ```env
   BASE_URL=https://abc123.ngrok-free.app
   ```

4. Перезапустить app:
   ```bash
   docker-compose restart app
   ```

Подробнее: [docs/setup/ngrok-setup.md](docs/setup/ngrok-setup.md)

### Шаг 4: Настройка Telegram Webhook

**Вариант 1: Корневой путь (рекомендуется)**
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://abc123.ngrok-free.app"
```

**Вариант 2: С указанием пути**
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://abc123.ngrok-free.app/webhook/telegram"
```

Оба варианта работают. Приложение поддерживает оба пути.

### Шаг 5: Инициализация MinIO

Бакет создается автоматически при первом запуске, или вручную:

```bash
python scripts/init_minio.py
```

Консоль MinIO: http://localhost:9001 (minioadmin/minioadmin)

### Шаг 6: Тестирование

1. Откройте Telegram и найдите вашего бота
2. Отправьте команду `/start`
3. Отправьте фото
4. Проверьте логи: `docker-compose logs -f app`
5. Проверьте MinIO консоль: http://localhost:9001

Проверьте логи:
- Фото загружено в S3
- Prediction создан в Mock Replicate
- Вебхук получен и обработан
- Результат отправлен пользователю

Проверьте MinIO консоль:
- `images/input/` - исходные фото
- `tasks/` - JSON состояния задач

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

## Перезапуск бота без остановки всего Docker

Если нужно перезапустить только бота (сервис `app`), не останавливая MinIO и другие сервисы:

### Способ 1: Через Docker Compose (рекомендуется)

```bash
# Перезапустить только сервис app
docker-compose restart app

# Или с просмотром логов
docker-compose restart app && docker-compose logs -f app
```

### Способ 2: Через Docker напрямую

```bash
# Перезапустить контейнер по имени
docker restart telegram-bot-app

# Просмотр логов после перезапуска
docker logs -f telegram-bot-app
```

### Когда использовать перезапуск

Перезапуск бота полезен в следующих случаях:
- После изменения переменных окружения в `.env` файле
- После обновления кода (если auto-reload не сработал)
- При необходимости обновить конфигурацию без остановки всех сервисов
- После изменения webhook URL в Telegram

### Проверка статуса сервисов

```bash
# Проверить статус всех сервисов
docker-compose ps

# Проверить статус только бота
docker-compose ps app

# Проверить логи бота
docker-compose logs app
```

### Автоматическая перезагрузка

При разработке бот автоматически перезагружается при изменении файлов в папке `src/` благодаря флагу `--reload` в docker-compose.yml. В этом случае ручной перезапуск не требуется.

## Остановка

```bash
docker-compose down
```

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

## Устранение проблем

### MinIO не доступен

Проверьте, что MinIO запущен:
```bash
docker-compose ps minio
```

### Webhook не работает

1. Проверьте, что ngrok запущен и URL правильный
2. Проверьте webhook: `curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"`
3. Проверьте логи: `docker-compose logs app`

### Ошибки при загрузке в S3

1. Проверьте, что бакет создан: http://localhost:9001
2. Проверьте переменные окружения в `.env`
3. Запустите скрипт инициализации: `python scripts/init_minio.py`

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
