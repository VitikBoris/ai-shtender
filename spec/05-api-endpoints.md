# 5. API и эндпоинты

## API Gateway (openapi.yaml)

| Метод | Путь                  | Интеграция   |
|-------|------------------------|--------------|
| POST  | `/webhook/telegram`    | fn-handler   |
| POST  | `/webhook/replicate`   | fn-callback  |

## Локально (FastAPI)

Те же пути — роуты в одном приложении:

- `POST /webhook/telegram` — входящие Update от Telegram.
- `POST /webhook/replicate` — вебхук с результатом от Replicate.
