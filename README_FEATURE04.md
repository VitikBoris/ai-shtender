# Feature 04: Интеграция с Yandex Cloud

Этот документ описывает деплой приложения в **Yandex Cloud**: Cloud Functions (Telegram и Replicate webhooks), API Gateway (публичный HTTPS URL), Object Storage (S3). Деплой выполняется **скриптами PowerShell** и **YC CLI** (идемпотентно: create-or-update).

## Что поднимается в Yandex Cloud

- **2 Cloud Functions**: `fn-handler` (Telegram webhook), `fn-callback` (Replicate webhook)
- **1 API Gateway**: публичный HTTPS URL, маршруты `POST /webhook/telegram` и `POST /webhook/replicate`
- **IAM**: сервисный аккаунт с ролями `storage.editor`, `serverless.functions.invoker`
- **Object Storage**: бакет (создаётся отдельно, см. feature 2.5)

## Предварительные требования

- **YC CLI** установлен и настроен (`yc init`). См. [docs/setup/yc-cli-setup.md](docs/setup/yc-cli-setup.md)
- Выполнен **пункт 2.5**: Yandex Object Storage (бакет создан, ключи доступа есть). См. [features/feature-2.5-yandex-s3.md](features/feature-2.5-yandex-s3.md)
- Есть **токены**: Telegram Bot, Replicate API, ключи S3 (Access Key ID / Secret Access Key)

## Конфигурация

Скрипты читают настройки из двух файлов в `scripts/powershell/` (оба в `.gitignore`):

### 1. `yc.env` (несекретное)

Скопируйте шаблон и заполните:

```powershell
cd scripts\powershell
Copy-Item yc.env.example yc.env
# Отредактируйте yc.env
```

Пример содержимого:

```env
YC_FOLDER_ID=b1g...
YC_BUCKET_NAME=ai-shtender-bucket
YC_SERVICE_ACCOUNT_NAME=ai-shtender-sa
YC_FUNCTION_TELEGRAM_NAME=fn-handler
YC_FUNCTION_REPLICATE_NAME=fn-callback
YC_APIGW_NAME=ai-shtender-gw
YC_RUNTIME=python311
```

- **YC_FOLDER_ID** — ID каталога в Yandex Cloud (`yc resource-manager folder list`)
- **YC_BUCKET_NAME** — имя бакета Object Storage (тот же, что в feature 2.5)
- Остальные поля можно оставить по умолчанию

### 2. `yc.secrets.env` (секреты)

Скопируйте шаблон и заполните **реальными** значениями:

```powershell
Copy-Item yc.secrets.env.example yc.secrets.env
# Отредактируйте yc.secrets.env (токены и ключи S3)
```

Пример:

```env
TG_BOT_TOKEN=123456:ABC...
REPLICATE_API_TOKEN=r8_...
REPLICATE_MODEL_VERSION=...   # version id модели в Replicate
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

**Важно:** файл `yc.secrets.env` не коммитить в git.

## Порядок деплоя

Выполняйте команды из каталога `scripts\powershell`:

### Шаг 1. IAM (сервисный аккаунт и роли)

```powershell
.\init-yc-iam.ps1
```

Создаёт сервисный аккаунт (если нет) и назначает роли на каталог: `storage.editor`, `serverless.functions.invoker`. Опционально: `-GrantEditor` для роли `editor`.

### Шаг 2. Object Storage (если бакет ещё не создан)

Если бакет из feature 2.5 уже есть — шаг можно пропустить.

```powershell
.\init-yandex-s3.ps1
```

Использует `YC_FOLDER_ID` и `YC_BUCKET_NAME` из `yc.env`. Создаёт бакет и применяет lifecycle (удаление `tasks/` старше 1 дня и т.п.).

### Шаг 3. Деплой Cloud Functions

```powershell
.\deploy-yc-functions.ps1
```

- Собирает ZIP (код `src/`, `handler.py`, `callback.py`, `requirements.functions.txt`)
- Создаёт или обновляет функции `fn-handler` и `fn-callback`
- Прокидывает переменные окружения из `yc.env` и `yc.secrets.env`

На первом прогоне `BASE_URL` у функций пустой — его зададим после создания API Gateway.

### Шаг 4. Деплой API Gateway

```powershell
.\deploy-yc-apigw.ps1
```

- Подставляет в `openapi.yaml` ID функций и сервисного аккаунта
- Создаёт или обновляет API Gateway
- В конце выводит **публичный URL** (например `https://xxx.apigw.yandexcloud.net`)

