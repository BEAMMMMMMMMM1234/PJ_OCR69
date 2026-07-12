from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.field_extractor import FieldExtractor
from core.document_classifier import DocumentClassifier
from core.final_output_formatter import FinalOutputFormatter
from core.gemma_postprocessor import GemmaPostProcessor
from core.paddle_ocr import PaddleOCRReader
from core.validator import DataValidator
from core.yolo_detector import YoloDetector

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = PROJECT_ROOT / "runtime"
RUNTIME_FINAL_OUTPUT_DIR = RUNTIME_DIR / "final_output"
RUNTIME_DEBUG_DIR = RUNTIME_DIR / "debug"
RUNTIME_ANNOTATED_DIR = RUNTIME_DEBUG_DIR / "annotated"
RUNTIME_CLASSIFICATION_DIR = RUNTIME_DEBUG_DIR / "classification"
RUNTIME_OCR_EVIDENCE_DIR = RUNTIME_DEBUG_DIR / "ocr_evidence"
RUNTIME_PIPELINE_TRACE_DIR = RUNTIME_DEBUG_DIR / "pipeline_trace"
DEBUG_TRACE_ARTIFACT_TYPE = "pipeline_trace"
DEBUG_TRACE_ARTIFACT_NOTE = (
    "This file is for developer debugging only. Web/API must use runtime/outputs/result.json"
)


