from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
JSON_REPORT_PATH = REPORTS_DIR / "input_image_validation_report.json"
MD_REPORT_PATH = REPORTS_DIR / "input_image_validation_report.md"

DEFAULT_INPUT_DIRS = [
    PROJECT_ROOT / "evaluation" / "appointment" / "images",
    PROJECT_ROOT / "evaluation" / "medicine" / "images",
]

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}
SMALL_DIMENSION_THRESHOLD = 300
LARGE_DIMENSION_THRESHOLD = 4000
BLUR_THRESHOLD = 120.0
LOW_CONTRAST_STDDEV_THRESHOLD = 35.0
EXTREME_ASPECT_RATIO_THRESHOLD = 3.0


@dataclass
class ImageRecord:
    path: str
    document_type: str
    status: str
    width: int
    height: int
    file_size_bytes: int
    extension: str
    issues: list[str]
    filename: str
    file_hash: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate input images before they are imported into the evaluation dataset."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional image directories or files. Defaults to evaluation/appointment/images and evaluation/medicine/images.",
    )
    return parser


def _ensure_reports_dir() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _document_type_for_path(path: Path) -> str:
    rel = _relative(path)
    if "/appointment/" in rel:
        return "Appointment"
    if "/medicine/" in rel:
        return "MedicineLabel"
    stem = path.stem.upper()
    if stem.startswith("A"):
        return "Appointment"
    if stem.startswith("M"):
        return "MedicineLabel"
    return "Unknown"


def _iter_target_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        return sorted(
            path
            for path in input_path.rglob("*")
            if path.is_file() and path.suffix in ALLOWED_SUFFIXES and path.name != ".gitkeep"
        )
    return []


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_name_pattern(document_type: str, stem: str) -> tuple[bool, str]:
    if not stem:
        return False, "missing filename stem"

    prefix = stem[0].upper()
    digits = stem[1:]
    if document_type == "Appointment" and prefix != "A":
        return False, "filename prefix must start with A for Appointment"
    if document_type == "MedicineLabel" and prefix != "M":
        return False, "filename prefix must start with M for MedicineLabel"
    if not digits.isdigit():
        return False, "filename suffix must contain only digits"
    if len(digits) not in {2, 3}:
        return False, "filename must use 2 or 3 digits"

    number = int(digits)
    if document_type == "Appointment":
        if len(digits) == 2 and not (1 <= number <= 25):
            return False, "Appointment filename must be A01-A25"
        if len(digits) == 3 and not (1 <= number <= 100):
            return False, "Appointment filename must be A001-A100"
    elif document_type == "MedicineLabel":
        if len(digits) == 2 and not (1 <= number <= 25):
            return False, "Medicine filename must be M01-M25"
        if len(digits) == 3 and not (1 <= number <= 120):
            return False, "Medicine filename must be M001-M120"
    else:
        return False, "unknown document type for filename validation"
    return True, ""


def _evaluate_single(path: Path) -> tuple[ImageRecord, dict[str, Any]]:
    issues: list[str] = []
    document_type = _document_type_for_path(path)
    extension = path.suffix
    filename = path.name
    file_hash = ""
    width = 0
    height = 0
    file_size_bytes = 0

    if not path.exists():
        issues.append("file does not exist")
        record = ImageRecord(
            path=_relative(path),
            document_type=document_type,
            status="invalid",
            width=0,
            height=0,
            file_size_bytes=0,
            extension=extension,
            issues=issues,
            filename=filename,
            file_hash=file_hash,
        )
        return record, {}

    try:
        file_size_bytes = path.stat().st_size
    except OSError as exc:
        issues.append(f"cannot read file size: {exc}")

    if file_size_bytes == 0:
        issues.append("file size is 0 byte")

    if extension not in ALLOWED_SUFFIXES:
        issues.append(f"unsupported extension: {extension}")

    pil_ok = False
    cv_ok = False
    image_array: np.ndarray | None = None

    try:
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            pil_ok = True
    except Exception as exc:
        issues.append(f"PIL cannot read image: {exc}")

    try:
        cv_image = cv2.imread(str(path))
        if cv_image is None:
            raise ValueError("cv2.imread returned None")
        cv_ok = True
        image_array = cv_image
        if not pil_ok:
            height, width = cv_image.shape[:2]
    except Exception as exc:
        issues.append(f"OpenCV cannot read image: {exc}")

    if width <= 0 or height <= 0:
        issues.append("width or height is not greater than 0")

    if width > 0 and height > 0:
        if width < SMALL_DIMENSION_THRESHOLD or height < SMALL_DIMENSION_THRESHOLD:
            issues.append(f"warning: image is small ({width}x{height})")
        if width > LARGE_DIMENSION_THRESHOLD or height > LARGE_DIMENSION_THRESHOLD:
            issues.append(f"warning: image is very large ({width}x{height})")
        if min(width, height) > 0 and max(width, height) / min(width, height) >= EXTREME_ASPECT_RATIO_THRESHOLD:
            issues.append(f"warning: extreme aspect ratio ({width}x{height})")

    if image_array is not None:
        try:
            gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
            blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            contrast_score = float(gray.std())
            if blur_score < BLUR_THRESHOLD:
                issues.append(f"warning: blur risk (score={blur_score:.2f})")
            if contrast_score < LOW_CONTRAST_STDDEV_THRESHOLD:
                issues.append(f"warning: low contrast risk (score={contrast_score:.2f})")
            if width > 0 and height > 0 and (width < 500 or height < 500):
                issues.append("warning: OCR risk (small image)")
            if width > 0 and height > 0 and max(width, height) / max(1, min(width, height)) > EXTREME_ASPECT_RATIO_THRESHOLD:
                issues.append("warning: YOLO risk (extreme aspect ratio)")
        except Exception as exc:
            issues.append(f"warning: quality metrics unavailable ({exc})")

    pattern_ok, pattern_message = _validate_name_pattern(document_type, path.stem)
    if not pattern_ok:
        issues.append(pattern_message)

    if pil_ok and cv_ok and width > 0 and height > 0 and file_size_bytes > 0:
        try:
            file_hash = _hash_file(path)
        except Exception as exc:
            issues.append(f"cannot hash image: {exc}")
    else:
        file_hash = ""

    record = ImageRecord(
        path=_relative(path),
        document_type=document_type,
        status="valid",
        width=width,
        height=height,
        file_size_bytes=file_size_bytes,
        extension=extension,
        issues=issues,
        filename=filename,
        file_hash=file_hash,
    )
    return record, {"pil_ok": pil_ok, "cv_ok": cv_ok}


