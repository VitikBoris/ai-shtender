"""
Генерация штендера: детекция лица на фото, вставка в шаблон, экспорт в PDF.
Если лицо не найдено — исключение FaceNotFoundError, fallback по центру не используется.
"""
import io
import logging
from typing import Optional, Tuple

import cv2
import httpx
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class FaceNotFoundError(Exception):
    """Лицо на фото не обнаружено. Штендер не создаётся."""

    pass


# Прямоугольник под фото на шаблоне в пикселях (x, y, width, height).
# Замерено по assets/shtender_template.png: левый верх (138, 205), правый низ (1061, 1335).
TEMPLATE_PHOTO_RECT_PX = (138, 205, 923, 1130)
FACE_CROP_PADDING = 0.4


def _load_photo(photo_source: str) -> Image.Image:
    """Загрузить фото из пути к файлу или по URL. Возвращает PIL Image в RGB."""
    if photo_source.strip().lower().startswith(("http://", "https://")):
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(photo_source)
            resp.raise_for_status()
            data = resp.content
        img = Image.open(io.BytesIO(data)).convert("RGB")
    else:
        img = Image.open(photo_source).convert("RGB")
    return img


def _detect_face(image: Image.Image) -> Optional[Tuple[int, int, int, int]]:
    """
    Найти одно лицо на изображении (самое большое по площади).
    Возвращает (x, y, w, h) в пикселях или None.
    """
    gray = np.array(image.convert("L"))
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
    )
    if len(faces) == 0:
        return None
    areas = [w * h for (_, _, w, h) in faces]
    i = int(np.argmax(areas))
    x, y, w, h = faces[i]
    return (int(x), int(y), int(w), int(h))


def _crop_around_face(
    image: Image.Image,
    bbox: Tuple[int, int, int, int],
    padding_frac: float = FACE_CROP_PADDING,
) -> Image.Image:
    """Обрезать область вокруг лица с отступами. bbox = (x, y, w, h)."""
    x, y, w, h = bbox
    W, H = image.size
    pad_w = max(1, int(w * padding_frac))
    pad_h = max(1, int(h * padding_frac))
    x1 = max(0, x - pad_w)
    y1 = max(0, y - pad_h)
    x2 = min(W, x + w + pad_w)
    y2 = min(H, y + h + pad_h)
    return image.crop((x1, y1, x2, y2))


def _resize_fill(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Масштабировать и обрезать по центру так, чтобы заполнить target_w x target_h."""
    iw, ih = image.size
    target_ratio = target_w / target_h
    current_ratio = iw / ih
    if current_ratio > target_ratio:
        new_w = int(ih * target_ratio)
        left = (iw - new_w) // 2
        cropped = image.crop((left, 0, left + new_w, ih))
    else:
        new_h = int(iw / target_ratio)
        top = (ih - new_h) // 2
        cropped = image.crop((0, top, iw, top + new_h))
    return cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)


def _get_template_photo_rect(template: Image.Image) -> Tuple[int, int, int, int]:
    """Вернуть (x, y, width, height) прямоугольника под фото на шаблоне (в пикселях)."""
    return TEMPLATE_PHOTO_RECT_PX


def build_shtender_pdf(
    template_path: str,
    photo_source: str,
    output_path: Optional[str] = None,
) -> bytes:
    """
    Собрать штендер: загрузить фото, найти лицо, вставить в шаблон, экспорт в PDF.

    Если лицо на фото не найдено, выбрасывается FaceNotFoundError — штендер не создаётся.

    Args:
        template_path: Путь к PNG-шаблону.
        photo_source: Путь к файлу (jpg/png) или URL фото.
        output_path: Если задан — дополнительно записать PDF в файл.

    Returns:
        bytes PDF для отправки в Telegram или сохранения.

    Raises:
        FaceNotFoundError: На фото не обнаружено лицо.
    """
    template = Image.open(template_path).convert("RGB")
    rect_x, rect_y, rect_w, rect_h = _get_template_photo_rect(template)

    photo = _load_photo(photo_source)
    bbox = _detect_face(photo)

    if bbox is None:
        logger.warning("Лицо на фото не найдено")
        raise FaceNotFoundError("На фото не обнаружено лицо. Отправьте фото, где чётко видно лицо.")

    photo_crop = _crop_around_face(photo, bbox)
    logger.info("Лицо найдено, кадрирование по лицу")

    photo_resized = _resize_fill(photo_crop, rect_w, rect_h)
    template.paste(photo_resized, (rect_x, rect_y))

    buf = io.BytesIO()
    template.save(buf, format="PDF", resolution=100.0)
    pdf_bytes = buf.getvalue()

    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        logger.info("PDF записан: %s", output_path)

    return pdf_bytes
