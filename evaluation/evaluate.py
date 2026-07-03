from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.ocr_pipeline import OCRPipeline
from evaluation.cer import calculate_cer
from evaluation.field_accuracy import calculate_field_accuracy

DEFAULT_SAMPLE_PATH = PROJECT_ROOT / "evaluation" / "sample_ground_truth.json"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "evaluation" / "evaluation_report.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(sample_ground_truth_path: str | Path = DEFAULT_SAMPLE_PATH) -> dict[str, Any]:
    sample_ground_truth_path = Path(sample_ground_truth_path)
    payload = _load_json(sample_ground_truth_path)
    samples = payload.get("samples", [])

    pipeline = OCRPipeline()
    sample_reports: list[dict[str, Any]] = []
    cer_values: list[float] = []
    field_accuracy_values: list[float] = []

    for sample in samples:
        image_path_raw = sample.get("image_path", "")
        document_type = sample.get("document_type", "Unknown")
        reference_text = sample.get("reference_text", "")
        ground_truth_final_data = sample.get("ground_truth_final_data", {})

        predicted_result: dict[str, Any]
        sample_error: str | None = None
        if not image_path_raw:
            predicted_result = {
                "document_type": "Unknown",
                "ocr_evidence": {"raw_text": ""},
                "final_data": {},
            }
            sample_error = "image_path is missing"
        else:
            image_path = Path(image_path_raw)
            if not image_path.exists():
                predicted_result = {
                    "document_type": "Unknown",
                    "ocr_evidence": {"raw_text": ""},
                    "final_data": {},
                }
                sample_error = f"image_path not found: {image_path_raw}"
            else:
                try:
                    predicted_result = pipeline.run(image_path)
                    sample_error = predicted_result.get("error")
                except Exception as exc:  # noqa: BLE001
                    predicted_result = {
                        "document_type": "Unknown",
                        "ocr_evidence": {"raw_text": ""},
                        "final_data": {},
                    }
                    sample_error = str(exc)

        predicted_ocr = predicted_result.get("ocr_evidence", {}) or {}
        predicted_raw_text = predicted_ocr.get("raw_text", "")
        predicted_final_data = predicted_result.get("final_data", {}) or {}
        predicted_document_type = predicted_result.get("document_type", "Unknown")

        cer_report = calculate_cer(reference_text, predicted_raw_text)
        field_accuracy_report = calculate_field_accuracy(
            ground_truth_final_data,
            predicted_final_data,
        )

        cer_values.append(float(cer_report["cer"]))
        field_accuracy_values.append(float(field_accuracy_report["field_accuracy"]))

        sample_report: dict[str, Any] = {
            "image_path": image_path_raw,
            "document_type": document_type,
            "predicted_document_type": predicted_document_type,
            "cer": cer_report["cer"],
            "field_accuracy": field_accuracy_report["field_accuracy"],
            "field_details": field_accuracy_report["details"],
        }
        if sample_error:
            sample_report["error"] = sample_error

        sample_reports.append(sample_report)

    total_samples = len(sample_reports)
    average_cer = 0.0 if total_samples == 0 else sum(cer_values) / total_samples
    average_field_accuracy = 0.0 if total_samples == 0 else sum(field_accuracy_values) / total_samples

    return {
        "summary": {
            "total_samples": total_samples,
            "average_cer": average_cer,
            "average_field_accuracy": average_field_accuracy,
        },
        "samples": sample_reports,
    }


def main() -> int:
    report = evaluate(DEFAULT_SAMPLE_PATH)
    DEFAULT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
