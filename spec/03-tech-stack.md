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
| S3          | MinIO (эмулятор Object Storage)             |
| Оркестрация | Docker Compose                              |
| Туннель     | ngrok (чтобы TG и Replicate видели localhost) |
