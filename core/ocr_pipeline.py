from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.document_classifier import DocumentClassifier
from core.paddle_ocr import PaddleOCRReader
from core.yolo_detector import YoloDetector

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class OCRPipeline:
    def __init__(
        self,
        yolo_detector: YoloDetector | None = None,
        ocr_reader: PaddleOCRReader | None = None,
        document_classifier: DocumentClassifier | None = None,
        evidence_dir: Path | None = None,
        classification_dir: Path | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self.project_root = PROJECT_ROOT
        self.yolo_detector = yolo_detector or YoloDetector()
        self.ocr_reader = ocr_reader or PaddleOCRReader()
        self.classification_dir = classification_dir or (
            self.project_root / "debug" / "classification"
        )
        self.document_classifier = document_classifier or DocumentClassifier(
            evidence_dir=self.classification_dir
        )
        self.evidence_dir = evidence_dir or (self.project_root / "debug" / "ocr_evidence")
        self.output_dir = output_dir or (self.project_root / "outputs")

    def run(self, image_path: str | Path) -> dict[str, Any]:
        image_path = Path(image_path)
        base_result = self._empty_result(image_path)

        try:
            detections = self.yolo_detector.detect(image_path)
        except FileNotFoundError as exc:
            base_result["status"] = "failed"
            base_result["error"] = str(exc)
            self._save_outputs(image_path, base_result)
            return base_result
        except Exception as exc:
            base_result["status"] = "failed"
            base_result["error"] = f"YOLO error: {exc}"
            self._save_outputs(image_path, base_result)
            return base_result

        if not detections:
            self._save_outputs(image_path, base_result)
            return base_result

        sorted_detections = sorted(
            detections,
            key=lambda item: (
                item["bbox"][1],
                item["bbox"][0],
                item["bbox"][3],
                item["bbox"][2],
            ),
        )
        sorted_detections = [
            {
                "box_id": index,
                "bbox": detection["bbox"],
                "confidence": detection["confidence"],
            }
            for index, detection in enumerate(sorted_detections, start=1)
        ]

        try:
            text_regions = self.ocr_reader.read_regions(image_path, sorted_detections)
        except FileNotFoundError as exc:
            base_result["status"] = "failed"
            base_result["error"] = str(exc)
            self._save_outputs(image_path, base_result)
            return base_result
        except Exception as exc:
            base_result["status"] = "failed"
            base_result["error"] = f"PaddleOCR error: {exc}"
            self._save_outputs(image_path, base_result)
            return base_result

        raw_text = "\n".join(
            region["ocr_text"].strip() for region in text_regions if region["ocr_text"].strip()
        )
        ocr_errors = getattr(self.ocr_reader, "last_errors", [])
        error_message = "; ".join(dict.fromkeys(ocr_errors)) if ocr_errors else None

        result = {
            "status": "success",
            "image_path": str(image_path),
            "raw_text": raw_text,
            "text_regions": text_regions,
            "regions_count": len(text_regions),
            "error": error_message,
        }

        classification = self.document_classifier.classify(raw_text, image_path)
        result["classification"] = classification

        self._save_outputs(image_path, result)
        return result

    def _empty_result(self, image_path: Path) -> dict[str, Any]:
        return {
            "status": "success",
            "image_path": str(image_path),
            "raw_text": "",
            "text_regions": [],
            "regions_count": 0,
            "error": None,
            "classification": {
                "document_type": "Unknown",
                "appointment_score": 0,
                "medicine_score": 0,
                "matched_appointment_keywords": [],
                "matched_medicine_keywords": [],
            },
        }

    def _save_outputs(self, image_path: Path, result: dict[str, Any]) -> None:
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        evidence_path = self.evidence_dir / f"{image_path.stem}_ocr.json"
        output_path = self.output_dir / "result.json"

        evidence_payload = json.dumps(result, ensure_ascii=False, indent=2)
        evidence_path.write_text(evidence_payload, encoding="utf-8")
        output_path.write_text(evidence_payload, encoding="utf-8")
