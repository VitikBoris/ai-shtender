# Простейший smoke-test API Gateway эндпоинтов.
# Он НЕ пытается полноценно прогнать E2E (без реального Telegram/Replicate),
# а проверяет, что роуты отвечают 200 и функции вызываются.
#
# Использование:
#   cd scripts\powershell
#   .\smoke-test.ps1 -BaseUrl "https://<apigw-domain>"

param(
    [Parameter(Mandatory=$true)]
    [string]$BaseUrl
)

$ErrorActionPreference = "Stop"

Write-Host "Smoke test for BASE_URL=$BaseUrl" -ForegroundColor Green

function PostJson([string]$url, [object]$obj) {
    # В Windows PowerShell 5.1 Invoke-WebRequest иногда "зависает" из-за IE-парсера/прогресса.
    # Ставим таймаут и по возможности включаем BasicParsing.
    $ProgressPreference = 'SilentlyContinue'
    $body = ($obj | ConvertTo-Json -Depth 10)
    $args = @{
        Method      = 'Post'
        Uri         = $url
        Body        = $body
        ContentType = 'application/json'
        TimeoutSec  = 30
    }
    if ((Get-Command Invoke-WebRequest).Parameters.ContainsKey('UseBasicParsing')) {
        $args['UseBasicParsing'] = $true
    }
    return Invoke-WebRequest @args
}

try {
    $tgUrl = "$BaseUrl/webhook/telegram"
    $repUrl = "$BaseUrl/webhook/replicate"

    Write-Host "`nPOST $tgUrl (empty payload)..." -ForegroundColor Yellow
    $r1 = PostJson $tgUrl @{}
    Write-Host "Status: $($r1.StatusCode)" -ForegroundColor Green
    Write-Host $r1.Content

    Write-Host "`nPOST $repUrl (unknown prediction id)..." -ForegroundColor Yellow
    $r2 = PostJson $repUrl @{
        id = "smoke-test"
        status = "succeeded"
        output = "https://example.com/result.jpg"
    }
    Write-Host "Status: $($r2.StatusCode)" -ForegroundColor Green
    Write-Host $r2.Content

    Write-Host "`nSmoke test OK" -ForegroundColor Green
} catch {
    Write-Host "`nSmoke test FAILED: $_" -ForegroundColor Red
    exit 1
}

