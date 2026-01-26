# PowerShell скрипты

Эта папка содержит полезные PowerShell скрипты для работы с проектом.

## Скрипты

### install-yc-cli.ps1

Установка Yandex Cloud CLI на Windows.

**Использование:**
```powershell
.\install-yc-cli.ps1
```

**Описание:**
- Скачивает и запускает официальный скрипт установки YC CLI
- После установки необходимо перезапустить терминал или выполнить `refreshenv`
- Затем выполнить `yc init` для инициализации

### init-yandex-s3.ps1

Инициализация бакета Yandex Object Storage.

**Использование:**
```powershell
.\init-yandex-s3.ps1 -BucketName "ai-shtender-bucket" -FolderId "your-folder-id"
```

**Параметры:**
- `-BucketName` (обязательный) - имя бакета
- `-FolderId` (обязательный) - ID каталога в Yandex Cloud
- `-LifecycleConfigPath` (опциональный) - путь к файлу lifecycle.json (по умолчанию: `$PSScriptRoot\lifecycle.json`)

**Описание:**
- Создает бакет в Yandex Object Storage
- Применяет lifecycle policy из файла `lifecycle.json` в папке скрипта (если файл существует)
- Проверяет наличие YC CLI перед выполнением

**Пример:**
```powershell
# Получить ID каталога
yc resource-manager folder list

# Создать бакет
.\init-yandex-s3.ps1 -BucketName "ai-shtender-bucket" -FolderId "b1g2h3j4k5l6m7n8"
```

### check-env.ps1

Проверка переменных окружения, необходимых для работы проекта.

**Использование:**
```powershell
.\check-env.ps1
```

**Описание:**
- Проверяет наличие всех обязательных переменных окружения
- Показывает список найденных и отсутствующих переменных
- Скрывает значения токенов и ключей при выводе
- Возвращает код ошибки, если отсутствуют обязательные переменные

**Обязательные переменные:**
- `TG_BOT_TOKEN` - токен Telegram бота
- `S3_BUCKET` - имя бакета S3
- `S3_ENDPOINT_URL` - URL эндпоинта S3
- `AWS_ACCESS_KEY_ID` - Access Key ID для S3
- `AWS_SECRET_ACCESS_KEY` - Secret Access Key для S3
- `BASE_URL` - базовый URL приложения

**Опциональные переменные:**
- `REPLICATE_API_TOKEN` - токен API Replicate
- `S3_FORCE_PATH_STYLE` - принудительное использование path-style для S3
- `S3_USE_SSL` - использование SSL для S3

## Безопасность

⚠️ **Важно:** Не коммитьте файлы `.env` с реальными токенами и ключами в репозиторий!

Используйте `.env.example` как шаблон и добавляйте `.env` в `.gitignore`.

## Требования

- PowerShell 5.1 или выше
- Для скриптов работы с YC CLI: установленный и настроенный YC CLI (см. [docs/setup/yc-cli-setup.md](../../docs/setup/yc-cli-setup.md))

## Разрешения

При первом запуске скриптов PowerShell может запросить разрешение на выполнение. Если скрипты заблокированы, выполните:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Это разрешит выполнение локальных скриптов.
