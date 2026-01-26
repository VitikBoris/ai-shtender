# 3. Стек технологий

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

**Примечание:** Начиная с feature-2.5 рекомендуется использовать Yandex Object Storage вместо MinIO для локальной разработки. Это обеспечивает:
- Публичный доступ к presigned URL без необходимости в ngrok для MinIO
- Близость к production-окружению
- Упрощение интеграции с реальным Replicate API
