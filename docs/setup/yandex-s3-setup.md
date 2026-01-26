# Настройка Yandex Object Storage

## Зачем нужен Yandex Object Storage?

Yandex Object Storage - это S3-совместимое хранилище, которое:
- Обеспечивает публичный доступ к presigned URL без необходимости в ngrok
- Близко к production-окружению (используется тот же Object Storage, что и в feature-04)
- Упрощает интеграцию с реальным Replicate API (feature-03)
- Поддерживает автоматическую очистку старых файлов через lifecycle policy

## Предварительные требования

1. Установленный и настроенный YC CLI (см. [yc-cli-setup.md](yc-cli-setup.md))
2. Аккаунт Yandex Cloud с доступом к Object Storage

## Шаг 1: Создание бакета

### Вариант A: Использовать PowerShell скрипт (Windows, рекомендуется)

```powershell
cd scripts\powershell
.\init-yandex-s3.ps1 -BucketName "ai-shtender-bucket" -FolderId "<your-folder-id>"
```

Скрипт автоматически:
- Создаст бакет в Yandex Object Storage
- Применит lifecycle policy из файла `scripts/powershell/lifecycle.json` (если файл существует)

### Вариант B: Создать бакет вручную через CLI

1. Получить ID каталога:
   ```bash
   yc resource-manager folder list
   ```

2. Создать бакет:
   ```bash
   yc storage bucket create --name ai-shtender-bucket  --folder-id <folder-id>
   ```
   
   Где `ai-shtender-bucket` - имя бакета (должно быть уникальным глобально), `<your-folder-id>` - ID каталога.

## Шаг 2: Настройка Lifecycle Policy

Lifecycle policy автоматически удаляет старые файлы для экономии места и средств.

1. Убедитесь, что файл `scripts/powershell/lifecycle.json` существует (создан в feature-2.5)

2. Применить lifecycle policy:
   ```bash
   yc storage bucket update \
     --name ai-shtender-bucket \
     --lifecycle-rules-from-file scripts/powershell/lifecycle.json
   ```

Правила в `lifecycle.json`:
- `tasks/` - удалять файлы старше 1 дня
- `images/input/` - удалять файлы старше 14 дней
- `images/output/` - удалять файлы старше 14 дней

## Шаг 3: Создание сервисного аккаунта

Сервисный аккаунт нужен для доступа к бакету из приложения.

1. Создать сервисный аккаунт с ролью `storage.editor`:
   ```bash
   yc iam service-account create \
     --name bot-storage-sa \
     --folder-id <your-folder-id>
   ```

2. Назначить роль сервисному аккаунту:
   ```bash
   yc resource-manager folder add-access-binding <your-folder-id> \
     --role storage.editor \
     --subject serviceAccount:<service-account-id>
   ```

3. Создать статический ключ доступа:
   ```bash
   yc iam access-key create \
     --service-account-name bot-storage-sa
   ```

4. Сохранить Access Key ID и Secret Access Key в безопасном месте (понадобятся для `.env`)

## Шаг 4: Настройка конфигурации приложения

Обновить файл `.env` с настройками Yandex Object Storage:

```env
# S3 Configuration для Yandex Object Storage
S3_BUCKET=ai-shtender-bucket
S3_ENDPOINT_URL=https://storage.yandexcloud.net
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
S3_FORCE_PATH_STYLE=0
S3_USE_SSL=1
S3_PRESIGN_EXPIRES_SECONDS=3600
```

**Важно:** 
- `S3_FORCE_PATH_STYLE=0` для Yandex Object Storage (в отличие от MinIO, где используется `1`)
- `S3_USE_SSL=1` для использования HTTPS
- Не коммитьте файл `.env` с реальными ключами в репозиторий!

## Шаг 5: Проверка работы

1. Запустить приложение:
   ```bash
   docker-compose up app
   # или локально:
   uvicorn src.app:app --host 0.0.0.0 --port 8000
   ```

2. Проверить генерацию presigned URL:
   - URL должен иметь формат `https://storage.yandexcloud.net/bucket/key?...`
   - URL должен быть доступен из интернета (проверить через браузер или `curl`)

3. Протестировать загрузку и скачивание файлов через S3

4. Проверить сохранение и загрузку состояния задач (`tasks/{prediction_id}.json`)

## Структура папок в бакете

Бакет автоматически содержит следующие префиксы (папки):

- `images/input/` - исходные фото пользователей
- `images/output/` - результаты обработки (опционально)
- `tasks/` - JSON-файлы с состоянием задач

## Публичный доступ (опционально)

Для presigned URL публичный доступ не обязателен, так как presigned URL предоставляет временный доступ даже к приватным объектам.

Если все же нужно настроить публичный доступ на чтение (для тестирования):

```bash
yc storage bucket update \
  --name ai-shtender-bucket \
  --public-read
```

## Стоимость

- Yandex Object Storage: ~0.01₽ за GB в месяц
- Первые 10 GB бесплатно (в рамках бесплатного периода Yandex Cloud)
- Для тестирования и разработки расходы минимальны

## Устранение неполадок

### Ошибка при создании бакета

- Убедитесь, что имя бакета уникально глобально
- Проверьте, что у вас есть права на создание бакетов в каталоге
- Проверьте правильность `folder-id`

### Ошибка доступа к бакету

- Проверьте правильность Access Key ID и Secret Access Key
- Убедитесь, что сервисный аккаунт имеет роль `storage.editor`
- Проверьте, что ключи не истекли

### Presigned URL недоступен из интернета

- Убедитесь, что используется `S3_ENDPOINT_URL=https://storage.yandexcloud.net`
- Проверьте, что `S3_USE_SSL=1`
- Проверьте, что URL имеет правильный формат

## Дополнительные ресурсы

- [Документация Yandex Object Storage](https://yandex.cloud/en/docs/storage/)
- [YC CLI справочник по Object Storage](https://yandex.cloud/en/docs/cli/cli-ref/managed-services/storage/bucket/)
- [feature-2.5-yandex-s3.md](../../features/feature-2.5-yandex-s3.md)
