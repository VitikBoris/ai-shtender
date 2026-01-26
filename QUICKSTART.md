# Быстрый старт - Feature 02

## Предварительные требования

- Docker и Docker Compose ([гайд по установке](docs/setup/docker-compose-install.md))
- Python 3.9+ (для локального запуска)
- ngrok (для туннелирования) - [гайд по настройке](docs/setup/ngrok-setup.md)
- Telegram Bot Token (от @BotFather)

## Шаг 1: Настройка .env

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
MAX_IMAGE_MB=10
ALLOWED_IMAGE_MIME=image/jpeg,image/png
DEFAULT_MODE=process_photo
LOG_LEVEL=INFO
```

## Шаг 2: Запуск сервисов

```bash
# Запустить все сервисы
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```

Сервисы:
- MinIO: http://localhost:9001 (minioadmin/minioadmin)
- FastAPI: http://localhost:8000
- Mock Replicate: http://localhost:8001

## Шаг 3: Настройка ngrok

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

## Шаг 4: Настройка Telegram Webhook

**Вариант 1: Корневой путь (рекомендуется)**
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://abc123.ngrok-free.app"
```

**Вариант 2: С указанием пути**
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://abc123.ngrok-free.app/webhook/telegram"
```

Оба варианта работают. Приложение поддерживает оба пути.

## Шаг 5: Тестирование

1. Откройте Telegram и найдите вашего бота
2. Отправьте команду `/start`
3. Отправьте фото
4. Проверьте логи: `docker-compose logs -f app`
5. Проверьте MinIO консоль: http://localhost:9001

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
