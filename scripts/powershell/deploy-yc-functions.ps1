# Deploy Cloud Functions (create-or-update) for the project.
# - builds ZIP (src/ + handler.py + callback.py + requirements.txt)
# - creates/updates 2 functions: Telegram and Replicate
# - passes env vars from yc.env and yc.secrets.env
#
# Usage:
#   cd scripts\powershell
#   .\deploy-yc-functions.ps1
#   .\deploy-yc-functions.ps1 -BaseUrl "https://<apigw-domain>"

param(
    [Parameter(Mandatory=$false)]
    [string]$BaseUrl = "",

    [string]$EnvFilePath = (Join-Path $PSScriptRoot "yc.env"),
    [string]$SecretsFilePath = (Join-Path $PSScriptRoot "yc.secrets.env")
)

$ErrorActionPreference = "Stop"

# Silence YC CLI init warning so it does not break JSON parsing from stderr
if (-not $env:YC_CLI_INITIALIZATION_SILENCE) {
    $env:YC_CLI_INITIALIZATION_SILENCE = "true"
}

Write-Host "Deploying Cloud Functions..." -ForegroundColor Green

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
        throw "Required key not found: $key"
    }
    return $map[$key]
}

function ConvertTo-NormalizedBaseUrl([string]$url) {
    if (-not $url) { return "" }
    $u = $url.Trim()
    if (($u.StartsWith('"') -and $u.EndsWith('"')) -or ($u.StartsWith("'") -and $u.EndsWith("'"))) {
        $u = $u.Substring(1, $u.Length - 2)
    }
    return $u.Trim()
}

function Get-ApiGwBaseUrl([string]$apigwName) {
    $prevEA = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = yc serverless api-gateway get --name $apigwName --format json 2>&1
    } finally {
        $ErrorActionPreference = $prevEA
    }
    if ($LASTEXITCODE -ne 0) { throw ($out -join "`n") }
    $text = $out -join "`n"
    $m = [regex]::Match($text, '\{.*\}', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $m.Success) { throw "Could not extract JSON from yc (api-gateway get)" }
    $gw = $m.Value | ConvertFrom-Json
    $domain = $gw.domain
    if (-not $domain) { $domain = $gw.domainId }
    if (-not $domain) { $domain = $gw.host }
    if (-not $domain) { throw "Could not get domain from API Gateway '$apigwName'" }
    return ("https://{0}" -f $domain)
}

# Check YC CLI
try {
    $ycVersion = yc version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "YC CLI not found" }
    Write-Host "YC CLI: $ycVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: YC CLI not installed. Use scripts\powershell\install-yc-cli.ps1" -ForegroundColor Red
    exit 1
}

# Load config
$cfg = Read-EnvFile $EnvFilePath
$secrets = Read-EnvFile $SecretsFilePath

try {
    $folderId = Require $cfg "YC_FOLDER_ID"
    $bucketName = Require $cfg "YC_BUCKET_NAME"
    $saName = Require $cfg "YC_SERVICE_ACCOUNT_NAME"
    $fnTelegramName = Require $cfg "YC_FUNCTION_TELEGRAM_NAME"
    $fnReplicateName = Require $cfg "YC_FUNCTION_REPLICATE_NAME"
    $apigwName = $cfg["YC_APIGW_NAME"]
    $runtime = $cfg["YC_RUNTIME"]
    if (-not $runtime) { $runtime = "python311" }
} catch {
    Write-Host "Config error yc.env: $_" -ForegroundColor Red
    Write-Host "Copy yc.env.example to yc.env and fill values." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $SecretsFilePath)) {
    Write-Host "ERROR: secrets file not found: $SecretsFilePath" -ForegroundColor Red
    Write-Host "Copy yc.secrets.env.example to yc.secrets.env and fill tokens." -ForegroundColor Yellow
    exit 1
}

try {
    $tgToken = Require $secrets "TG_BOT_TOKEN"
    $replicateToken = Require $secrets "REPLICATE_API_TOKEN"
    $replicateModelVersion = Require $secrets "REPLICATE_MODEL_VERSION"
    $awsAccessKeyId = Require $secrets "AWS_ACCESS_KEY_ID"
    $awsSecretAccessKey = Require $secrets "AWS_SECRET_ACCESS_KEY"
} catch {
    Write-Host "Config error yc.secrets.env: $_" -ForegroundColor Red
    exit 1
}

# Find service account id (run init-yc-iam.ps1 first if needed)
Write-Host "`nLooking for service account $saName..." -ForegroundColor Yellow
$saId = $null
try {
    $saListJson = yc iam service-account list --folder-id $folderId --format json 2>&1
    if ($LASTEXITCODE -ne 0) { throw ($saListJson -join "`n") }
    $saList = $saListJson | ConvertFrom-Json
    $sa = $saList | Where-Object { $_.name -eq $saName } | Select-Object -First 1
    if ($sa) { $saId = $sa.id }
} catch {
    Write-Host "Error finding service account: $_" -ForegroundColor Red
    exit 1
}

