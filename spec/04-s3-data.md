# 4. Архитектура данных (S3-as-DB)

Бакет: из `S3_BUCKET` (например, `ai-shtender-bucket`).

Цели:

- хранить входные/выходные изображения;
- хранить «стейт» задач без базы данных;
- обеспечить безопасный доступ Replicate к входным данным через presigned URL;
- обеспечить автоочистку мусора (lifecycle).

---

## 4.1. Префиксы (папки) и назначение

| Путь | Назначение | Формат ключей |
|------|------------|---------------|
| `images/input/` | Исходные фото пользователя | `images/input/{yyyy}/{mm}/{dd}/{uuid}.jpg` |
| `images/output/` | Результаты обработки (если сохраняем у себя) | `images/output/{yyyy}/{mm}/{dd}/{prediction_id}.jpg` |
| `tasks/` | JSON состояния задач (**замена БД**) | `tasks/{prediction_id}.json` |
| `users/` (опционально) | Зарезервировано под будущее состояние пользователя | `users/{chat_id}.json` |

---

## 4.2. Ограничения и требования к объектам

- Разрешённые типы входных изображений: `image/jpeg`, `image/png`
- Максимальный размер входного файла: **10 MB** (значение из `MAX_IMAGE_MB`, проверять до загрузки)
- `Content-Type` при загрузке в S3: `image/jpeg` / `image/png` для картинок, `application/json; charset=utf-8` для JSON

---

## 4.3. Формат `tasks/{prediction_id}.json`

Минимальный (MVP):

```json
{
  "prediction_id": "abc123",
  "chat_id": 123456789,
  "user_id": 111222333,
  "input_s3_key": "images/input/2026/01/21/0c0f...uuid.jpg",
  "mode": "process_photo",
  "created_at": "2026-01-21T12:34:56Z"
}
```

Рекомендуемый расширенный (отладка, надёжность):

```json
{
  "prediction_id": "abc123",
  "chat_id": 123456789,
  "user_id": 111222333,
  "mode": "process_photo",
  "telegram": {
    "file_id": "AgACAgIA...",
    "message_id": 42
  },
  "input": {
    "s3_key": "images/input/2026/01/21/0c0f...uuid.jpg",
    "mime": "image/jpeg",
    "size_bytes": 345678
  },
  "replicate": {
    "model": "owner/model",
    "version": "model_version_hash",
    "webhook_events_filter": ["completed"]
  },
  "status": "queued",
  "created_at": "2026-01-21T12:34:56Z",
  "updated_at": "2026-01-21T12:34:56Z",
  "result": {
    "output_url": null,
    "output_s3_key": null
  },
  "error": {
    "code": null,
    "message": null
  }
}
```

### Статусы

`queued` → `processing` → `succeeded` / `failed`

---

## 4.4. Lifecycle Policy (автоочистка)

| Префикс | Рекомендуемый срок |
|---------|--------------------|
| `tasks/` | 1–3 дня |
| `images/input/` | 7–30 дней |
| `images/output/` | 7–30 дней |

Пример (концепт, Yandex Object Storage / MinIO):

```xml
<LifecycleConfiguration>
  <Rule>
    <ID>ExpireTasks</ID>
    <Filter><Prefix>tasks/</Prefix></Filter>
    <Status>Enabled</Status>
    <Expiration><Days>2</Days></Expiration>
  </Rule>
  <Rule>
    <ID>ExpireInputImages</ID>
    <Filter><Prefix>images/input/</Prefix></Filter>
    <Status>Enabled</Status>
    <Expiration><Days>14</Days></Expiration>
  </Rule>
  <Rule>
    <ID>ExpireOutputImages</ID>
    <Filter><Prefix>images/output/</Prefix></Filter>
    <Status>Enabled</Status>
    <Expiration><Days>14</Days></Expiration>
  </Rule>
</LifecycleConfiguration>
```

---

## 4.5. Идемпотентность и гонки

- Вебхук от Replicate может прийти повторно.
- `fn-callback` должен быть идемпотентным:
  - если `tasks/{prediction_id}.json` уже в статусе `succeeded` или `failed` — вернуть 200 OK;
  - (опционально) обновлять `status` и `updated_at` через перезапись объекта.
