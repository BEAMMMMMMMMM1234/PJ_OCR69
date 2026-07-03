from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.field_extractor import FieldExtractor
from core.document_classifier import DocumentClassifier
from core.gemma_formatter import GemmaFormatter
from core.paddle_ocr import PaddleOCRReader
from core.validator import DataValidator
from core.yolo_detector import YoloDetector

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class OCRPipeline:
    def __init__(
        self,
        yolo_detector: YoloDetector | None = None,
        ocr_reader: PaddleOCRReader | None = None,
        document_classifier: DocumentClassifier | None = None,
        field_extractor: FieldExtractor | None = None,
        validator: DataValidator | None = None,
        gemma_formatter: GemmaFormatter | None = None,
        evidence_dir: Path | None = None,
        classification_dir: Path | None = None,
        extraction_dir: Path | None = None,
        validated_dir: Path | None = None,
        final_dir: Path | None = None,
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
        self.field_extractor = field_extractor or FieldExtractor()
        self.validator = validator or DataValidator()
        self.gemma_formatter = gemma_formatter or GemmaFormatter()
        self.evidence_dir = evidence_dir or (self.project_root / "debug" / "ocr_evidence")
        self.extraction_dir = extraction_dir or (self.project_root / "debug" / "final_output")
        self.validated_dir = validated_dir or (self.project_root / "debug" / "final_output")
        self.final_dir = final_dir or (self.project_root / "debug" / "final_output")
        self.output_dir = output_dir or (self.project_root / "outputs")

    def run(self, image_path: str | Path) -> dict[str, Any]:
        image_path = Path(image_path)
        base_result = self._empty_result(image_path)

        try:
            detections = self.yolo_detector.detect(image_path)
        except FileNotFoundError as exc:
            base_result["status"] = "failed"
            base_result["error"] = str(exc)
            final_result = self._build_result(
                image_path=image_path,
                status="failed",
                raw_text="",
                text_regions=[],
                error=str(exc),
                classification=base_result["classification"],
                structured_data=base_result["structured_data"],
                validated_data=base_result["structured_data"],
                final_data={},
            )
            self._finalize_and_save(image_path, final_result)
            return final_result
        except Exception as exc:
            base_result["status"] = "failed"
            base_result["error"] = f"YOLO error: {exc}"
            final_result = self._build_result(
                image_path=image_path,
                status="failed",
                raw_text="",
                text_regions=[],
                error=str(exc),
                classification=base_result["classification"],
                structured_data=base_result["structured_data"],
                validated_data=base_result["structured_data"],
                final_data={},
            )
            self._finalize_and_save(image_path, final_result)
            return final_result

        if not detections:
            final_result = self._build_result(
                image_path=image_path,
                status="success",
                raw_text="",
                text_regions=[],
                error=None,
                classification=base_result["classification"],
                structured_data=base_result["structured_data"],
                validated_data=base_result["structured_data"],
                final_data={},
            )
            self._finalize_and_save(image_path, final_result)
            return final_result

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
            final_result = self._build_result(
                image_path=image_path,
                status="failed",
                raw_text="",
                text_regions=[],
                error=str(exc),
                classification=base_result["classification"],
                structured_data=base_result["structured_data"],
                validated_data=base_result["structured_data"],
                final_data={},
            )
            self._finalize_and_save(image_path, final_result)
            return final_result
        except Exception as exc:
            base_result["status"] = "failed"
            base_result["error"] = f"PaddleOCR error: {exc}"
            final_result = self._build_result(
                image_path=image_path,
                status="failed",
                raw_text="",
                text_regions=[],
                error=str(exc),
                classification=base_result["classification"],
                structured_data=base_result["structured_data"],
                validated_data=base_result["structured_data"],
                final_data={},
            )
            self._finalize_and_save(image_path, final_result)
            return final_result

        raw_text = "\n".join(
            region["ocr_text"].strip() for region in text_regions if region["ocr_text"].strip()
        )
        ocr_errors = getattr(self.ocr_reader, "last_errors", [])
        error_message = "; ".join(dict.fromkeys(ocr_errors)) if ocr_errors else None

        classification = self.document_classifier.classify(raw_text, image_path)
        document_type = classification["document_type"]
        structured_data = self.field_extractor.extract(
            document_type=document_type,
            raw_text=raw_text,
            text_regions=text_regions,
        )
        validated_data = self.validator.validate(document_type, structured_data)
        final_data = self.gemma_formatter.format(document_type, validated_data)

        result = self._build_result(
            image_path=image_path,
            status="success",
            raw_text=raw_text,
            text_regions=text_regions,
            error=error_message,
            classification=classification,
            structured_data=structured_data,
            validated_data=validated_data,
            final_data=final_data,
        )

        self._finalize_and_save(image_path, result)
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
            "structured_data": {},
            "validated_data": {},
            "final_data": {},
        }

    def _build_result(
        self,
        image_path: Path,
        status: str,
        raw_text: str,
        text_regions: list[dict[str, Any]],
        error: str | None,
        classification: dict[str, Any],
        structured_data: dict[str, Any],
        validated_data: dict[str, Any],
        final_data: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": status,
            "document_type": classification.get("document_type", "Unknown"),
            "structured_data": structured_data,
            "validated_data": validated_data,
            "final_data": final_data,
            "ocr_evidence": {
                "image_path": str(image_path),
                "raw_text": raw_text,
                "text_regions": text_regions,
                "regions_count": len(text_regions),
                "error": error,
            },
            "classification": classification,
            "error": error,
        }

    def _finalize_and_save(
        self,
        image_path: Path,
        result: dict[str, Any],
    ) -> None:
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.extraction_dir.mkdir(parents=True, exist_ok=True)
        self.validated_dir.mkdir(parents=True, exist_ok=True)
        self.final_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        evidence_path = self.evidence_dir / f"{image_path.stem}_ocr.json"
        extraction_path = self.extraction_dir / f"{image_path.stem}_extracted.json"
        validated_path = self.validated_dir / f"{image_path.stem}_validated.json"
        final_path = self.final_dir / f"{image_path.stem}_final.json"
        output_path = self.output_dir / "result.json"

        evidence_payload = json.dumps(result.get("ocr_evidence", result), ensure_ascii=False, indent=2)
        evidence_path.write_text(evidence_payload, encoding="utf-8")
        extraction_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        validated_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        final_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