if (-not $saId) {
    Write-Host "ERROR: service account '$saName' not found in folder $folderId" -ForegroundColor Red
    Write-Host "Run first: .\init-yc-iam.ps1" -ForegroundColor Yellow
    exit 1
}
Write-Host "Service Account ID: $saId" -ForegroundColor Green

# Prepare build/zip
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ycDir = Join-Path $repoRoot ".yc"
$buildDir = Join-Path $ycDir "build"

New-Item -ItemType Directory -Force -Path $ycDir | Out-Null
if (Test-Path $buildDir) {
    Remove-Item -Recurse -Force $buildDir
}
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

Write-Host "`nPreparing artifact (code directory)..." -ForegroundColor Yellow
Copy-Item -Recurse -Force (Join-Path $repoRoot "src") (Join-Path $buildDir "src")
Copy-Item -Force (Join-Path $repoRoot "handler.py") (Join-Path $buildDir "handler.py")
Copy-Item -Force (Join-Path $repoRoot "callback.py") (Join-Path $buildDir "callback.py")
Copy-Item -Force (Join-Path $repoRoot "requirements.functions.txt") (Join-Path $buildDir "requirements.txt")
# Шаблон штендера (режим «Создание штендера»)
$assetsSrc = Join-Path $repoRoot "assets"
if (Test-Path $assetsSrc) {
    Copy-Item -Recurse -Force $assetsSrc (Join-Path $buildDir "assets")
}

Write-Host "Artifact ready: $buildDir" -ForegroundColor Green

# Env vars for functions
$envVars = @(
    "TG_BOT_TOKEN=$tgToken",
    "REPLICATE_API_TOKEN=$replicateToken",
    "REPLICATE_MODEL_VERSION=$replicateModelVersion",
    "S3_BUCKET=$bucketName",
    "AWS_ACCESS_KEY_ID=$awsAccessKeyId",
    "AWS_SECRET_ACCESS_KEY=$awsSecretAccessKey",
    "S3_ENDPOINT_URL=https://storage.yandexcloud.net",
    "S3_FORCE_PATH_STYLE=false",
    "S3_USE_SSL=true"
)
$BaseUrl = ConvertTo-NormalizedBaseUrl $BaseUrl
if (-not $BaseUrl) {
    if ($apigwName) {
        Write-Host "BASE_URL not passed, getting from API Gateway '$apigwName'..." -ForegroundColor Yellow
        try {
            $BaseUrl = Get-ApiGwBaseUrl $apigwName
        } catch {
            Write-Host "Could not get BASE_URL from API Gateway: $_" -ForegroundColor Red
            Write-Host "Run first: .\deploy-yc-apigw.ps1, or pass -BaseUrl `"https://<apigw-domain>`"" -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "ERROR: BASE_URL not set. Pass -BaseUrl or set YC_APIGW_NAME in yc.env." -ForegroundColor Red
        exit 1
    }
}
$envVars += "BASE_URL=$BaseUrl"

function Ensure-Function([string]$fnName, [string]$folderId) {
    $fn = $null
    try {
        $fnJson = yc serverless function get --name $fnName --format json 2>&1
        if ($LASTEXITCODE -eq 0) {
            $fn = $fnJson | ConvertFrom-Json
        }
    } catch {
        $fn = $null
    }

    if (-not $fn) {
        Write-Host "Function '$fnName' not found, creating..." -ForegroundColor Yellow
        $createJson = yc serverless function create --name $fnName --folder-id $folderId --format json 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw ("Failed to create function ${fnName}: " + ($createJson -join "`n"))
        }
        $fn = $createJson | ConvertFrom-Json
        Write-Host "Function created: id=$($fn.id)" -ForegroundColor Green
    } else {
        Write-Host "Function found: '$fnName' (id=$($fn.id))" -ForegroundColor Green
    }
    return $fn
}

