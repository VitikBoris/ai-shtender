# Гайды по установке и настройке

Эта папка содержит гайды по установке и настройке всех необходимых инструментов для работы с проектом.

## Содержание

- [Установка Docker и Docker Compose](docker-compose-install.md) - подробная инструкция по установке Docker и Docker Compose для Windows, Linux и macOS
- [Настройка MinIO](minio-setup.md) - настройка локального S3-эмулятора MinIO
- [Настройка ngrok](ngrok-setup.md) - настройка туннелирования для локальной разработки
- [Настройка Yandex Cloud CLI](yc-cli-setup.md) - установка и настройка YC CLI для работы с Yandex Cloud

## Быстрая проверка

После установки всех инструментов проверьте, что все работает:

```bash
# Проверить Docker
docker --version

# Проверить Docker Compose
docker compose version

# Проверить Python (для локального запуска)
python --version

# Проверить ngrok (если установлен)
ngrok version

# Проверить YC CLI (если установлен)
yc version
```

## Порядок установки

1. **Docker и Docker Compose** - [гайд по установке](docker-compose-install.md)
2. **MinIO** - настраивается автоматически через docker-compose, но можно настроить вручную - [гайд по настройке](minio-setup.md)
3. **ngrok** - необходим для локальной разработки с webhook-ами - [гайд по настройке](ngrok-setup.md)
4. **Yandex Cloud CLI** - необходим для работы с Yandex Object Storage и Cloud Functions - [гайд по настройке](yc-cli-setup.md)

## Следующие шаги

После установки всех инструментов:

1. Перейти к [QUICKSTART.md](../../QUICKSTART.md) для быстрого старта проекта
2. Или следовать инструкциям в [README_FEATURE02.md](../../README_FEATURE02.md)
3. Изучить [спецификацию проекта](../../spec/)

## Полезные команды

- **Перезапуск бота без остановки всего Docker**: см. раздел в [QUICKSTART.md](../../QUICKSTART.md#перезапуск-бота-без-остановки-всего-docker)
