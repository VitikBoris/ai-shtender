# 3. Стек технологий

## Статус

- **Локально**: ✅ реализовано (FastAPI + S3-as-DB; поддерживаются real Replicate и mock-режим).
- **Yandex Cloud (Production)**: ⏳ в плане (Serverless: Cloud Functions + API Gateway).

## Yandex Cloud (Production)

| Компонент       | Технология              |
|-----------------|-------------------------|
| Cloud Provider  | Yandex Cloud            |
| Runtime         | Python 3.9+             |
| Бизнес-логика   | Cloud Functions         |
| Маршрутизация   | API Gateway             |
| Хранилище       | Object Storage (S3)     |
| Секреты         | Lockbox или Env Vars    |
| Внешние API     | Telegram Bot API, Replicate API |

## Локальная разработка

| Компонент   | Технология                                  |
|-------------|---------------------------------------------|
| HTTP-сервер | FastAPI (вместо Cloud Functions)            |
| S3          | Yandex Object Storage (рекомендуется) или MinIO (эмулятор) |
| CLI         | YC CLI (для работы с Yandex Cloud)          |
| Оркестрация | Docker Compose (опционально, только для MinIO) |
| Туннель     | ngrok (чтобы TG и Replicate видели localhost) |

### Кодировка PowerShell-скриптов

Файлы `*.ps1` в проекте должны сохраняться в кодировке **UTF-8 с BOM** (Byte Order Mark). Это обеспечивает корректное отображение кириллицы и других не-ASCII символов при запуске в Windows PowerShell. Без BOM PowerShell 5.1 может интерпретировать файл в системной кодовой странице (например, CP1251), что приводит к искажению русских комментариев и строк.

**Примечание:** Начиная с feature-2.5 рекомендуется использовать Yandex Object Storage вместо MinIO для локальной разработки. Это обеспечивает:
- Публичный доступ к presigned URL без необходимости в ngrok для MinIO
- Близость к production-окружению
- Упрощение интеграции с реальным Replicate API