function Deploy-Version([string]$fnName, [string]$entrypoint, [string]$runtime, [string]$sourcePath, [string]$saId, [string[]]$envVars) {
    Write-Host "`nDeploying version for '$fnName' (entrypoint=$entrypoint)..." -ForegroundColor Yellow
    $envArgs = @()
    foreach ($e in $envVars) {
        $envArgs += "--environment"
        $envArgs += $e
    }
    $allArgs = @(
        "serverless", "function", "version", "create",
        "--function-name", $fnName,
        "--runtime", $runtime,
        "--entrypoint", $entrypoint,
        "--memory", "256m",
        "--execution-timeout", "30s",
        "--service-account-id", $saId,
        "--source-path", $sourcePath,
        "--format", "json"
    ) + $envArgs
    $prevEA = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & yc @allArgs 2>&1
    } finally {
        $ErrorActionPreference = $prevEA
    }

    if ($LASTEXITCODE -ne 0) {
        throw ("Failed to deploy version of ${fnName}: " + ($out -join "`n"))
    }
    $text = $out -join "`n"
    $m = [regex]::Match($text, '\{.*\}', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $m.Success) { throw ("Could not extract JSON from yc (version create) for ${fnName}: " + $text) }
    $ver = $m.Value | ConvertFrom-Json
    Write-Host "Version deployed: id=$($ver.id)" -ForegroundColor Green
    return $ver
}

function Deploy-Version-FromPackage([string]$fnName, [string]$entrypoint, [string]$runtime, [string]$pkgBucket, [string]$pkgObject, [string]$pkgSha256, [string]$saId, [string[]]$envVars) {
    Write-Host "`nDeploying version for '$fnName' (from Object Storage)..." -ForegroundColor Yellow
    $envArgs = @()
    foreach ($e in $envVars) {
        $envArgs += "--environment"
        $envArgs += $e
    }
    $allArgs = @(
        "serverless", "function", "version", "create",
        "--function-name", $fnName,
        "--runtime", $runtime,
        "--entrypoint", $entrypoint,
        "--memory", "256m",
        "--execution-timeout", "30s",
        "--service-account-id", $saId,
        "--package-bucket-name", $pkgBucket,
        "--package-object-name", $pkgObject,
        "--package-sha256", $pkgSha256,
        "--format", "json"
    ) + $envArgs
    $prevEA = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & yc @allArgs 2>&1
    } finally {
        $ErrorActionPreference = $prevEA
    }

    if ($LASTEXITCODE -ne 0) {
        throw ("Failed to deploy version of ${fnName}: " + ($out -join "`n"))
    }
    $text = $out -join "`n"
    $m = [regex]::Match($text, '\{.*\}', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $m.Success) { throw ("Could not extract JSON from yc (version create) for ${fnName}: " + $text) }
    $ver = $m.Value | ConvertFrom-Json
    Write-Host "Version deployed: id=$($ver.id)" -ForegroundColor Green
    return $ver
}

# Upload package to Object Storage (package > 3.5 MB — required for opencv + assets)
$pkgKey = "deploy/package.zip"
Write-Host "`nZipping and uploading package to s3://$bucketName/$pkgKey ..." -ForegroundColor Yellow
$env:AWS_ACCESS_KEY_ID = $awsAccessKeyId
$env:AWS_SECRET_ACCESS_KEY = $awsSecretAccessKey
$uploadScript = Join-Path $repoRoot "scripts\upload_package.py"
if (-not (Test-Path $uploadScript)) {
    Write-Host "ERROR: $uploadScript not found" -ForegroundColor Red
    exit 1
}
# boto3 needed for S3 upload
$prevEA = $ErrorActionPreference
$ErrorActionPreference = "Continue"
pip install --quiet boto3 2>$null
$ErrorActionPreference = $prevEA
$pkgSha256 = & python $uploadScript --build-dir $buildDir --bucket $bucketName --key $pkgKey 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Upload error: $pkgSha256" -ForegroundColor Red
    exit 1
}
$pkgSha256 = ($pkgSha256 | Select-Object -Last 1).Trim()
if (-not $pkgSha256 -or $pkgSha256.Length -ne 64) {
    Write-Host "ERROR: upload script did not return sha256 (got: $pkgSha256)" -ForegroundColor Red
    exit 1
}
Write-Host "Package uploaded, sha256=$pkgSha256" -ForegroundColor Green

# Ensure functions exist and deploy from package
try {
    $fnTelegram = Ensure-Function -fnName $fnTelegramName -folderId $folderId
    $fnReplicate = Ensure-Function -fnName $fnReplicateName -folderId $folderId

    $null = Deploy-Version-FromPackage -fnName $fnTelegramName -entrypoint "handler.handler" -runtime $runtime -pkgBucket $bucketName -pkgObject $pkgKey -pkgSha256 $pkgSha256 -saId $saId -envVars $envVars
    $null = Deploy-Version-FromPackage -fnName $fnReplicateName -entrypoint "callback.handler" -runtime $runtime -pkgBucket $bucketName -pkgObject $pkgKey -pkgSha256 $pkgSha256 -saId $saId -envVars $envVars
} catch {
    Write-Host "Deploy error: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`nDone." -ForegroundColor Green
Write-Host "Telegram function: $fnTelegramName" -ForegroundColor Cyan
Write-Host "Replicate function: $fnReplicateName" -ForegroundColor Cyan
