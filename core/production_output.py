from __future__ import annotations

import json
import logging
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = PROJECT_ROOT / "runtime"
RUNTIME_OUTPUTS_DIR = RUNTIME_DIR / "outputs"
RUNTIME_REPORTS_DIR = PROJECT_ROOT / "reports"
RUNTIME_LOGS_DIR = RUNTIME_DIR / "logs"
RUNTIME_DEBUG_DIR = RUNTIME_DIR / "debug"
RUNTIME_FINAL_OUTPUT_DIR = RUNTIME_DIR / "final_output"
RUNTIME_DEBUG_ANNOTATED_DIR = RUNTIME_DEBUG_DIR / "annotated"
RUNTIME_DEBUG_CLASSIFICATION_DIR = RUNTIME_DEBUG_DIR / "classification"
RUNTIME_DEBUG_OCR_EVIDENCE_DIR = RUNTIME_DEBUG_DIR / "ocr_evidence"
RUNTIME_DEBUG_PIPELINE_TRACE_DIR = RUNTIME_DEBUG_DIR / "pipeline_trace"
RUNTIME_DEBUG_GEMMA_DIR = RUNTIME_DEBUG_DIR / "gemma"
RUNTIME_SUMMARY_PATH = RUNTIME_REPORTS_DIR / "report_summary.json"

def ensure_runtime_dirs() -> dict[str, Path]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_FINAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DEBUG_ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DEBUG_CLASSIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DEBUG_OCR_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DEBUG_PIPELINE_TRACE_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DEBUG_GEMMA_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "runtime": RUNTIME_DIR,
        "outputs": RUNTIME_OUTPUTS_DIR,
        "reports": RUNTIME_REPORTS_DIR,
        "logs": RUNTIME_LOGS_DIR,
        "final_output": RUNTIME_FINAL_OUTPUT_DIR,
        "debug": RUNTIME_DEBUG_DIR,
        "pipeline_trace": RUNTIME_DEBUG_PIPELINE_TRACE_DIR,
    }


class SummaryWriter:
    def write(self, path: Path, entries: list[dict[str, Any]]) -> dict[str, Any]:
        payload = build_summary_report(entries)
        write_json(path, payload)
        return payload


def setup_logger(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("pj_ocr69.runtime")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def build_production_output(
    pipeline_result: dict[str, Any],
) -> dict[str, Any]:
    final_output = pipeline_result.get("final_output")
    if isinstance(final_output, dict) and final_output:
        return dict(final_output)
    return {}


def write_latest_result(output: dict[str, Any]) -> Path:
    path = RUNTIME_OUTPUTS_DIR / "result.json"
    write_json(path, output)
    return path


def build_report_entry(
    image_name: str,
    pipeline_result: dict[str, Any],
    processing_time: float,
) -> dict[str, Any]:
    status = str(pipeline_result.get("status", "failed"))
    document_type = str(pipeline_result.get("document_type", "Unknown"))
    final_output = pipeline_result.get("final_output", {}) or {}
    warnings: list[str] = []
    if status != "success":
        warnings.append("status failed")
    if pipeline_result.get("error"):
        warnings.append(str(pipeline_result.get("error")))
    if isinstance(final_output, dict) and final_output.get("error"):
        warnings.append(str(final_output.get("error")))
    return {
        "image_name": image_name,
        "status": status,
        "document_type": document_type,
        "processing_time": round(float(processing_time), 2),
        "warning": warnings,
        "error": pipeline_result.get("error"),
    }


def build_summary_report(entries: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(entries)
    success = sum(1 for item in entries if item.get("status") == "success")
    failed = total - success
    appointment = sum(1 for item in entries if item.get("document_type") == "Appointment")
    medicine = sum(1 for item in entries if item.get("document_type") == "MedicineLabel")
    processing_times = [float(item.get("processing_time", 0.0)) for item in entries]

    return {
        "total": total,
        "success": success,
        "failed": failed,
        "appointment": appointment,
        "medicine": medicine,
        "average_processing_time": round(mean(processing_times), 2) if processing_times else 0.0,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
