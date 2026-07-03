from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(PROJECT_ROOT / ".paddlex"))
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))

from paddleocr import TextRecognition


def expand_box(
    box: list[int] | tuple[int, int, int, int],
    image_width: int,
    image_height: int,
    padding: int = 12,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = [int(round(value)) for value in box]
    left = max(0, min(x1, x2) - padding)
    top = max(0, min(y1, y2) - padding)
    right = min(image_width, max(x1, x2) + padding)
    bottom = min(image_height, max(y1, y2) + padding)

    if right <= left:
        right = min(image_width, left + 1)
    if bottom <= top:
        bottom = min(image_height, top + 1)

    return left, top, right, bottom


class PaddleOCRReader:
    def __init__(
        self,
        model_dir: Path | None = None,
        model_name: str = "PP-OCRv5_server_rec",
        padding: int = 12,
    ) -> None:
        self.project_root = PROJECT_ROOT
        self.model_dir = model_dir or (
            self.project_root / "models" / "paddle" / "th_PP-OCRv5_mobile_rec"
        )
        self.model_name = model_name
        self.padding = padding
        self.last_errors: list[str] = []

        if not self.model_dir.exists():
            raise FileNotFoundError(
                f"ไม่พบโมเดล PaddleOCR ที่ {self.model_dir}. กรุณาตรวจสอบไฟล์ models/paddle/th_PP-OCRv5_mobile_rec/"
            )

        self.reader = TextRecognition(
            model_name=self.model_name,
            model_dir=str(self.model_dir),
        )

    def read_regions(
        self,
        image_path: str | Path,
        boxes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"ไม่พบไฟล์รูปภาพ: {image_path}")

        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"ไม่สามารถอ่านไฟล์รูปภาพด้วย OpenCV: {image_path}")

        image_height, image_width = image.shape[:2]
        regions: list[dict[str, Any]] = []
        self.last_errors = []

        for box in boxes:
            bbox = box.get("bbox", [0, 0, 0, 0])
            expanded_bbox = expand_box(
                bbox,
                image_width=image_width,
                image_height=image_height,
                padding=self.padding,
            )
            x1, y1, x2, y2 = expanded_bbox
            roi = image[y1:y2, x1:x2]

            ocr_text, ocr_confidence, ocr_error = self._recognize_roi(roi)
            if ocr_error:
                self.last_errors.append(ocr_error)
            regions.append(
                {
                    "box_id": box.get("box_id"),
                    "bbox": [int(value) for value in box.get("bbox", [0, 0, 0, 0])],
                    "ocr_text": ocr_text,
                    "ocr_confidence": round(float(ocr_confidence), 4),
                    "yolo_confidence": round(float(box.get("confidence", 0.0)), 4),
                }
            )

        return regions

    def _recognize_roi(self, roi: np.ndarray) -> tuple[str, float, str | None]:
        if roi.size == 0:
            return "", 0.0, None

        try:
            results = self.reader.predict(roi)
        except Exception as exc:
            return "", 0.0, f"{type(exc).__name__}: {exc}"

        text, confidence = self._extract_text_and_confidence(results)
        return text, confidence, None

    def _extract_text_and_confidence(self, result: Any) -> tuple[str, float]:
        if result is None:
            return "", 0.0

        normalized = self._normalize_result(result)

        if isinstance(normalized, list):
            texts: list[str] = []
            confidences: list[float] = []
            for item in normalized:
                item_text, item_confidence = self._extract_text_and_confidence(item)
                if item_text:
                    texts.append(item_text)
                if item_confidence > 0:
                    confidences.append(item_confidence)
            if not texts:
                return "", max(confidences) if confidences else 0.0
            joined_text = "\n".join(texts).strip()
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            return joined_text, avg_confidence

        if isinstance(normalized, dict):
            text = self._find_first_value(
                normalized,
                ("rec_text", "text", "ocr_text", "transcription", "label", "result"),
            )
            confidence = self._find_first_value(
                normalized,
                ("rec_score", "score", "confidence", "probability", "prob"),
            )
            if text is None:
                return "", float(confidence) if confidence is not None else 0.0
            return str(text).strip(), float(confidence) if confidence is not None else 0.0

        if hasattr(normalized, "text") or hasattr(normalized, "rec_text"):
            text = getattr(normalized, "rec_text", None) or getattr(normalized, "text", "")
            confidence = (
                getattr(normalized, "rec_score", None)
                if getattr(normalized, "rec_score", None) is not None
                else getattr(normalized, "score", None)
            )
            return str(text).strip(), float(confidence) if confidence is not None else 0.0

        if isinstance(normalized, str):
            return normalized.strip(), 0.0

        return "", 0.0

    def _normalize_result(self, result: Any) -> Any:
        if hasattr(result, "to_dict"):
            try:
                return result.to_dict()
            except Exception:
                pass

        if isinstance(result, tuple):
            result = list(result)

        if isinstance(result, list) and len(result) == 1:
            return self._normalize_result(result[0])

        if isinstance(result, list):
            return [self._normalize_result(item) for item in result]

        if hasattr(result, "__dict__") and not isinstance(result, (str, bytes)):
            try:
                data = {
                    key: value
                    for key, value in vars(result).items()
                    if not key.startswith("_")
                }
                if data:
                    return data
            except Exception:
                pass

        return result

    def _find_first_value(self, data: Any, keys: tuple[str, ...]) -> Any:
        if isinstance(data, dict):
            for key in keys:
                if key in data and data[key] not in (None, ""):
                    return data[key]
            for value in data.values():
                found = self._find_first_value(value, keys)
                if found not in (None, ""):
                    return found
        elif isinstance(data, list):
            for item in data:
                found = self._find_first_value(item, keys)
                if found not in (None, ""):
                    return found
        return None
