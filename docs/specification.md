

# Локальная спецификация: Telegram Bot (S3-as-DB Architecture)

## 1. Концепция локального стека

Вместо облачных функций Yandex Cloud мы будем использовать **FastAPI** — он отлично подходит для обработки вебхуков. Вместо Yandex Object Storage мы используем **MinIO** (локальный S3), который работает идентично.

## 2. Локальная инфраструктура (Docker Compose)

Для запуска всех зависимостей одной командой используйте этот `docker-compose.yaml`:

```yaml
services:
  # Эмулятор S3 (Object Storage)
  minio:
    image: minio/minio
    ports:
      - "9000:9000" # API
      - "9001:9001" # Консоль управления
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"

  # Наше приложение (FastAPI)
  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - minio

```

## 3. Файловая структура проекта (Локально)

```text
project/
├── main.py          # FastAPI приложение (объединяет handler и callback)
├── requirements.txt # boto3, fastapi, uvicorn, requests, python-dotenv
├── .env             # Конфигурация
└── docker-compose.yml

```

## 4. Конфигурация окружения (.env)

Создайте файл `.env` для локальных тестов:

```env
# API Ключи
TG_BOT_TOKEN=ваш_токен_из_BotFather
REPLICATE_API_TOKEN=ваш_токен_replicate

# Настройки S3 (Local MinIO)
S3_BUCKET=my-bot-bucket
S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin

# Публичный адрес для вебхуков (получите через ngrok)
BASE_URL=https://your-unique-id.ngrok-free.app

```

## 5. Логика работы в режиме разработки

### Этап 1: Подготовка (Tunneling)

Так как Telegram и Replicate должны «увидеть» ваш локальный сервер, используйте **ngrok**:
`ngrok http 8000`
Скопируйте полученный `https://...` адрес в переменную `BASE_URL` в `.env`.

### Этап 2: Имитация S3-as-DB

В коде используйте `boto3`. Для локального MinIO важно указать `endpoint_url`:

```python
s3 = boto3.client('s3', endpoint_url=os.getenv('S3_ENDPOINT_URL'))

```

* **Запись состояния:** `s3.put_object(Bucket=..., Key=f"tasks/{prediction_id}.json", Body=json.dumps(state))`
* **Чтение состояния:** `s3.get_object(Bucket=..., Key=f"tasks/{prediction_id}.json")`

### Этап 3: Обработка изображений

Для того чтобы Replicate смог скачать ваше фото из локального MinIO через Presigned URL, **MinIO также должен быть доступен извне**.

* *Лайфхак для тестов:* Если пробрасывать MinIO через ngrok сложно, на этапе локальной разработки можно загружать фото не в S3, а на любой бесплатный хостинг картинок (например, ImgBB) и отдавать Replicate прямую ссылку. Но для полной симуляции YC лучше использовать S3-путь.

---

## 6. План разработки (Step-by-Step)

1. **Запуск MinIO:** Выполните `docker-compose up minio`. Зайдите на `localhost:9001` и создайте бакет `my-bot-bucket`.
2. **Эндпоинт 1 (`/webhook/telegram`):** * Реализуйте прием сообщения.
* Загрузку в MinIO.
* Отправку запроса в Replicate с указанием `webhook: BASE_URL + "/webhook/replicate"`.


3. **Эндпоинт 2 (`/webhook/replicate`):**
* Прием данных.
* Поиск JSON-файла в папке `tasks/` внутри MinIO.
* Отправка результата в Telegram.


4. **Тестирование:** Отправьте фото боту и следите за логами FastAPI и появлением файлов в консоли MinIO.

## 7. Что спросить у ИИ (Промпт для кодинга)

> "Напиши локальное приложение на **FastAPI**, которое имитирует работу Serverless функций. Нужно два роута: `/webhook/telegram` и `/webhook/replicate`. Используй **boto3** для хранения состояния в S3 (локальный MinIO) по пути `tasks/{prediction_id}.json`.
> Логика:
> 1. При получении фото от TG: качаем его, кладем в S3, шлем запрос в Replicate.
> 2. При вебхуке от Replicate: достаем из S3 файл задачи, берем оттуда `chat_id` и пересылаем результат пользователю.
> 
> 
> Предусмотри, чтобы `endpoint_url` для S3 брался из конфига (для совместимости с MinIO)."
