# Пункт 4.5: Генерация штендера (лицо в шаблоне → PDF)

План: [feature-plan.md](feature-plan.md)

**Статус:** ✅ Реализовано  
**Коммит:** —

## Цель

По шаблону (`assets/shtender_template.png`) и фото (файл или URL, в т.ч. результат Replicate) получать PDF штендера. В рамку шаблона попадает **лицо**: детекция лица → кадрирование вокруг лица → вставка в шаблон → экспорт в PDF. Если лицо не найдено — штендер не создаётся, пользователю сообщается об этом.

## Задачи

1. **Зависимости**
   - В [requirements.txt](../requirements.txt): `opencv-python-headless` для детекции лиц, Pillow уже есть.

2. **Конфигурация**
   - В [src/config.py](../src/config.py): `SHTENDER_TEMPLATE_PATH` (по умолчанию `assets/shtender_template.png`).

3. **Модуль генерации штендера** ([src/services/shtender.py](../src/services/shtender.py))
   - Загрузка фото: путь к файлу или URL (в т.ч. `output` от Replicate).
   - Детекция лица (OpenCV Haar cascade), выбор одного лица (наибольшее по площади).
   - Кадрирование вокруг лица с отступами; вставка в прямоугольник шаблона; экспорт в PDF.
   - При отсутствии лица — исключение `FaceNotFoundError` (без fallback по центру).

4. **Интеграция в вебхук Replicate** ([src/domain/logic.py](../src/domain/logic.py))
   - После успешного результата Replicate: при наличии шаблона вызывается `build_shtender_pdf`; PDF отправляется пользователю через `send_document_bytes`. При `FaceNotFoundError` — сообщение пользователю «На фото не обнаружено лицо…».

5. **CLI** ([scripts/shtender_cli.py](../scripts/shtender_cli.py))
   - Аргументы: `--template`, `--photo`, `--output`. При отсутствии лица — вывод в stderr и код выхода 1.

## Ключевые файлы

| Файл | Назначение |
|------|------------|
| [requirements.txt](../requirements.txt) | opencv-python-headless |
| [src/config.py](../src/config.py) | SHTENDER_TEMPLATE_PATH |
| [src/services/shtender.py](../src/services/shtender.py) | Детекция лица, композит, PDF, FaceNotFoundError |
| [src/domain/logic.py](../src/domain/logic.py) | Вызов штендера в process_replicate_webhook, обработка FaceNotFoundError |
| [src/services/telegram_api.py](../src/services/telegram_api.py) | send_document_bytes для PDF |
| [scripts/shtender_cli.py](../scripts/shtender_cli.py) | CLI для ручной генерации PDF |

## Связанные документы

- [feature-plan.md](feature-plan.md) — план фич
- [feature-04-yandex-cloud.md](feature-04-yandex-cloud.md) — пункт 4 (деплой в YC)
- [spec/06-handlers.md](../spec/06-handlers.md) — логика fn-callback (штендер после Replicate)
