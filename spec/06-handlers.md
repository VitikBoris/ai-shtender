# 6. Логика обработчиков

Два входа:

- **fn-handler** / `POST /webhook/telegram` — входящие Update от Telegram;
- **fn-callback** / `POST /webhook/replicate` — вебхуки от Replicate.

Требования:

- отвечать Telegram быстро (желательно < 2–3 с), иначе Telegram будет ретраить;
- быть устойчивыми к дублям (один и тот же Update / вебхук может прийти повторно);
- логировать `prediction_id`, `chat_id`, `message_id`.

---

## 6.A. fn-handler (входящие от Telegram)

**Вход:** JSON Update от Telegram (`message` / `callback_query`).

### Поддерживаемые сценарии (MVP + /menu)

#### 1) `/start`

- Отправить приветствие и краткую инструкцию.
- (Опционально) установить режим по умолчанию в `users/{chat_id}.json`.

#### 2) `/menu`

- Показать InlineKeyboard:
  - «Обработка фото» (`mode=process_photo`);
  - «Рамка» (`mode=frame`).
- При выборе кнопки: сохранить режим в `users/{chat_id}.json`, ответить подтверждением.

#### 3) CallbackQuery (нажатие кнопок меню)

- Прочитать `callback_query.data`.
- Обновить `users/{chat_id}.json`.
- Ответить `answerCallbackQuery` (чтобы Telegram убрал «часики»).

#### 4) Пользователь прислал фото (`message.photo`)

- Выбрать самое большое `photo_size` (последний элемент массива обычно максимальный).
- Скачать файл из Telegram:
  - `getFile` → получить `file_path`;
  - скачать по `https://api.telegram.org/file/bot<TOKEN>/<file_path>`.
- Проверить mime и размер (ограничения из конфига).
- Загрузить в S3: `images/input/.../{uuid}.jpg` (+ `Content-Type`).
- Получить presigned URL (GET, TTL например 1 ч).
- Определить текущий режим:
  - прочитать `users/{chat_id}.json`; если нет — дефолт `process_photo`.
- Создать prediction в Replicate:
  - `POST /predictions` с `model`/`version` и `input` (`image=presigned_url` + параметры режима);
  - `webhook = BASE_URL/webhook/replicate`;
  - `webhook_events_filter = ["completed"]`.
- Сохранить стейт:
  - `tasks/{prediction_id}.json` (`chat_id`, `user_id`, `input_s3_key`, `mode`, `created_at`, `message_id`, модель).
- Ответить пользователю: «Принял. Обрабатываю…» (`sendMessage`).

#### 5) Текст без фото

- Если ожидаем фото: подсказать «Пришлите фото».
- Иначе: показать `/menu`.

---

## 6.B. fn-callback (вебхук от Replicate)

**Вход:** JSON от Replicate (`id`, `status`, `output`, `error` и т.п.).

### Логика

1. Извлечь `prediction_id` (`id`) и `status`.
2. Загрузить `tasks/{prediction_id}.json` из S3:
   - если нет — залогировать и вернуть **200 OK** (чтобы Replicate не ретраил).
3. Проверить идемпотентность:
   - если в стейте уже `status` = `succeeded` или `failed` — вернуть 200 OK.
4. Обработать `status`:
   - **`succeeded`**:
     - из `output`: если массив — первый URL; если строка — использовать её;
     - (опционально) скачать output и сохранить в `images/output/.../{prediction_id}.jpg`;
     - отправить в Telegram: `sendPhoto` (по URL или по загруженному файлу).
   - **`failed`**:
     - отправить `sendMessage` с текстом ошибки (без технических секретов).
   - прочие (`processing`, `canceled`) — лог и 200 OK.
5. Обновить `tasks/{prediction_id}.json`:
   - `status`, `updated_at`, `result.output_url` или `error.message`.
6. (Опционально) удалить `tasks/{prediction_id}.json` после успеха или положиться на Lifecycle.

---

## 6.C. Retry и таймауты

- **Telegram API:** таймаут 5–10 с, 2–3 ретрая на сетевые ошибки / 429 с backoff.
- **S3:** ретрай на временные ошибки.
- **Replicate:** таймаут на `POST /predictions`; при недоступности — сообщить пользователю и не создавать `tasks/`.

---

## 6.D. Безопасность (кратко)

- **Telegram webhook:** при необходимости — проверка IP или secret в path/заголовке.
- **Replicate webhook:** желательно секрет (query-параметр или заголовок) и проверка на входе.
