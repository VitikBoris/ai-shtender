# Пункт 2.5: Интеграция S3 с Yandex Object Storage (удаление локального MinIO)

План: [feature-plan.md](feature-plan.md)

**Статус:** ✅ Реализовано  
**Коммит:** [Реализация feature 2.5: интеграция Yandex Object Storage](https://github.com/VitikBoris/ai-shtender/commit/)

## Цель

Перенести хранилище с локального MinIO на Yandex Object Storage для обеспечения публичного доступа к presigned URL, необходимого для работы с реальным Replicate API.

## Задачи

1. **Установка и настройка Yandex Cloud CLI**

   - Выполнить инструкции из [docs/setup/yc-cli-setup.md](../docs/setup/yc-cli-setup.md) ([GitHub](https://github.com/VitikBoris/ai-shtender/blob/master/docs/setup/yc-cli-setup.md))
   - Убедиться, что CLI настроен и работает: `yc config list`

2. **Создание бакета в Yandex Object Storage через CLI**

   - **Вариант 1: Использовать PowerShell скрипт (Windows, рекомендуется):**
     ```powershell
     cd scripts\powershell
     .\init-yandex-s3.ps1 -BucketName "ai-shtender-bucket" -FolderId "<your-folder-id>"
     ```
     Скрипт автоматически создаст бакет и применит lifecycle policy, если файл `scripts/powershell/lifecycle.json` существует.
     - Скрипт: [scripts/powershell/init-yandex-s3.ps1](https://github.com/VitikBoris/ai-shtender/blob/master/scripts/powershell/init-yandex-s3.ps1)
     - Lifecycle config: [scripts/powershell/lifecycle.json](https://github.com/VitikBoris/ai-shtender/blob/master/scripts/powershell/lifecycle.json)
   
   - **Вариант 2: Создать бакет вручную:**
     ```bash
     yc storage bucket create \
       --name ai-shtender-bucket \
       --folder-id <your-folder-id>
     ```
     Где `ai-shtender-bucket` - имя бакета (должно быть уникальным глобально), `<your-folder-id>` - ID каталога (можно получить через `yc resource-manager folder list`)
   
   - **Настроить lifecycle policy для автоматической очистки:**
     
     Создать файл `lifecycle.json`:
     ```json
     {
       "rules": [
         {
           "id": "delete-tasks-after-1-day",
           "enabled": true,
           "filter": {
             "prefix": "tasks/"
           },
           "expiration": {
             "days": 1
           }
         },
         {
           "id": "delete-input-images-after-14-days",
           "enabled": true,
           "filter": {
             "prefix": "images/input/"
           },
           "expiration": {
             "days": 14
           }
         },
         {
           "id": "delete-output-images-after-14-days",
           "enabled": true,
           "filter": {
             "prefix": "images/output/"
           },
           "expiration": {
             "days": 14
           }
         }
       ]
     }
     ```
     
     Применить lifecycle policy:
     ```bash
     yc storage bucket update \
       --name ai-shtender-bucket \
       --lifecycle-rules-from-file scripts/powershell/lifecycle.json
     ```
   
   - **Настроить публичный доступ для presigned URL (опционально, для тестирования):**
     ```bash
     # Установить публичный доступ на чтение (опционально)
     yc storage bucket update \
       --name ai-shtender-bucket \
       --public-read
     ```
     **Примечание:** Для presigned URL публичный доступ не обязателен, так как presigned URL предоставляет временный доступ даже к приватным объектам.

3. **Создание сервисного аккаунта и получение ключей доступа**

   - Создать сервисный аккаунт с ролью `storage.editor`
   - Создать статический ключ доступа (Access Key ID и Secret Access Key)
   - Сохранить ключи в безопасном месте (позже добавить в `.env`)

4. **Обновление конфигурации приложения**

   - Обновить `.env`:
     ```env
     S3_ENDPOINT_URL=https://storage.yandexcloud.net
     S3_BUCKET=your-bucket-name
     AWS_ACCESS_KEY_ID=your-access-key-id
     AWS_SECRET_ACCESS_KEY=your-secret-access-key
     S3_FORCE_PATH_STYLE=false
     S3_USE_SSL=true
     ```
   - Проверить, что код в `src/services/s3_storage.py` корректно работает с новыми настройками ([GitHub](https://github.com/VitikBoris/ai-shtender/blob/master/src/services/s3_storage.py))

5. **Удаление/отключение локального MinIO**

   - Остановить MinIO в `docker-compose.yml`:
     - Закомментировать сервис `minio` и связанные volumes ([GitHub](https://github.com/VitikBoris/ai-shtender/blob/master/docker-compose.yml))
     - Удалить зависимости от MinIO в других сервисах (если есть)
   - Удалить или переименовать скрипты инициализации:
     - `scripts/init_minio.py` (удален)
     - `scripts/init_minio.sh` (удален)
   - Обновить документацию:
     - В `docs/setup/minio-setup.md` добавлена пометка об устаревании ([GitHub](https://github.com/VitikBoris/ai-shtender/blob/master/docs/setup/minio-setup.md))
     - Создана новая документация `docs/setup/yandex-s3-setup.md` с инструкциями по настройке Yandex Object Storage ([GitHub](https://github.com/VitikBoris/ai-shtender/blob/master/docs/setup/yandex-s3-setup.md))

6. **Проверка работы**

   - Запустить приложение и проверить создание бакета (если бакет не существует, он создастся автоматически через `s3_storage.get_s3_client()`)
   - Проверить генерацию presigned URL:
     - URL должен иметь формат `https://storage.yandexcloud.net/bucket/key?...`
     - URL должен быть доступен из интернета (проверить через браузер или `curl`)
   - Протестировать загрузку и скачивание файлов через S3
   - Проверить сохранение и загрузку состояния задач (`tasks/{prediction_id}.json`)

## Файлы

- [`scripts/powershell/lifecycle.json`](https://github.com/VitikBoris/ai-shtender/blob/master/scripts/powershell/lifecycle.json) - конфигурация lifecycle policy для бакета
- `.env` - обновлены настройки S3 для Yandex Object Storage (пример: [`scripts/powershell/yc.env.example`](https://github.com/VitikBoris/ai-shtender/blob/master/scripts/powershell/yc.env.example))
- [`docker-compose.yml`](https://github.com/VitikBoris/ai-shtender/blob/master/docker-compose.yml) - отключен сервис `minio`
- [`scripts/powershell/init-yandex-s3.ps1`](https://github.com/VitikBoris/ai-shtender/blob/master/scripts/powershell/init-yandex-s3.ps1) - PowerShell скрипт для создания бакета
- [`docs/setup/yandex-s3-setup.md`](https://github.com/VitikBoris/ai-shtender/blob/master/docs/setup/yandex-s3-setup.md) - новая документация
- [`docs/setup/yc-cli-setup.md`](https://github.com/VitikBoris/ai-shtender/blob/master/docs/setup/yc-cli-setup.md) - инструкции по установке Yandex Cloud CLI
- [`docs/setup/minio-setup.md`](https://github.com/VitikBoris/ai-shtender/blob/master/docs/setup/minio-setup.md) - помечен как устаревшее
- [`src/services/s3_storage.py`](https://github.com/VitikBoris/ai-shtender/blob/master/src/services/s3_storage.py) - обновлен для работы с Yandex Object Storage

## Преимущества

- Presigned URL доступен из интернета без необходимости в ngrok для MinIO
- Близко к production-окружению (используется тот же Object Storage, что и в feature-04)
- Упрощает интеграцию с реальным Replicate API (feature-03)
- Автоматическая очистка старых файлов через lifecycle policy

## Стоимость

- Yandex Object Storage: ~0.01₽ за GB в месяц
- Первые 10 GB бесплатно (в рамках бесплатного периода Yandex Cloud)
- Для тестирования и разработки расходы минимальны

## Связанные фичи

- Предшествует: [feature-03-real-replicate.md](feature-03-real-replicate.md)
- Подготавливает инфраструктуру для: [feature-04-yandex-cloud.md](feature-04-yandex-cloud.md)
