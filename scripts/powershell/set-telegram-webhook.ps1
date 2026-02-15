# Установка Telegram webhook на API Gateway URL.
#
# Использование:
#   cd scripts\powershell
#   .\set-telegram-webhook.ps1 -BaseUrl "https://<apigw-domain>"
#   # или без BaseUrl (тогда домен берется из YC_APIGW_NAME через yc)
#   .\set-telegram-webhook.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$BaseUrl = "",

    [string]$EnvFilePath = (Join-Path $PSScriptRoot "yc.env"),
    [string]$SecretsFilePath = (Join-Path $PSScriptRoot "yc.secrets.env")
)

$ErrorActionPreference = "Stop"

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

Write-Host "Настройка Telegram webhook..." -ForegroundColor Green

$cfg = Read-EnvFile $EnvFilePath
$secrets = Read-EnvFile $SecretsFilePath

$tgToken = Require $secrets "TG_BOT_TOKEN"
$apigwName = $cfg["YC_APIGW_NAME"]

if (-not $BaseUrl) {
    if (-not $apigwName) {
        throw "BaseUrl не задан и YC_APIGW_NAME не найден в yc.env"
    }

    # Получить домен API Gateway через yc
    try {
        $gwJson = yc serverless api-gateway get --name $apigwName --format json 2>&1
        if ($LASTEXITCODE -ne 0) { throw ($gwJson -join "`n") }
        $gw = $gwJson | ConvertFrom-Json
        $domain = $gw.domain
        if (-not $domain) { throw "Не удалось извлечь domain" }
        $BaseUrl = "https://$domain"
    } catch {
        throw "Не удалось получить BASE_URL из API Gateway: $_"
    }
}

$webhookUrl = "$BaseUrl/webhook/telegram"
Write-Host "Webhook URL: $webhookUrl" -ForegroundColor Cyan

$apiUrl = "https://api.telegram.org/bot$tgToken/setWebhook"
$payload = @{
    url = $webhookUrl
}

try {
    $resp = Invoke-RestMethod -Method Post -Uri $apiUrl -Body ($payload | ConvertTo-Json) -ContentType "application/json"
    Write-Host "setWebhook ответ:" -ForegroundColor Green
    $resp | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Ошибка при установке webhook: $_" -ForegroundColor Red
    exit 1
}

try {
    $infoUrl = "https://api.telegram.org/bot$tgToken/getWebhookInfo"
    $info = Invoke-RestMethod -Method Get -Uri $infoUrl
    Write-Host "`ngetWebhookInfo:" -ForegroundColor Green
    $info | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Не удалось получить getWebhookInfo: $_" -ForegroundColor Yellow
}

