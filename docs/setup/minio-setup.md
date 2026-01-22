# Настройка MinIO

## Автоматическая инициализация

Бакет создается автоматически при первом запуске приложения через `s3_storage.get_s3_client()`.

Также можно запустить скрипт вручную:

```bash
# Windows (PowerShell)
python scripts/init_minio.py

# Linux/Mac
bash scripts/init_minio.sh
```

## Ручная настройка через консоль MinIO

1. Запустить MinIO через docker-compose:
   ```bash
   docker-compose up minio
   ```

2. Открыть консоль MinIO: http://localhost:9001

3. Войти с учетными данными:
   - Username: `minioadmin`
   - Password: `minioadmin`

4. Создать бакет:
   - Нажать "Create Bucket"
   - Имя бакета: `my-bot-bucket` (или значение из `S3_BUCKET` в `.env`)
   - Нажать "Create Bucket"

## Структура папок

Бакет будет автоматически содержать следующие префиксы (папки):

- `images/input/` - исходные фото пользователей
- `images/output/` - результаты обработки (опционально)
- `tasks/` - JSON-файлы с состоянием задач

## Lifecycle Policy (опционально)

Для автоматической очистки старых файлов можно настроить Lifecycle Policy в консоли MinIO:

1. Открыть консоль MinIO
2. Выбрать бакет
3. Перейти в "Lifecycle"
4. Добавить правила:
   - `tasks/` - удалять через 2-3 дня
   - `images/input/` - удалять через 14 дней
   - `images/output/` - удалять через 14 дней