class OCRPipeline:
    def __init__(
        self,
        yolo_detector: YoloDetector | None = None,
        ocr_reader: PaddleOCRReader | None = None,
        document_classifier: DocumentClassifier | None = None,
        field_extractor: FieldExtractor | None = None,
        validator: DataValidator | None = None,
        gemma_postprocessor: GemmaPostProcessor | None = None,
        final_output_formatter: FinalOutputFormatter | None = None,
        evidence_dir: Path | None = None,
        classification_dir: Path | None = None,
        extraction_dir: Path | None = None,
        validated_dir: Path | None = None,
        final_dir: Path | None = None,
        trace_dir: Path | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self.project_root = PROJECT_ROOT
        self.yolo_detector = yolo_detector or YoloDetector()
        self.ocr_reader = ocr_reader or PaddleOCRReader()
        self.classification_dir = classification_dir or RUNTIME_CLASSIFICATION_DIR
        self.document_classifier = document_classifier or DocumentClassifier(
            evidence_dir=self.classification_dir
        )
        self.field_extractor = field_extractor or FieldExtractor()
        self.validator = validator or DataValidator()
        self.gemma_postprocessor = gemma_postprocessor or GemmaPostProcessor()
        self.final_output_formatter = final_output_formatter or FinalOutputFormatter()
        self.evidence_dir = evidence_dir or RUNTIME_OCR_EVIDENCE_DIR
        self.final_dir = final_dir or RUNTIME_FINAL_OUTPUT_DIR
        self.trace_dir = trace_dir or RUNTIME_PIPELINE_TRACE_DIR
        self.extraction_dir = extraction_dir or self.trace_dir
        self.validated_dir = validated_dir or self.trace_dir
        self.output_dir = output_dir or self.final_dir

    def run(self, image_path: str | Path) -> dict[str, Any]:
        image_path = Path(image_path)
        base_result = self._empty_result(image_path)

        try:
            detections = self.yolo_detector.detect(image_path)
        except FileNotFoundError as exc:
            base_result["status"] = "failed"
            base_result["error"] = str(exc)
            final_output = self.final_output_formatter.format("failed", "Unknown", {}, str(exc))
            final_result = self._build_result(
                image_path=image_path,
                status="failed",
                raw_text="",
                text_regions=[],
                error=str(exc),
                classification=base_result["classification"],
                structured_data=base_result["structured_data"],
                validated_data=base_result["structured_data"],
                gemma_data={},
                gemma_attempted=False,
                gemma_used=False,
                gemma_success=False,
                gemma_approval=False,
                gemma_error=str(exc),
                gemma_debug={},
                final_data={},
                final_output=final_output,
            )
            self._finalize_and_save(image_path, final_result)
            return final_result
        except Exception as exc:
            base_result["status"] = "failed"
            base_result["error"] = f"YOLO error: {exc}"
            final_output = self.final_output_formatter.format("failed", "Unknown", {}, str(exc))
            final_result = self._build_result(
                image_path=image_path,
                status="failed",
                raw_text="",
                text_regions=[],
                error=str(exc),
                classification=base_result["classification"],
                structured_data=base_result["structured_data"],
                validated_data=base_result["structured_data"],
                gemma_data={},
                gemma_attempted=False,
                gemma_used=False,
                gemma_success=False,
                gemma_approval=False,
                gemma_error=str(exc),
                gemma_debug={},
                final_data={},
                final_output=final_output,
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
                gemma_data={},
                gemma_attempted=False,
                gemma_used=False,
                gemma_success=False,
                gemma_approval=False,
                gemma_error=None,
                gemma_debug={},
                final_data={},
                final_output=self.final_output_formatter.format("success", "Unknown", {}, None),
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
            final_output = self.final_output_formatter.format("failed", "Unknown", {}, str(exc))
            final_result = self._build_result(
                image_path=image_path,
                status="failed",
                raw_text="",
                text_regions=[],
                error=str(exc),
                classification=base_result["classification"],
                structured_data=base_result["structured_data"],
                validated_data=base_result["structured_data"],
                gemma_data={},
                gemma_attempted=False,
                gemma_used=False,
                gemma_success=False,
                gemma_approval=False,
                gemma_error=str(exc),
                gemma_debug={},
                final_data={},
                final_output=final_output,
            )
            self._finalize_and_save(image_path, final_result)
            return final_result
        except Exception as exc:
            base_result["status"] = "failed"
            base_result["error"] = f"PaddleOCR error: {exc}"
            final_output = self.final_output_formatter.format("failed", "Unknown", {}, str(exc))
            final_result = self._build_result(
                image_path=image_path,
                status="failed",
                raw_text="",
                text_regions=[],
                error=str(exc),
                classification=base_result["classification"],
                structured_data=base_result["structured_data"],
                validated_data=base_result["structured_data"],
                gemma_data={},
                gemma_attempted=False,
                gemma_used=False,
                gemma_success=False,
                gemma_approval=False,
                gemma_error=str(exc),
                gemma_debug={},
                final_data={},
                final_output=final_output,
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
        gemma_result = self.gemma_postprocessor.postprocess(
            document_type,
            validated_data,
            raw_text,
            debug_name=image_path.stem,
        )
        gemma_data = gemma_result.get("data", {}) or {}
        gemma_attempted = bool(gemma_result.get("attempted"))
        gemma_used = bool(gemma_result.get("used"))
        gemma_success = bool(gemma_result.get("success"))
        gemma_approval = bool(gemma_result.get("approval"))
        gemma_error = gemma_result.get("error")
        gemma_debug = gemma_result.get("debug", {}) or {}
        final_data = gemma_data if gemma_data else validated_data
        final_output = self.final_output_formatter.format("success", document_type, final_data, error_message)

        result = self._build_result(
            image_path=image_path,
            status="success",
            raw_text=raw_text,
            text_regions=text_regions,
            error=error_message,
            classification=classification,
            structured_data=structured_data,
            validated_data=validated_data,
            gemma_data=gemma_data,
            gemma_attempted=gemma_attempted,
            gemma_used=gemma_used,
            gemma_success=gemma_success,
            gemma_approval=gemma_approval,
            gemma_error=gemma_error,
            gemma_debug=gemma_debug,
            final_data=final_data,
            final_output=final_output,
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
            "gemma_data": {},
            "gemma_attempted": False,
            "gemma_used": False,
            "gemma_success": False,
            "gemma_approval": False,
            "gemma_error": None,
            "gemma_debug": {},
            "final_data": {},
            "final_output": {},
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
        gemma_data: dict[str, Any],
        gemma_attempted: bool,
        gemma_used: bool,
        gemma_success: bool,
        gemma_approval: bool,
        gemma_error: str | None,
        gemma_debug: dict[str, Any],
        final_data: dict[str, Any],
        final_output: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": status,
            "document_type": classification.get("document_type", "Unknown"),
            "structured_data": structured_data,
            "validated_data": validated_data,
            "gemma_data": gemma_data,
            "gemma_attempted": gemma_attempted,
            "gemma_used": gemma_used,
            "gemma_success": gemma_success,
            "gemma_approval": gemma_approval,
            "gemma_error": gemma_error,
            "gemma_debug": gemma_debug,
            "final_data": final_data,
            "ocr_evidence": {
                "image_path": str(image_path),
                "raw_text": raw_text,
                "text_regions": text_regions,
                "regions_count": len(text_regions),
                "error": error,
            },
            "classification": classification,
            "final_output": final_output,
            "error": error,
        }

    def _finalize_and_save(
        self,
        image_path: Path,
        result: dict[str, Any],
    ) -> None:
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.final_dir.mkdir(parents=True, exist_ok=True)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.extraction_dir.mkdir(parents=True, exist_ok=True)
        self.validated_dir.mkdir(parents=True, exist_ok=True)

        evidence_path = self.evidence_dir / f"{image_path.stem}_ocr.json"
        final_path = self.final_dir / f"{image_path.stem}.json"
        trace_path = self.trace_dir / f"{image_path.stem}_trace.json"

        evidence_payload = json.dumps(result.get("ocr_evidence", result), ensure_ascii=False, indent=2)
        final_payload = result.get("final_output") or self._build_final_output_artifact(result)
        trace_payload = self._build_pipeline_trace_artifact(result)
        evidence_path.write_text(evidence_payload, encoding="utf-8")
        final_path.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        trace_path.write_text(json.dumps(trace_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_final_output_artifact(self, result: dict[str, Any]) -> dict[str, Any]:
        from core.production_output import build_production_output

        return build_production_output(result)

    def _build_pipeline_trace_artifact(self, result: dict[str, Any]) -> dict[str, Any]:
        artifact = dict(result)
        artifact["artifact_type"] = DEBUG_TRACE_ARTIFACT_TYPE
        artifact["note"] = DEBUG_TRACE_ARTIFACT_NOTE
        gemma_debug = artifact.get("gemma_debug", {}) or {}
        artifact["gemma_attempted"] = bool(artifact.get("gemma_attempted"))
        artifact["gemma_success"] = bool(artifact.get("gemma_success"))
        artifact["gemma_model"] = gemma_debug.get("model")
        artifact["gemma_error"] = artifact.get("gemma_error") or gemma_debug.get("error")
        artifact["gemma_latency_seconds"] = gemma_debug.get("latency_seconds")
        artifact["changed_fields"] = gemma_debug.get("changed_fields", [])
        artifact["approval"] = gemma_debug.get("approval")
        artifact["warnings"] = gemma_debug.get("warnings", [])
        return artifact
