from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.ocr_pipeline import OCRPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run YOLO detection on a single image.")
    parser.add_argument("image_path", help="Path to input image, e.g. data/test_images/A1.jpg")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        pipeline = OCRPipeline()
        result = pipeline.run(Path(args.image_path))
    except FileNotFoundError as exc:
        result = {
            "status": "failed",
            "image_path": args.image_path,
            "raw_text": "",
            "text_regions": [],
            "regions_count": 0,
            "error": str(exc),
        }
    except Exception as exc:
        result = {
            "status": "failed",
            "image_path": args.image_path,
            "raw_text": "",
            "text_regions": [],
            "regions_count": 0,
            "error": str(exc),
        }

    output_path = Path(__file__).resolve().parent / "outputs" / "result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
