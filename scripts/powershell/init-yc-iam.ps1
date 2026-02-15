# Скрипт инициализации IAM для проекта (Service Account + роли на folder)
# Использование:
#   cd scripts\powershell
#   .\init-yc-iam.ps1
#
# По умолчанию берет настройки из yc.env (в той же папке).
# Можно переопределять через параметры.

param(
    [Parameter(Mandatory=$false)]
    [string]$FolderId,

    [Parameter(Mandatory=$false)]
    [string]$ServiceAccountName,

    [Parameter(Mandatory=$false)]
    [switch]$GrantEditor,

    [string]$EnvFilePath = (Join-Path $PSScriptRoot "yc.env")
)

Write-Host "Инициализация IAM (service account + роли)..." -ForegroundColor Green

function Read-EnvFileValue([string]$path, [string]$key) {
    if (-not (Test-Path $path)) {
        return $null
    }
    $value = $null
    Get-Content $path | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim()
            if ($k -eq $key -and $v) {
                $value = $v
            }
        }
    }
    return $value
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

# Подтянуть значения из yc.env при необходимости
if (-not $FolderId) {
    $FolderId = Read-EnvFileValue -path $EnvFilePath -key "YC_FOLDER_ID"
}
if (-not $ServiceAccountName) {
    $ServiceAccountName = Read-EnvFileValue -path $EnvFilePath -key "YC_SERVICE_ACCOUNT_NAME"
}

if (-not $FolderId) {
    Write-Host ""
Write-Host "ОШИБКА: YC_FOLDER_ID не указан!" -ForegroundColor Red
    Write-Host "Укажите folder-id одним из способов:" -ForegroundColor Yellow
    Write-Host "  1. Параметр: -FolderId '<your-folder-id>'" -ForegroundColor Yellow
    Write-Host "  2. В файле yc.env: YC_FOLDER_ID=<your-folder-id>" -ForegroundColor Yellow
    exit 1
}

if (-not $ServiceAccountName) {
    $ServiceAccountName = "ai-shtender-sa"
    Write-Host ""
Write-Host "YC_SERVICE_ACCOUNT_NAME не задан, использую дефолт: $ServiceAccountName" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Каталог (folder-id): $FolderId" -ForegroundColor Cyan
Write-Host "Service Account name: $ServiceAccountName" -ForegroundColor Cyan

# Проверка доступа к каталогу
Write-Host ""
Write-Host "Проверка доступа к каталогу..." -ForegroundColor Yellow
try {
    $null = yc resource-manager folder get $FolderId 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Не удалось получить доступ к каталогу $FolderId"
    }
    Write-Host "Доступ к каталогу подтвержден" -ForegroundColor Green
}
catch {
    Write-Host "Ошибка: $_" -ForegroundColor Red
    Write-Host "Проверьте, что yc init выполнен и у вас есть права на каталог." -ForegroundColor Yellow
    exit 1
}

# Найти/создать сервисный аккаунт
Write-Host ""
Write-Host "Поиск сервисного аккаунта..." -ForegroundColor Yellow
$sa = $null
try {
    $saListJson = yc iam service-account list --folder-id $FolderId --format json 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ($saListJson -join "`n")
    }
    $saList = $saListJson | ConvertFrom-Json
    $sa = $saList | Where-Object { $_.name -eq $ServiceAccountName } | Select-Object -First 1
}
catch {
    Write-Host "Ошибка при получении списка сервисных аккаунтов: $_" -ForegroundColor Red
    exit 1
}

if (-not $sa) {
    Write-Host "Сервисный аккаунт не найден, создаю..." -ForegroundColor Yellow
    try {
        $saCreateJson = yc iam service-account create --folder-id $FolderId --name $ServiceAccountName --format json 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw ($saCreateJson -join "`n")
        }
        $sa = $saCreateJson | ConvertFrom-Json
        Write-Host "Сервисный аккаунт создан: id=$($sa.id)" -ForegroundColor Green
    }
    catch {
        Write-Host "Ошибка при создании сервисного аккаунта: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Сервисный аккаунт найден: id=$($sa.id)" -ForegroundColor Green
}

$saId = $sa.id
if (-not $saId) {
    Write-Host "ОШИБКА: Не удалось получить service account id" -ForegroundColor Red
    exit 1
}

# Роли для назначения
$roles = @(
    "storage.editor",
    "serverless.functions.invoker"
)
if ($GrantEditor) {
    $roles += "editor"
}

# Получить текущие биндинги, чтобы не дублировать
Write-Host ""
Write-Host "Проверка текущих ролей на каталоге..." -ForegroundColor Yellow
$bindings = @()
try {
    $bindingsJson = yc resource-manager folder list-access-bindings $FolderId --format json 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ($bindingsJson -join "`n")
    }
    $bindings = $bindingsJson | ConvertFrom-Json
}
catch {
    Write-Host "Ошибка при получении access bindings: $_" -ForegroundColor Red
    exit 1
}

function Has-Binding([object[]]$bindings, [string]$role, [string]$saId) {
    foreach ($b in $bindings) {
        if ($b.roleId -ne $role) { continue }
        foreach ($m in $b.subjects) {
            if ($m.type -eq "serviceAccount" -and $m.id -eq $saId) {
                return $true
            }
        }
    }
    return $false
}

Write-Host ""
Write-Host "Назначение ролей сервисному аккаунту..." -ForegroundColor Yellow
foreach ($role in $roles) {
    if (Has-Binding -bindings $bindings -role $role -saId $saId) {
        Write-Host "  Роль уже назначена: $role" -ForegroundColor Green
        continue
    }

    Write-Host "  Назначаю роль: $role" -ForegroundColor Cyan
    $out = yc resource-manager folder add-access-binding $FolderId --role $role --subject "serviceAccount:$saId" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Ошибка при назначении роли ${role}:" -ForegroundColor Red
        Write-Host ($out -join "`n") -ForegroundColor Red
        exit 1
    }
    Write-Host "  Роль назначена: $role" -ForegroundColor Green
}

Write-Host ""
Write-Host "Готово." -ForegroundColor Green
Write-Host "Service Account ID: $saId" -ForegroundColor Cyan
Write-Host "Service Account Name: $ServiceAccountName" -ForegroundColor Cyan

