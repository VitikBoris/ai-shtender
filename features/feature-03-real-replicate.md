# Пункт 3: Интеграция с реальным Replicate

План: [feature-plan.md](feature-plan.md)

**Статус:** ✅ Реализовано  
**README:** [`README_FEATURE03.md`](../README_FEATURE03.md)

## Цель

Заменить локальный эмулятор на реальный Replicate API, сохранив архитектуру с S3-as-DB.

## Задачи

1. **Получение токена Replicate**

   - Регистрация на Replicate, получение `REPLICATE_API_TOKEN`
   - Добавление токена в `.env`

2. **Выбор модели Replicate**

   - Определить модель для обработки изображений (например, `sczhou/codeformer` для восстановления фото)
   - Документировать параметры модели в коде

2.5. **Интеграция S3 с Yandex Object Storage**

   - Выполнить задачи из [feature-2.5-yandex-s3.md](feature-2.5-yandex-s3.md)
   - Убедиться, что presigned URL от Yandex Object Storage доступен из интернета (необходимо для Replicate)

3. **Обновление кода для работы с Replicate API**

   - В проекте это реализовано в:
     - `src/domain/logic.py` — создание prediction и сохранение состояния в S3
     - `src/services/replicate_api.py` — вызов Replicate API / Mock Replicate
     - `src/domain/logic.py` — обработка вебхука (аналог `callback.py`) и отправка результата пользователю
   - Используется endpoint `https://api.replicate.com/v1/predictions` и поле `version` (нужен `REPLICATE_MODEL_VERSION`)

4. **Обработка ошибок и edge cases**

   - Обработка таймаутов Replicate
   - Обработка ошибок API Replicate (401, 429, 500)
   - Логирование для отладки
   - Обработка случая, когда `tasks/{prediction_id}.json` не найден в S3 (редкий кейс)

5. **Проверка presigned URL для S3**

   - Убедиться, что presigned URL от Yandex Object Storage доступен из интернета (необходимо для Replicate)
   - Проверить, что URL имеет формат `https://storage.yandexcloud.net/bucket/key?...`
   - Протестировать доступность URL из браузера или через `curl`

## Файлы

- `src/config.py` (добавлен `REPLICATE_MODEL_VERSION`)
- `src/services/replicate_api.py` (real вызов + логирование HTTP ошибок)
- `src/domain/logic.py` (передача model/version + сообщения об ошибках)
- `docker-compose.yml` (`mock-replicate` сделан опциональным через профиль `mock`)
- `README.md` (инструкции mock vs real)
- `README_FEATURE03.md` (инструкции для пункта 3)

## Предварительные требования

- Выполнен [feature-2.5-yandex-s3.md](feature-2.5-yandex-s3.md) (интеграция S3 с Yandex Object Storage)

## Тестирование

- Проверка работы с реальным Replicate
- Мониторинг вебхуков от Replicate
- Проверка сохранения/загрузки состояния в S3
