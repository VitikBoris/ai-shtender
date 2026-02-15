# Конфигурация Yandex Cloud для скриптов PowerShell
# Скопируйте этот файл в yc.env и заполните своими значениями
# 
# ВАЖНО: Не коммитьте yc.env в git. Секреты храните в yc.secrets.env!

# ID каталога (folder-id) в Yandex Cloud
# Получить список каталогов: yc resource-manager folder list
YC_FOLDER_ID=

# Имя бакета Object Storage (должно быть уникальным глобально)
YC_BUCKET_NAME=ai-shtender-bucket

# Имя сервисного аккаунта (будет создан, если не существует)
YC_SERVICE_ACCOUNT_NAME=ai-shtender-sa

# Имена Cloud Functions (будут созданы, если не существуют)
YC_FUNCTION_TELEGRAM_NAME=fn-handler
YC_FUNCTION_REPLICATE_NAME=fn-callback

# Имя API Gateway (будет создан, если не существует)
YC_APIGW_NAME=ai-shtender-gw

# Runtime для Cloud Functions (например: python39, python311)
YC_RUNTIME=python311

# ID облака (опционально, обычно определяется автоматически)
# YC_CLOUD_ID=b1g...

# ID сервисного аккаунта (опционально, для автоматизации)
# YC_SERVICE_ACCOUNT_ID=aje...
