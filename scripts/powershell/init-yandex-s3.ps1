# Скрипт инициализации Yandex Object Storage
# Использование: .\init-yandex-s3.ps1 -BucketName "ai-shtender-bucket" -FolderId "your-folder-id"
# Или создайте файл yc.env с переменными YC_FOLDER_ID и YC_BUCKET_NAME

param(
    [Parameter(Mandatory=$false)]
    [string]$BucketName,
    
    [Parameter(Mandatory=$false)]
    [string]$FolderId,
    
    [string]$LifecycleConfigPath = (Join-Path $PSScriptRoot "lifecycle.json"),
    
    [string]$EnvFilePath = (Join-Path $PSScriptRoot "yc.env")
)

Write-Host "Инициализация Yandex Object Storage..." -ForegroundColor Green

# Загрузка переменных из файла yc.env, если он существует
$ycEnvFolderId = $null
$ycEnvBucketName = $null

if (Test-Path $EnvFilePath) {
    Write-Host "`nЗагрузка конфигурации из $EnvFilePath..." -ForegroundColor Yellow
    Get-Content $EnvFilePath | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            if ($key -eq "YC_FOLDER_ID" -and $value) {
                $ycEnvFolderId = $value
            }
            if ($key -eq "YC_BUCKET_NAME" -and $value) {
                $ycEnvBucketName = $value
            }
        }
    }
    
    if ($ycEnvFolderId) {
        Write-Host "  YC_FOLDER_ID найден в конфигурации" -ForegroundColor Green
    }
    if ($ycEnvBucketName) {
        Write-Host "  YC_BUCKET_NAME найден в конфигурации" -ForegroundColor Green
    }
} else {
    Write-Host "`nФайл $EnvFilePath не найден. Используйте параметры командной строки." -ForegroundColor Yellow
}

# Использование значений из параметров или из файла конфигурации
if (-not $FolderId) {
    if ($ycEnvFolderId) {
        $FolderId = $ycEnvFolderId
        Write-Host "`nИспользуется folder-id из конфигурации: $FolderId" -ForegroundColor Cyan
    } else {
        Write-Host "`nОШИБКА: folder-id не указан!" -ForegroundColor Red
        Write-Host "Укажите folder-id одним из способов:" -ForegroundColor Yellow
        Write-Host "  1. Параметр: -FolderId 'your-folder-id'" -ForegroundColor Yellow
        Write-Host "  2. В файле yc.env: YC_FOLDER_ID=your-folder-id" -ForegroundColor Yellow
        exit 1
    }
}

if (-not $BucketName) {
    if ($ycEnvBucketName) {
        $BucketName = $ycEnvBucketName
        Write-Host "Используется bucket-name из конфигурации: $BucketName" -ForegroundColor Cyan
    } else {
        Write-Host "`nОШИБКА: bucket-name не указан!" -ForegroundColor Red
        Write-Host "Укажите bucket-name одним из способов:" -ForegroundColor Yellow
        Write-Host "  1. Параметр: -BucketName 'my-bucket'" -ForegroundColor Yellow
        Write-Host "  2. В файле yc.env: YC_BUCKET_NAME=my-bucket" -ForegroundColor Yellow
        exit 1
    }
}

# Проверка наличия YC CLI
try {
    $ycVersion = yc version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "YC CLI не установлен или не найден в PATH"
    }
    Write-Host "YC CLI найден: $ycVersion" -ForegroundColor Green
}
catch {
    Write-Host "Ошибка: YC CLI не установлен. Установите его с помощью .\install-yc-cli.ps1" -ForegroundColor Red
    exit 1
}

# Проверка конфигурации YC CLI
Write-Host "`nПроверка конфигурации YC CLI..." -ForegroundColor Yellow
try {
    $config = yc config list 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Ошибка: YC CLI не настроен. Выполните 'yc init' для инициализации." -ForegroundColor Red
        exit 1
    }
    
    # Проверяем наличие folder-id в конфигурации
    if ($config -notmatch "folder-id") {
        Write-Host "Предупреждение: folder-id не найден в конфигурации YC CLI" -ForegroundColor Yellow
    }
    
    Write-Host "Конфигурация YC CLI проверена" -ForegroundColor Green
}
catch {
    Write-Host "Ошибка при проверке конфигурации: $_" -ForegroundColor Red
    exit 1
}

