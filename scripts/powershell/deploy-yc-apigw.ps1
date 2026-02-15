# Деплой API Gateway (create-or-update) из openapi.yaml.
# Скрипт:
# - находит function_id для двух функций (по именам из yc.env)
# - находит service_account_id (по имени из yc.env)
# - рендерит спецификацию (подставляет IDs вместо плейсхолдеров)
# - создает/обновляет API Gateway
# - печатает публичный URL
#
# Использование:
#   cd scripts\powershell
#   .\deploy-yc-apigw.ps1

param(
    [string]$EnvFilePath = (Join-Path $PSScriptRoot "yc.env"),
    [string]$OpenApiTemplatePath = (Resolve-Path (Join-Path $PSScriptRoot "..\\..\\openapi.yaml"))
)

$ErrorActionPreference = "Stop"

Write-Host "Деплой API Gateway..." -ForegroundColor Green

function Read-EnvFile([string]$path) {
    $map = @{}
    if (-not (Test-Path $path)) {
        return $map
    }
    Get-Content $path | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim()
            if ($k) {
                $map[$k] = $v
            }
        }
    }
    return $map
}

function Require([hashtable]$map, [string]$key) {
    if (-not $map.ContainsKey($key) -or -not $map[$key]) {
        throw "Обязательный ключ не найден: $key"
    }
    return $map[$key]
}

# Проверка наличия YC CLI
try {
    $ycVersion = yc version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "YC CLI не найден" }
    Write-Host "YC CLI найден: $ycVersion" -ForegroundColor Green
} catch {
    Write-Host "Ошибка: YC CLI не установлен. Установите его через scripts\\powershell\\install-yc-cli.ps1" -ForegroundColor Red
    exit 1
}

# Конфиг
$cfg = Read-EnvFile $EnvFilePath
try {
    $folderId = Require $cfg "YC_FOLDER_ID"
    $apigwName = Require $cfg "YC_APIGW_NAME"
    $saName = Require $cfg "YC_SERVICE_ACCOUNT_NAME"
    $fnTelegramName = Require $cfg "YC_FUNCTION_TELEGRAM_NAME"
    $fnReplicateName = Require $cfg "YC_FUNCTION_REPLICATE_NAME"
} catch {
    Write-Host "Ошибка конфигурации yc.env: $_" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $OpenApiTemplatePath)) {
    Write-Host "ОШИБКА: openapi.yaml не найден: $OpenApiTemplatePath" -ForegroundColor Red
    exit 1
}

# Найти SA id
Write-Host "`nПоиск сервисного аккаунта $saName..." -ForegroundColor Yellow
$saId = $null
try {
    $saListJson = yc iam service-account list --folder-id $folderId --format json 2>&1
    if ($LASTEXITCODE -ne 0) { throw ($saListJson -join "`n") }
    $saList = $saListJson | ConvertFrom-Json
    $sa = $saList | Where-Object { $_.name -eq $saName } | Select-Object -First 1
    if ($sa) { $saId = $sa.id }
} catch {
    Write-Host "Ошибка при поиске сервисного аккаунта: $_" -ForegroundColor Red
    exit 1
}
if (-not $saId) {
    Write-Host "ОШИБКА: сервисный аккаунт '$saName' не найден. Запустите init-yc-iam.ps1" -ForegroundColor Red
    exit 1
}
Write-Host "Service Account ID: $saId" -ForegroundColor Green

function Get-FunctionId([string]$fnName) {
    $fnJson = yc serverless function get --name $fnName --format json 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ("Не удалось получить функцию '$fnName'. Сначала задеплойте функции (deploy-yc-functions.ps1).`n" + ($fnJson -join "`n"))
    }
    $fn = $fnJson | ConvertFrom-Json
    return $fn.id
}

Write-Host "`nПолучение function_id..." -ForegroundColor Yellow
try {
    $fnTelegramId = Get-FunctionId $fnTelegramName
    $fnReplicateId = Get-FunctionId $fnReplicateName
} catch {
    Write-Host "Ошибка: $_" -ForegroundColor Red
    exit 1
}
Write-Host "FN_TELEGRAM_ID: $fnTelegramId" -ForegroundColor Green
Write-Host "FN_REPLICATE_ID: $fnReplicateId" -ForegroundColor Green

