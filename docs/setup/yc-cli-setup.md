# Настройка Yandex Cloud CLI (YC CLI)

## Зачем нужен YC CLI?

YC CLI (Yandex Cloud Command Line Interface) - это инструмент командной строки для управления ресурсами Yandex Cloud. Используется для:
- Создания и управления бакетами Object Storage
- Создания сервисных аккаунтов
- Управления Cloud Functions
- Настройки API Gateway
- И других операций с инфраструктурой Yandex Cloud

## Установка YC CLI

### Windows (PowerShell)

**Вариант 1: Использовать готовый скрипт (рекомендуется)**

```powershell
# Перейти в папку со скриптами
cd scripts\powershell

# Запустить скрипт установки
.\install-yc-cli.ps1
```

**Вариант 2: Установка вручную**

```powershell
# Скачать и установить YC CLI
iex (New-Object System.Net.WebClient).DownloadString('https://storage.yandexcloud.net/yandexcloud-yc/install.ps1')
```

После выполнения скрипт предложит добавить директорию `yc` в PATH. Следовать инструкциям на экране.

После установки перезапустить терминал или выполнить:
```powershell
refreshenv
```

### Linux/macOS

```bash
curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
```

После установки перезапустить терминал или выполнить:
```bash
# Linux
source ~/.bashrc

# macOS (zsh)
source ~/.zshrc
```

### Альтернативный способ (для всех платформ)

Скачать установщик с официального сайта: https://yandex.cloud/en/docs/cli/quickstart

## Инициализация YC CLI

После установки необходимо инициализировать CLI:

```bash
yc init
```

Следовать инструкциям:

1. **Ввести OAuth токен:**
   - Получить токен на странице: https://oauth.yandex.ru/authorize?response_type=token&client_id=1a6990aa636648e9b2ef855fa7bec2fb
   - Скопировать токен из адресной строки (параметр `access_token`)
   - Вставить токен в терминал

2. **Выбрать облако (cloud):**
   - Выбрать облако из списка (обычно одно облако)

3. **Выбрать каталог (folder):**
   - Выбрать каталог, в котором будут создаваться ресурсы
   - Если каталога нет, создать его в консоли: https://console.cloud.yandex.ru

4. **Выбрать зону по умолчанию (default zone):**
   - Выбрать зону (например, `ru-central1-a`, `ru-central1-b`, `ru-central1-c`)

## Проверка конфигурации

Проверить, что CLI настроен правильно:

```bash
yc config list
```

Должны отображаться:
- `token` - OAuth токен
- `cloud-id` - ID облака
- `folder-id` - ID каталога
- `compute-default-zone` - зона по умолчанию

## Проверка текущего пользователя и диагностика ошибок доступа

### Как узнать под каким пользователем работает yc

YC CLI использует OAuth токен для аутентификации. Чтобы узнать, под каким пользователем вы работаете:

**Способ 1: Проверка через список доступных каталогов**

```bash
# Посмотреть, к каким каталогам есть доступ
yc resource-manager folder list

# Посмотреть информацию о конкретном каталоге
yc resource-manager folder get <folder-id>
```

**Способ 2: Проверка через конфигурацию**

```bash
# Посмотреть текущую конфигурацию
yc config list

# Посмотреть только токен (первые и последние символы для безопасности)
yc config get token
```

**Способ 3: Проверка через API (PowerShell)**

```powershell
# Получить информацию о текущем аккаунте через API
$token = yc config get token
$headers = @{ "Authorization" = "Bearer $token" }
Invoke-RestMethod -Uri "https://iam.api.cloud.yandex.net/iam/v1/userAccounts" -Headers $headers | ConvertTo-Json
```

**Способ 4: Проверка через список облаков**

```bash
# Посмотреть доступные облака
yc resource-manager cloud list
```

### Диагностика ошибки "rpc error: code = PermissionDenied desc = Access Denied"

Ошибка `PermissionDenied` означает, что у текущего пользователя недостаточно прав для выполнения операции. Вот пошаговая диагностика:

**1. Проверьте действительность OAuth токена**

OAuth токены Yandex Cloud имеют ограниченный срок действия (обычно 1 год). Если токен истек:

```bash
# Проверить, работает ли токен
yc resource-manager cloud list

# Если ошибка - выполните повторную инициализацию
yc init
```

**2. Проверьте права доступа к каталогу**

```bash
# Получить список каталогов, к которым есть доступ
yc resource-manager folder list

# Проверить права на конкретный каталог
yc resource-manager folder list-access-bindings <folder-id>
```

**3. Проверьте правильность folder-id**

```bash
# Убедитесь, что folder-id в конфигурации правильный
yc config get folder-id

# Сравните с доступными каталогами
yc resource-manager folder list
```

**4. Проверьте необходимые роли**

Для создания бакетов Object Storage нужна роль `storage.editor` или `editor` на уровне каталога:

```bash
# Проверить роли текущего пользователя на каталог
yc resource-manager folder list-access-bindings <folder-id>
```

**5. Типичные причины ошибки PermissionDenied:**

- **Истекший OAuth токен** - выполните `yc init` для обновления
- **Неправильный folder-id** - проверьте через `yc resource-manager folder list`
- **Недостаточно прав** - нужна роль `editor` или `admin` на каталог
- **Каталог не существует** - проверьте существование каталога
- **Используется сервисный аккаунт без прав** - убедитесь, что у сервисного аккаунта есть нужные роли

**6. Решение проблемы:**

```bash
# Шаг 1: Обновить токен
yc init

# Шаг 2: Проверить доступ к каталогу
yc resource-manager folder get <folder-id>

# Шаг 3: Если нет доступа, попросите администратора облака назначить роль:
# - Для создания бакетов: роль 'storage.editor' или 'editor'
# - Для управления ресурсами: роль 'editor' или 'admin'
```

**7. Проверка через веб-консоль:**

Если проблемы сохраняются, проверьте права в веб-консоли:
- Откройте: https://console.cloud.yandex.ru
- Перейдите в нужный каталог
- Проверьте раздел "Права доступа" (Access bindings)
- Убедитесь, что ваш аккаунт имеет необходимые роли

## Полезные команды

### Получить список каталогов

```bash
yc resource-manager folder list
```

### Получить список облаков

```bash
yc resource-manager cloud list
```

### Проверить версию CLI

```bash
yc version
```

### Получить справку по команде

```bash
yc <команда> --help
```

Например:
```bash
yc storage bucket create --help
```

## Следующие шаги

После установки и настройки YC CLI:

1. Создать бакет Object Storage (см. [feature-2.5-yandex-s3.md](../../features/feature-2.5-yandex-s3.md))
2. Создать сервисный аккаунт для доступа к ресурсам
3. Настроить Cloud Functions (см. [feature-04-yandex-cloud.md](../../features/feature-04-yandex-cloud.md))

## Дополнительные ресурсы

- Официальная документация: https://yandex.cloud/en/docs/cli/
- Справочник команд: https://yandex.cloud/en/docs/cli/cli-ref/
- GitHub репозиторий: https://github.com/yandex-cloud/yandex-cloud-cli