**Сохраните этот URL** — это ваш `BASE_URL`.

### Шаг 5. Обновить BASE_URL у функций

```powershell
.\deploy-yc-functions.ps1 -BaseUrl "https://<ваш-домен-api-gateway>"
```

Подставьте домен из шага 4. Так Replicate будет слать webhook на правильный URL.

### Шаг 6. Установить Telegram webhook

```powershell
.\set-telegram-webhook.ps1 -BaseUrl "https://<ваш-домен-api-gateway>"
```

Либо без `-BaseUrl` — скрипт возьмёт домен API Gateway из YC по имени `YC_APIGW_NAME`.

После этого Telegram будет отправлять обновления на `https://<домен>/webhook/telegram`.

### Шаг 7. Smoke-тест (опционально)

```powershell
.\smoke-test.ps1 -BaseUrl "https://<ваш-домен-api-gateway>"
```

Проверяет, что `POST /webhook/telegram` и `POST /webhook/replicate` отвечают (без полноценного E2E).

## Проверка работы (E2E)

1. Отправьте боту в Telegram фото.
2. В консоли Yandex Cloud откройте **Cloud Functions** → логи функции `fn-handler`: должны быть загрузка в S3, создание prediction в Replicate.
3. В бакете Object Storage проверьте появление ключей `images/input/...` и `tasks/<prediction_id>.json`.
4. После завершения обработки Replicate вызовет `fn-callback`; бот должен прислать результат пользователю.
5. Логи `fn-callback` можно смотреть в Cloud Logging.

## Типичные проблемы

| Проблема | Что проверить |
|----------|----------------|
| Replicate не вызывает webhook | `BASE_URL` в env функций должен быть URL API Gateway (HTTPS). После шага 5 перезапустите шаг 3 с `-BaseUrl`. |
| Telegram не присылает обновления | Выполнен ли шаг 6 (`set-telegram-webhook.ps1`)? В ответе `getWebhookInfo` должен быть ваш URL. |
| Ошибка доступа к S3 в функции | У сервисного аккаунта есть роль `storage.editor`? Ключи в `yc.secrets.env` совпадают с ключами бакета? |
| PermissionDenied при создании функции/API Gateway | Выполните `yc init` (актуальный OAuth). У вашего пользователя должна быть роль `editor` (или выше) на каталог. |
| Функция не находит модуль `src` | Деплой собирает ZIP с папкой `src/` и `handler.py`/`callback.py` в корне архива. Не меняйте структуру без правки `deploy-yc-functions.ps1`. |

## Файлы пункта 4

| Файл | Назначение |
|------|------------|
| `handler.py` | Entrypoint Cloud Function для Telegram webhook |
| `callback.py` | Entrypoint Cloud Function для Replicate webhook |
| `openapi.yaml` | Спецификация API Gateway (плейсхолдеры подставляются скриптом) |
| `requirements.functions.txt` | Зависимости для Cloud Functions (без FastAPI/uvicorn) |
| `scripts/powershell/init-yc-iam.ps1` | IAM: сервисный аккаунт и роли |
| `scripts/powershell/deploy-yc-functions.ps1` | Сборка ZIP и деплой двух функций |
| `scripts/powershell/deploy-yc-apigw.ps1` | Деплой API Gateway из openapi.yaml |
| `scripts/powershell/set-telegram-webhook.ps1` | Установка webhook в Telegram |
| `scripts/powershell/smoke-test.ps1` | Проверка доступности эндпоинтов |

Подробнее про скрипты: [scripts/powershell/README.md](scripts/powershell/README.md).

## Связанные документы

- [features/feature-04-yandex-cloud.md](features/feature-04-yandex-cloud.md) — описание задач пункта 4
- [features/feature-2.5-yandex-s3.md](features/feature-2.5-yandex-s3.md) — Object Storage
- [docs/setup/yc-cli-setup.md](docs/setup/yc-cli-setup.md) — установка и настройка YC CLI