def _apply_duplicate_checks(records: list[ImageRecord]) -> None:
    filename_groups: dict[str, list[int]] = {}
    hash_groups: dict[str, list[int]] = {}
    for index, record in enumerate(records):
        filename_groups.setdefault(record.filename, []).append(index)
        if record.file_hash:
            hash_groups.setdefault(record.file_hash, []).append(index)

    for indices in filename_groups.values():
        if len(indices) > 1:
            for index in indices:
                records[index].issues.append("duplicate filename")

    for indices in hash_groups.values():
        if len(indices) > 1:
            for index in indices:
                records[index].issues.append("duplicate image hash")


def _finalize_status(record: ImageRecord) -> None:
    hard_prefixes = (
        "file does not exist",
        "PIL cannot read image",
        "OpenCV cannot read image",
        "width or height is not greater than 0",
        "file size is 0 byte",
    )
    has_invalid_issue = any(issue.startswith(hard_prefixes) for issue in record.issues)
    if has_invalid_issue:
        record.status = "invalid"
        return

    warning_prefixes = (
        "warning:",
        "duplicate filename",
        "duplicate image hash",
        "unsupported extension",
        "filename prefix must",
        "filename suffix must",
        "filename must use",
        "unknown document type for filename validation",
    )
    has_warning = any(issue.startswith(warning_prefixes) for issue in record.issues)

    record.status = "warning" if has_warning else "valid"


def _summarize(records: list[ImageRecord]) -> dict[str, Any]:
    summary = {
        "summary": {
            "total_images": len(records),
            "valid_images": 0,
            "warning_images": 0,
            "invalid_images": 0,
        },
        "appointment": {"total": 0, "valid": 0, "warnings": 0, "invalid": 0},
        "medicine": {"total": 0, "valid": 0, "warnings": 0, "invalid": 0},
        "images": [],
    }

    for record in records:
        doc_key = "appointment" if record.document_type == "Appointment" else "medicine" if record.document_type == "MedicineLabel" else None
        summary["summary"][f"{record.status}_images"] += 1
        if doc_key is not None:
            summary[doc_key]["total"] += 1
            summary[doc_key][f"{record.status}s" if record.status == "warning" else record.status] += 1
        summary["images"].append(
            {
                "path": record.path,
                "document_type": record.document_type,
                "status": record.status,
                "width": record.width,
                "height": record.height,
                "file_size_bytes": record.file_size_bytes,
                "extension": record.extension,
                "issues": record.issues,
            }
        )

    return summary


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Input Image Validation Report",
        "",
        "## Summary",
        "",
        f"- Total images: `{report['summary']['total_images']}`",
        f"- Valid images: `{report['summary']['valid_images']}`",
        f"- Warning images: `{report['summary']['warning_images']}`",
        f"- Invalid images: `{report['summary']['invalid_images']}`",
        "",
        "## By Document Type",
        "",
        f"- Appointment: total `{report['appointment']['total']}`, valid `{report['appointment']['valid']}`, warnings `{report['appointment']['warnings']}`, invalid `{report['appointment']['invalid']}`",
        f"- MedicineLabel: total `{report['medicine']['total']}`, valid `{report['medicine']['valid']}`, warnings `{report['medicine']['warnings']}`, invalid `{report['medicine']['invalid']}`",
        "",
        "## Problematic Images",
        "",
    ]

    problematic = [item for item in report["images"] if item["status"] != "valid"]
    if not problematic:
        lines.append("- None")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "| Path | Type | Status | Issues |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in problematic:
        issues = "<br>".join(item["issues"])
        lines.append(
            f"| `{item['path']}` | {item['document_type']} | {item['status']} | {issues} |"
        )
    lines.append("")
    return "\n".join(lines)


def validate_input_images(paths: list[str] | None = None) -> dict[str, Any]:
    input_paths = [Path(path) for path in (paths or [])]
    if not input_paths:
        input_paths = DEFAULT_INPUT_DIRS

    collected: list[Path] = []
    for input_path in input_paths:
        if not input_path.exists():
            print(f"WARNING: input path not found: {input_path}", file=sys.stderr)
            continue
        collected.extend(_iter_target_files(input_path))

    records: list[ImageRecord] = []
    for path in collected:
        record, _ = _evaluate_single(path)
        records.append(record)

    _apply_duplicate_checks(records)
    for record in records:
        _finalize_status(record)

    report = _summarize(records)
    return report


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    _ensure_reports_dir()
    report = validate_input_images(args.paths)
    json_payload = json.dumps(report, ensure_ascii=False, indent=2)
    JSON_REPORT_PATH.write_text(json_payload, encoding="utf-8")
    MD_REPORT_PATH.write_text(_render_markdown(report), encoding="utf-8")

    print(json_payload)
    print()
    print("Input image validation completed")
    print(f"JSON report: {JSON_REPORT_PATH}")
    print(f"Markdown report: {MD_REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