# Рендер openapi.yaml
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")
$ycDir = Join-Path $repoRoot ".yc"
New-Item -ItemType Directory -Force -Path $ycDir | Out-Null
$renderedSpecPath = Join-Path $ycDir "openapi.rendered.yaml"

Write-Host "`nРендер спецификации..." -ForegroundColor Yellow
$spec = Get-Content $OpenApiTemplatePath -Raw
$spec = $spec.Replace("<FN_TELEGRAM_ID>", $fnTelegramId)
$spec = $spec.Replace("<FN_REPLICATE_ID>", $fnReplicateId)
$spec = $spec.Replace("<SERVICE_ACCOUNT_ID>", $saId)
Set-Content -Path $renderedSpecPath -Value $spec -Encoding UTF8
Write-Host "Rendered spec: $renderedSpecPath" -ForegroundColor Green

# Create-or-update API gateway
Write-Host "`nСоздание/обновление API Gateway '$apigwName'..." -ForegroundColor Yellow
$gw = $null
try {
    $gwJson = yc serverless api-gateway get --name $apigwName --format json 2>&1
    if ($LASTEXITCODE -eq 0) {
        $gw = $gwJson | ConvertFrom-Json
    }
} catch {
    $gw = $null
}

# yc пишет прогресс в stderr — PowerShell не должен трактовать это как ошибку
$prevEA = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    if (-not $gw) {
        $out = yc serverless api-gateway create --name $apigwName --folder-id $folderId --spec $renderedSpecPath --format json 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Ошибка при создании API Gateway:" -ForegroundColor Red
            Write-Host ($out -join "`n") -ForegroundColor Red
            exit 1
        }
        # Вывод может содержать прогресс (stderr) + многострочный JSON
        $text = $out -join "`n"
        $m = [regex]::Match($text, '\{[\s\S]*\}', [System.Text.RegularExpressions.RegexOptions]::Singleline)
        if (-not $m.Success) { throw "Не удалось извлечь JSON из вывода yc (create)" }
        $gw = $m.Value | ConvertFrom-Json
        Write-Host "API Gateway создан: id=$($gw.id)" -ForegroundColor Green
    } else {
        $out = yc serverless api-gateway update --name $apigwName --spec $renderedSpecPath --format json 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Ошибка при обновлении API Gateway:" -ForegroundColor Red
            Write-Host ($out -join "`n") -ForegroundColor Red
            exit 1
        }
        $text = $out -join "`n"
        $m = [regex]::Match($text, '\{[\s\S]*\}', [System.Text.RegularExpressions.RegexOptions]::Singleline)
        if (-not $m.Success) { throw "Не удалось извлечь JSON из вывода yc (update)" }
        $gw = $m.Value | ConvertFrom-Json
        Write-Host "API Gateway обновлен: id=$($gw.id)" -ForegroundColor Green
    }
} finally {
    $ErrorActionPreference = $prevEA
}

# Получить домен (публичный URL)
try {
    $gwJson2 = yc serverless api-gateway get --name $apigwName --format json 2>&1
    if ($LASTEXITCODE -ne 0) { throw ($gwJson2 -join "`n") }
    $text2 = $gwJson2 -join "`n"
    $m2 = [regex]::Match($text2, '\{[\s\S]*\}', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $m2.Success) { throw "Не удалось извлечь JSON из вывода yc (get)" }
    $gw2 = $m2.Value | ConvertFrom-Json
    $domain = $gw2.domain
    if (-not $domain) { $domain = $gw2.domainId }
    if (-not $domain) { $domain = $gw2.host }
    if (-not $domain) {
        throw "Не удалось извлечь domain из ответа yc"
    }
    $baseUrl = "https://$domain"
    Write-Host "`nBASE_URL (API Gateway): $baseUrl" -ForegroundColor Cyan
} catch {
    Write-Host "Не удалось получить домен API Gateway: $_" -ForegroundColor Yellow
    Write-Host "Откройте API Gateway в консоли и возьмите поле Domain." -ForegroundColor Yellow
}

