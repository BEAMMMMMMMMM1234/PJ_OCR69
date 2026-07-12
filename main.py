from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from core.ocr_pipeline import OCRPipeline
from core.final_output_formatter import FinalOutputFormatter
from core.production_output import (
    RUNTIME_LOGS_DIR,
    RUNTIME_OUTPUTS_DIR,
    RUNTIME_REPORTS_DIR,
    RUNTIME_SUMMARY_PATH,
    build_production_output,
    build_report_entry,
    build_summary_report,
    ensure_runtime_dirs,
    setup_logger,
    write_latest_result,
    write_json,
)

ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}
FINAL_OUTPUT_FORMATTER = FinalOutputFormatter()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run OCR pipeline on a single image or a folder of images."
    )
    parser.add_argument(
        "image_path",
        help="Path to an image or folder, e.g. evaluation/appointment/images/A01.jpg or evaluation/appointment/images/",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Print and save the clean production JSON output only.",
    )
    return parser


def _failed_result(image_path: str, error: str) -> dict[str, object]:
    final_output = FINAL_OUTPUT_FORMATTER.format("failed", "Unknown", {}, error)
    return {
        "status": "failed",
        "document_type": "Unknown",
        "structured_data": {},
        "validated_data": {},
        "final_data": {},
        "final_output": final_output,
        "ocr_evidence": {
            "image_path": image_path,
            "raw_text": "",
            "text_regions": [],
            "regions_count": 0,
            "error": error,
        },
        "classification": {
            "document_type": "Unknown",
            "appointment_score": 0,
            "medicine_score": 0,
            "matched_appointment_keywords": [],
            "matched_medicine_keywords": [],
        },
        "error": error,
    }


def _iter_input_images(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        return sorted(
            path
            for path in input_path.rglob("*")
            if path.is_file()
            and path.suffix in ALLOWED_IMAGE_SUFFIXES
            and "visual_dashboard" not in path.as_posix()
            and "visual_report" not in path.as_posix()
            and "runtime/" not in path.as_posix()
            and "/debug/" not in path.as_posix()
            and "/outputs/" not in path.as_posix()
            and "/archive/" not in path.as_posix()
        )
    return []


def _process_single(
    pipeline: OCRPipeline,
    image_path: Path,
    logger,
    production: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    started_at = time.perf_counter()
    try:
        raw_result = pipeline.run(image_path)
    except FileNotFoundError as exc:
        raw_result = _failed_result(str(image_path), str(exc))
    except Exception as exc:
        raw_result = _failed_result(str(image_path), str(exc))

    processing_time = time.perf_counter() - started_at
    production_output = raw_result.get("final_output") or build_production_output(raw_result)
    report_entry = build_report_entry(image_path.name, raw_result, processing_time)

    write_latest_result(production_output)
    if production:
        report_path = RUNTIME_REPORTS_DIR / f"{image_path.stem}_report.json"
        write_json(report_path, report_entry)
    logger.info(
        "processed %s | status=%s | document_type=%s | processing_time=%.2fs",
        image_path,
        production_output["status"],
        production_output["document_type"],
        processing_time,
    )

    return raw_result, production_output, report_entry


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    ensure_runtime_dirs()
    logger = setup_logger(RUNTIME_LOGS_DIR / "runtime.log")
    input_path = Path(args.image_path)
    images = _iter_input_images(input_path)

    if not images:
        error = f"ไม่พบไฟล์หรือโฟลเดอร์ที่ระบุ: {input_path}"
        result = _failed_result(str(input_path), error)
        production_output = result.get("final_output") or build_production_output(result)
        report_entry = build_report_entry(input_path.name, result, 0.0)
        write_latest_result(production_output)
        if args.production:
            write_json(RUNTIME_REPORTS_DIR / "result_report.json", report_entry)
            summary = build_summary_report([report_entry])
            write_json(RUNTIME_SUMMARY_PATH, summary)
        logger.error(error)
        print(
            json.dumps(
                production_output if args.production else result,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    report_entries: list[dict[str, Any]] = []
    last_raw_result: dict[str, Any] | None = None
    pipeline = OCRPipeline()
    for image_path in images:
        raw_result, production_output, report_entry = _process_single(
            pipeline,
            image_path,
            logger,
            production=args.production,
        )
        last_raw_result = raw_result
        report_entries.append(report_entry)

    summary = build_summary_report(report_entries)
    if args.production:
        write_json(RUNTIME_SUMMARY_PATH, summary)

    if input_path.is_file():
        if args.production:
            final_output = json.loads((RUNTIME_OUTPUTS_DIR / "result.json").read_text(encoding="utf-8"))
            print(json.dumps(final_output, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(last_raw_result or {}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