# Проверка доступа к каталогу
Write-Host "`nПроверка доступа к каталогу $FolderId..." -ForegroundColor Yellow
try {
    $null = yc resource-manager folder get $FolderId 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Ошибка: Не удалось получить доступ к каталогу $FolderId" -ForegroundColor Red
        Write-Host "Возможные причины:" -ForegroundColor Yellow
        Write-Host "  1. Неправильный folder-id" -ForegroundColor Yellow
        Write-Host "  2. Недостаточно прав доступа к каталогу" -ForegroundColor Yellow
        Write-Host "  3. Каталог не существует" -ForegroundColor Yellow
        Write-Host "`nПроверьте список каталогов: yc resource-manager folder list" -ForegroundColor Cyan
        exit 1
    }
    Write-Host "Доступ к каталогу подтвержден" -ForegroundColor Green
}
catch {
    Write-Host "Ошибка при проверке доступа к каталогу: $_" -ForegroundColor Red
    exit 1
}

# Проверка существования бакета
Write-Host "`nПроверка существования бакета $BucketName..." -ForegroundColor Yellow
try {
    $null = yc storage bucket get --name $BucketName 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Бакет $BucketName уже существует" -ForegroundColor Green
        $bucketExists = $true
    } else {
        $bucketExists = $false
    }
}
catch {
    $bucketExists = $false
}

# Создание бакета
if (-not $bucketExists) {
    Write-Host "`nСоздание бакета: $BucketName..." -ForegroundColor Yellow
    try {
        $output = yc storage bucket create --name $BucketName --folder-id $FolderId 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Бакет успешно создан!" -ForegroundColor Green
        } else {
            $errorOutput = $output -join "`n"
            if ($errorOutput -match 'PermissionDenied' -or $errorOutput -match 'Access Denied') {
                Write-Host "`nОШИБКА: Недостаточно прав для создания бакета" -ForegroundColor Red
                Write-Host "`nВозможные решения:" -ForegroundColor Yellow
                Write-Host "  1. Проверьте, что ваш OAuth токен действителен:" -ForegroundColor Yellow
                Write-Host "     yc config list" -ForegroundColor Cyan
                Write-Host "     Если токен истек, выполните: yc init" -ForegroundColor Cyan
                Write-Host "`n  2. Убедитесь, что у вас есть права 'editor' или 'admin' на каталог:" -ForegroundColor Yellow
                Write-Host "     Проверьте права в консоли: https://console.cloud.yandex.ru" -ForegroundColor Cyan
                Write-Host "`n  3. Проверьте правильность folder-id:" -ForegroundColor Yellow
                Write-Host "     yc resource-manager folder list" -ForegroundColor Cyan
                Write-Host "`n  4. Если вы используете сервисный аккаунт, убедитесь, что у него есть роль 'storage.editor':" -ForegroundColor Yellow
                Write-Host "     yc resource-manager folder list-access-bindings $FolderId" -ForegroundColor Cyan
                Write-Host "`nДетали ошибки:" -ForegroundColor Yellow
                Write-Host $errorOutput -ForegroundColor Red
                exit 1
            } elseif ($errorOutput -match "already exists" -or $errorOutput -match "уже существует") {
                Write-Host "Бакет уже существует" -ForegroundColor Yellow
            } else {
                Write-Host "Ошибка при создании бакета:" -ForegroundColor Red
                Write-Host $errorOutput -ForegroundColor Red
                exit 1
            }
        }
    }
    catch {
        Write-Host "Ошибка при создании бакета: $_" -ForegroundColor Red
        exit 1
    }
}

# Применение lifecycle policy, если файл существует
if (Test-Path $LifecycleConfigPath) {
    Write-Host "`nПрименение lifecycle policy из $LifecycleConfigPath..." -ForegroundColor Yellow
    try {
        $output = yc storage bucket update --name $BucketName --lifecycle-rules-from-file $LifecycleConfigPath 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Lifecycle policy успешно применена!" -ForegroundColor Green
        } else {
            $errorOutput = $output -join "`n"
            if ($errorOutput -match 'PermissionDenied' -or $errorOutput -match 'Access Denied') {
                Write-Host "Ошибка: Недостаточно прав для применения lifecycle policy" -ForegroundColor Red
                Write-Host "Убедитесь, что у вас есть права 'storage.editor' на каталог" -ForegroundColor Yellow
                Write-Host "Детали ошибки:" -ForegroundColor Yellow
                Write-Host $errorOutput -ForegroundColor Red
            } else {
                Write-Host "Ошибка при применении lifecycle policy: $errorOutput" -ForegroundColor Red
            }
        }
    }
    catch {
        Write-Host "Ошибка при применении lifecycle policy: $_" -ForegroundColor Red
    }
} else {
    Write-Host "`nФайл lifecycle.json не найден по пути: $LifecycleConfigPath" -ForegroundColor Yellow
    Write-Host "Пропускаем настройку lifecycle policy." -ForegroundColor Yellow
}

Write-Host "`nИнициализация завершена!" -ForegroundColor Green
Write-Host "Имя бакета: $BucketName" -ForegroundColor Cyan
Write-Host ('ID каталога: ' + $FolderId) -ForegroundColor Cyan
