Техническая спецификация: Serverless Telegram Bot (YC + Replicate + S3-as-DB)
1. Обзор проекта
Разработка бэкенда для Telegram-бота, обрабатывающего изображения с помощью нейросетей (Replicate). Архитектура полностью бессерверная (Serverless) на базе Yandex Cloud. Ключевая особенность: Отказ от баз данных (SQL/NoSQL) в пользу использования Object Storage (S3) для хранения контекста задач (state management).

2. Стек технологий
Cloud Provider: Yandex Cloud.

Runtime: Python 3.9+.

Infrastructure:

Cloud Functions: Бизнес-логика.

API Gateway: Маршрутизация HTTP-запросов.

Object Storage (S3): Хранение изображений И JSON-файлов состояния.

Lockbox: Хранение токенов (опционально, или через Env Vars).

External APIs:

Telegram Bot API.

Replicate API.

3. Архитектура данных (S3 Structure)
В бакете (например, my-bot-bucket) используется следующая структура папок:

images/input/

Хранение исходных фото от пользователей.

Имя файла: {uuid}.jpg

tasks/ (Замена Базе Данных)

Хранение JSON-файлов с метаданными задачи.

Имя файла: {prediction_id}.json (где prediction_id — ID задачи из Replicate).

Содержание файла:

JSON

{
  "chat_id": 123456789,
  "file_id": "AgAC...",
  "timestamp": 1700000000
}
Lifecycle Policy (Важно!):

Настроить правило в S3: Удалять объекты с префиксом tasks/ старше 1 дня. (Автоматическая очистка мусора).

4. Компоненты и логика
А. API Gateway (openapi.yaml)
Два эндпоинта:

POST /webhook/telegram -> Интеграция с функцией fn-handler.

POST /webhook/replicate -> Интеграция с функцией fn-callback.

Б. Функция 1: Обработчик входящих (fn-handler)
Вход: JSON Update от Telegram. Логика:

Парсинг: Если сообщение содержит фото, берем file_id (наилучшее качество).

Download: Скачиваем фото через Telegram getFile.

Upload to S3: Загружаем фото в images/input/{uuid}.jpg.

Presign: Генерируем временную ссылку (Presigned URL, метод GET, 1 час) на этот файл для Replicate.

Replicate Request: Делаем POST запрос к Replicate API:

input: {"image": presigned_url, ...}

webhook: https://<apigw_url>/webhook/replicate

webhook_events_filter: ["completed"]

Save State (S3):

Получаем id (prediction_id) из ответа Replicate.

Создаем файл в S3: ключ tasks/{prediction_id}.json.

Тело: json.dumps({"chat_id": telegram_chat_id}).

Response: Отправляем пользователю в TG: "Задачу принял, ожидайте".

Возвращаем 200 OK.

В. Функция 2: Прием результата (fn-callback)
Вход: JSON Webhook от Replicate. Логика:

Парсинг: Извлекаем id (prediction_id) и status из тела запроса.

Load State (S3):

Пытаемся скачать файл tasks/{prediction_id}.json из S3.

Если файла нет (редкий кейс) — логируем ошибку и выходим.

Читаем JSON, извлекаем chat_id.

Check Status:

Если status == "succeeded": Извлекаем URL готового фото (output).

Если status == "failed": Готовим текст ошибки.

Send to TG:

Используем метод sendPhoto (передаем URL от Replicate) или sendMessage (если ошибка) по адресу chat_id.

(Опционально) Cleanup: Удаляем файл tasks/{prediction_id}.json (или оставляем его умирать по Lifecycle policy).

Возвращаем 200 OK.

5. Переменные окружения (Env Vars)
TG_BOT_TOKEN: Токен бота.

REPLICATE_API_TOKEN: Токен Replicate.

S3_BUCKET: Имя бакета.

AWS_ACCESS_KEY_ID: Идентификатор ключа сервисного аккаунта YC.

AWS_SECRET_ACCESS_KEY: Секретный ключ сервисного аккаунта YC.

S3_ENDPOINT_URL: https://storage.yandexcloud.net

6. Промпт для ИИ-разработчика
Ниже готовый текст запроса, который можно отправить кодеру:

"Напиши код на Python для Yandex Cloud Functions, реализующий Telegram-бота для обработки фото через Replicate.

Архитектурные требования:

Используй библиотеку boto3 для работы с Yandex Object Storage (S3 protocol).

Не используй базы данных. Для сохранения состояния между запросом пользователя и вебхуком от Replicate используй S3: сохраняй JSON-файл по пути tasks/{prediction_id}.json, внутри которого лежит {"chat_id": 123}.

В функции-обработчике Telegram (handler.py): скачивай фото, загружай в S3, генерируй Presigned URL, создавай prediction в Replicate с указанием webhook URL, сохраняй стейт в S3.

В функции-обработчике Replicate (callback.py): читай стейт из S3 по prediction_id, отправляй готовое фото пользователю в Telegram.

Используй стандартную библиотеку requests для HTTP вызовов.

Учти обработку ошибок (try/except) и логирование."