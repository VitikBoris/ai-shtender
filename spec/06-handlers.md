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

### Поддерживаемые сценарии (MVP)

#### 1) `/start`

- Отправить приветствие и краткую инструкцию (в т.ч. про /menu).

#### 2) `/menu`

- Отправить сообщение с **InlineKeyboard** и двумя кнопками:
  - **Детализация** — режим обработки фото через Replicate (реставрация).
  - **Создание штендера** — режим: только детекция лица и генерация PDF-штендера (без Replicate).
  - Кнопка **« Назад»** — убрать клавиатуру (editMessageReplyMarkup с пустым `inline_keyboard`).
- При нажатии на режим: `answerCallbackQuery`, сохранить режим в S3 `users/{chat_id}.json` (поле `mode`: `restoration` или `shtender`), отправить подтверждение.
- При нажатии «Назад»: `answerCallbackQuery`, убрать кнопки у сообщения с меню.

**callback_data:** `mode=detailization` → сохранять `mode: "restoration"`; `mode=shtender` → `mode: "shtender"`; `action=back` → закрыть меню.

#### 3) Пользователь прислал фото (`message.photo`)

- Выбрать самое большое `photo_size` (последний элемент массива обычно максимальный).
- Скачать файл из Telegram:
  - `getFile` → получить `file_path`;
  - скачать по `https://api.telegram.org/file/bot<TOKEN>/<file_path>`.
- Проверить mime и размер (ограничения из конфига).
- Загрузить в S3: `images/input/.../{uuid}.jpg` (+ `Content-Type`).
- Получить presigned URL (GET, TTL например 1 ч).
- Режим обработки — из S3 `users/{chat_id}.json` (поле `mode`). Если нет — по умолчанию `restoration`. Режим `shtender`: фото не отправляется в Replicate — скачивается, строится штендер (лицо + PDF) и отправляется пользователю; при отсутствии лица — сообщение «На фото не обнаружено лицо…».
- Создать prediction в Replicate:
  - `POST /predictions` с `model`/`version` и `input` (`image=presigned_url`);
  - `webhook = BASE_URL/webhook/replicate`;
  - `webhook_events_filter = ["completed"]`.
- Сохранить стейт:
  - `tasks/{prediction_id}.json` (`chat_id`, `user_id`, `input_s3_key`, `mode`, `created_at`, `message_id`, модель).
- Ответить пользователю: «Принял. Обрабатываю…» (`sendMessage`).

#### 4) Текст без фото

- Подсказать «Пришлите фото».

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
     - отправить в Telegram: `sendPhoto` (по URL или по загруженному файлу);
     - (Feature 4.5) при наличии шаблона штендера: сгенерировать PDF (детекция лица, вставка в шаблон) и отправить `sendDocument`; если лицо не найдено — отправить сообщение пользователю, PDF не создавать.
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
