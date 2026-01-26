# 2. Архитектура

## Поток данных (Yandex Cloud)

```mermaid
graph TD
    User((Пользователь)) <--> TG[Telegram Bot API]
    
    subgraph "Yandex Cloud"
        AGW[API Gateway]
        HandleFn[Cloud Function: Handler]
        ObjectStorage[(Object Storage)]
        ResultFn[Cloud Function: Callback]
    end
    
    subgraph "External AI"
        Replicate[Replicate API]
    end

    User -- "Отправляет фото" --> TG
    TG -- "Webhook (Update)" --> AGW
    AGW --> HandleFn
    
    HandleFn -- "1. Сохраняет фото (images/)" --> ObjectStorage
    HandleFn -- "2. POST /predictions" --> Replicate
    HandleFn -- "3. Создает JSON-стейт (tasks/)" --> ObjectStorage
    HandleFn -- "4. Ответ 'Обрабатываю...'" --> TG
    
    Replicate -. "Генерация" .-> Replicate
    
    Replicate -- "5. POST Webhook (Result)" --> AGW
    AGW --> ResultFn
    ResultFn -- "6. Читает JSON-стейт" --> ObjectStorage
    ResultFn -- "7. Отправляет результат" --> TG
    TG -- "Готовое изображение" --> User
```

## Локальный эквивалент

| Yandex Cloud            | Локально                         |
|-------------------------|----------------------------------|
| Cloud Function: Handler | FastAPI, роут `/webhook/telegram` |
| Cloud Function: Callback| FastAPI, роут `/webhook/replicate` |
| Object Storage          | Yandex Object Storage (рекомендуется) или MinIO (S3-совместимый) |
| API Gateway             | FastAPI (прямые HTTP-роуты)      |

**Примечание:** Начиная с feature-2.5 рекомендуется использовать Yandex Object Storage для локальной разработки вместо MinIO. Это обеспечивает публичный доступ к presigned URL и близость к production-окружению.
