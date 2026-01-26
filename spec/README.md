# Спецификация: Telegram Bot (S3-as-DB)

Спецификация разбита на отдельные файлы по темам. Порядок чтения — по номерам.

| Файл | Содержание |
|------|------------|
| [01-overview.md](01-overview.md) | Обзор проекта, концепция S3-as-DB, цели |
| [02-architecture.md](02-architecture.md) | Архитектура: диаграмма, поток данных (YC и локальный) |
| [03-tech-stack.md](03-tech-stack.md) | Стек: Yandex Cloud и локально (FastAPI, MinIO) |
| [04-s3-data.md](04-s3-data.md) | S3: images/, tasks/, users/, JSON, Lifecycle, идемпотентность |
| [05-api-endpoints.md](05-api-endpoints.md) | Эндпоинты, маршрутизация |
| [06-handlers.md](06-handlers.md) | Логика fn-handler и fn-callback, /menu, retry, безопасность |
| [07-local-dev.md](07-local-dev.md) | Локальная разработка: Docker, MinIO, ngrok, структура кода |
| [08-configuration.md](08-configuration.md) | Переменные окружения, лимиты, MinIO/YC |
| [09-prompts.md](09-prompts.md) | Промпты для ИИ-разработчика |

## Гайды по установке

Все гайды по установке и настройке инструментов находятся в [docs/setup/](../docs/setup/):

- [Установка Docker и Docker Compose](../docs/setup/docker-compose-install.md)
- [Настройка MinIO](../docs/setup/minio-setup.md) (устарело, см. feature-2.5)
- [Настройка ngrok](../docs/setup/ngrok-setup.md)
- [Настройка Yandex Cloud CLI](../docs/setup/yc-cli-setup.md)

---
*Источники: docs/specification.md, docs/logicsinYandexCloud.md, docs/final_spec.md*
