"""
Entrypoint для Yandex Cloud Functions: обработчик Telegram webhook.

Важно: в Cloud Functions нежелательно делать "fire-and-forget" через create_task()
после возврата ответа. Поэтому здесь обработка выполняется в рамках одного вызова.
"""

import asyncio
import base64
import json
import logging
import os
import sys
from typing import Any, Dict

# В Yandex Cloud Functions код может распаковываться не рядом с runtime,
# поэтому `src/` не всегда находится через стандартный sys.path.
# Добавляем наиболее вероятные директории с кодом.
_CANDIDATE_PATHS = [
    os.path.dirname(__file__),
    os.getcwd(),
    "/function/code",
    "/function",
]
for _p in _CANDIDATE_PATHS:
    try:
        if _p and _p not in sys.path and os.path.isdir(_p):
            sys.path.insert(0, _p)
    except Exception:
        # Никаких исключений на этапе импорта — иначе API Gateway вернет 502.
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _parse_event_body(event: Dict[str, Any]) -> Any:
    body = event.get("body")
    if body is None:
        return {}

    if isinstance(body, (dict, list)):
        return body

    if not isinstance(body, str):
        return {}

    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    body = body.strip()
    if not body:
        return {}
    return json.loads(body)


def handler(event, context):  # noqa: ARG001
    try:
        # Импортируем бизнес-логику лениво (внутри handler),
        # чтобы исключить 502 при проблемах с PYTHONPATH на cold start.
        try:
            from src.handlers.telegram_processor import process_telegram_update  # noqa: WPS433
        except Exception as import_err:
            logger.exception(
                "Import error (src). __file__=%s cwd=%s sys.path[0:5]=%s err=%s",
                __file__,
                os.getcwd(),
                sys.path[:5],
                import_err,
            )
            try:
                here = os.path.dirname(__file__)
                logger.info("Listdir(__file__ dir=%s): %s", here, os.listdir(here))
            except Exception:
                pass
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": str(import_err)}, ensure_ascii=False),
            }

        update_data = _parse_event_body(event or {})
        logger.info("Telegram webhook received: update_id=%s", update_data.get("update_id"))

        asyncio.run(process_telegram_update(update_data))

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": True}, ensure_ascii=False),
        }
    except Exception as e:
        logger.exception("Telegram webhook error: %s", e)
        # Возвращаем 200, чтобы Telegram не ретраил бесконечно
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
        }

