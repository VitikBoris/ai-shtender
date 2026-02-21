"""
CLI для генерации штендера: шаблон + фото (файл или URL) → PDF.
При отсутствии лица на фото штендер не создаётся, выводится сообщение.
Запуск из корня проекта: python -m scripts.shtender_cli --template ... --photo ... --output ...
"""
import argparse
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.services.shtender import build_shtender_pdf, FaceNotFoundError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Собрать штендер: шаблон + фото (файл или URL) → PDF. Лицо на фото обязательно."
    )
    parser.add_argument("--template", required=True, help="Путь к PNG-шаблону штендера")
    parser.add_argument("--photo", required=True, help="Путь к файлу фото (jpg/png) или URL")
    parser.add_argument("--output", required=True, help="Путь для сохранения PDF")
    args = parser.parse_args()

    try:
        build_shtender_pdf(
            template_path=args.template,
            photo_source=args.photo,
            output_path=args.output,
        )
        print(f"Готово: {args.output}")
        return 0
    except FaceNotFoundError as e:
        print("Лицо на фото не найдено.", str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
