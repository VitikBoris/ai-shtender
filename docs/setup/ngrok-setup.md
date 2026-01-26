# Настройка ngrok для локальной разработки

## Зачем нужен ngrok?

Telegram Bot API и Replicate API отправляют webhook-и на ваш сервер по HTTPS. Локальный сервер (`localhost:8000`) недоступен из интернета. Ngrok создает публичный HTTPS-туннель к локальному серверу, позволяя принимать webhook-и от внешних сервисов во время локальной разработки.

## Установка ngrok

1. Скачать ngrok: https://ngrok.com/download
2. Распаковать и добавить в PATH (или использовать полный путь)

## Запуск ngrok

1. Запустить FastAPI приложение:
   ```bash
   docker-compose up app
   # или локально:
   uvicorn src.app:app --host 0.0.0.0 --port 8000
   ```

2. В отдельном терминале запустить ngrok:
   ```bash
   ngrok http 8000
   ```

3. Скопировать HTTPS URL (например: `https://abc123.ngrok-free.app`)

4. Обновить `.env`:
   ```env
   BASE_URL=https://abc123.ngrok-free.app
   ```

## Настройка Telegram Webhook

После получения URL от ngrok, настроить webhook в Telegram:

**Вариант 1: Корневой путь (рекомендуется для простоты)**
```bash
curl "https://api.telegram.org/bot8326793362:AAE2ofAP2KOGSBRW1ody2VpiSXmmx1KUK6A/setWebhook?url=https://intercessional-willow-sententiously.ngrok-free.dev"
```

**Вариант 2: С указанием пути**
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://abc123.ngrok-free.app/webhook/telegram"
```

Оба варианта работают одинаково. Приложение поддерживает оба пути:
- `POST /` - корневой путь (для совместимости)
- `POST /webhook/telegram` - явный путь

## Проверка webhook

Проверить текущий webhook:
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

Удалить webhook (вернуться к polling):
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook"
```

## Примечания

- Бесплатный ngrok дает случайный URL при каждом запуске
- Для постоянного URL нужен платный план ngrok
- Альтернативы: localtunnel, serveo, cloudflared
