# Feature 03: Real Replicate Integration

Этот документ описывает запуск и настройку **реального Replicate API** вместо локального эмулятора (Mock Replicate).

## Что изменилось по сравнению с Feature 02

- В режиме **real** приложение отправляет запросы в `https://api.replicate.com/v1/predictions`
- Для real режима нужны:
  - `REPLICATE_API_TOKEN`
  - `REPLICATE_MODEL_VERSION` (**version id** модели в Replicate)
- `MOCK_REPLICATE_URL` должен быть **не задан** (или пустой), чтобы включился real режим
- `mock-replicate` в `docker-compose.yml` теперь **опциональный** (запускается только с профилем `mock`)

## Предварительные требования

- Выполнен пункт 2.5: Yandex Object Storage (presigned URL должен быть доступен из интернета) — см. `features/feature-2.5-yandex-s3.md`
- `BASE_URL` должен быть публичным **HTTPS** адресом, доступным из интернета (для вебхуков Telegram и Replicate)
  - Для локальной разработки используйте ngrok — см. `docs/setup/ngrok-setup.md`

## Переменные окружения (.env)

Минимальный набор для **real режима**:

```env
# Telegram
TG_BOT_TOKEN=...

# Webhook (публичный HTTPS URL)
BASE_URL=https://<your-domain-or-ngrok>

# S3 (рекомендуется Yandex Object Storage для real режима)
S3_ENDPOINT_URL=https://storage.yandexcloud.net
S3_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_FORCE_PATH_STYLE=false
S3_USE_SSL=true
S3_PRESIGN_EXPIRES_SECONDS=3600

# Replicate (real)
REPLICATE_API_TOKEN=...
REPLICATE_MODEL_VERSION=...

# ВАЖНО: для real режима переменная ниже должна быть пустой/отсутствовать
# MOCK_REPLICATE_URL=http://mock-replicate:8001
```

### Как получить `REPLICATE_API_TOKEN`

- Зарегистрируйтесь в Replicate и создайте API token.
- Сохраните токен в `.env` как `REPLICATE_API_TOKEN`.

### Как получить `REPLICATE_MODEL_VERSION`

В этом проекте в запросе используется поле `version` (см. `src/services/replicate_api.py`), поэтому нужен **ID версии модели**.

Примерная логика:
- Выберите модель (например `sczhou/codeformer`).
- Откройте страницу модели в Replicate и найдите **version id** (обычно это длинная строка-идентификатор версии).
- Вставьте её в `.env` как `REPLICATE_MODEL_VERSION`.

## Запуск

### Real режим (Replicate API)

```bash
docker compose up -d
```

Проверьте, что:
- `MOCK_REPLICATE_URL` **не задан**
- `REPLICATE_API_TOKEN` и `REPLICATE_MODEL_VERSION` заданы

### Mock режим (локальный эмулятор)

Если хотите запустить как в Feature 02:

```bash
docker compose --profile mock up -d
```

и в `.env`:

```env
MOCK_REPLICATE_URL=http://mock-replicate:8001
```

## Быстрые проверки (sanity checks)

### 1) Публичность вашего сервиса

Откройте в браузере:
- `BASE_URL/health`

Ожидаемый ответ: JSON со `status: ok`.

### 2) Доступность presigned URL из S3

Для real Replicate критично, чтобы ссылка на входное изображение была доступна из интернета.
Проверка:
- отправьте фото боту
- в логах найдите presigned URL (или временно залогируйте его)
- откройте URL в браузере/через `curl` с внешней машины/без доступа к вашей локальной сети

## Поток обработки (в двух словах)

1. Telegram присылает webhook на `/webhook/telegram`
2. Сервис загружает входное изображение в S3 и генерирует presigned URL
3. Сервис создаёт prediction в Replicate с `webhook=BASE_URL/webhook/replicate`
4. Replicate присылает `completed` webhook на `/webhook/replicate`
5. Сервис отправляет пользователю результат (URL из `output`)

## Типичные проблемы

- **Replicate не доставляет webhook**:
  - `BASE_URL` не публичный HTTPS или недоступен извне
  - неверный путь (должен быть `/webhook/replicate`)
- **Replicate не может скачать входное изображение**:
  - presigned URL недоступен из интернета (часто проблема с локальным MinIO без проброса наружу)
  - неверные S3 настройки (см. `features/feature-2.5-yandex-s3.md`)
- **401/403 от Replicate**:
  - неверный `REPLICATE_API_TOKEN`
- **429 от Replicate**:
  - rate limit — попробуйте позже
- **Ошибка “требуется указать модель/version”**:
  - не задан `REPLICATE_MODEL_VERSION` (нужен именно version id)

