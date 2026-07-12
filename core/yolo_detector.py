from __future__ import annotations

import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("YOLO_CONFIG_DIR", str(PROJECT_ROOT / ".ultralytics"))
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))

from PIL import Image, ImageDraw
from ultralytics import YOLO


class YoloDetector:
    def __init__(
        self,
        model_path: Path | None = None,
        debug_dir: Path | None = None,
    ) -> None:
        self.project_root = PROJECT_ROOT
        self.model_path = model_path or (self.project_root / "models" / "yolo" / "best.pt")
        self.debug_dir = debug_dir or (self.project_root / "runtime" / "debug" / "annotated")

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"ไม่พบโมเดล YOLO ที่ {self.model_path}. กรุณาตรวจสอบไฟล์ models/yolo/best.pt"
            )

        self.model = YOLO(str(self.model_path))

    def detect(self, image_path: str | Path) -> list[dict[str, Any]]:
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"ไม่พบไฟล์รูปภาพ: {image_path}")

        results = self.model.predict(source=str(image_path), verbose=False)
        if not results:
            self._save_annotated_image(image_path, [])
            return []

        result = results[0]
        detections: list[dict[str, Any]] = []
        for box_id, box in enumerate(result.boxes, start=1):
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            confidence = float(box.conf.item()) if box.conf is not None else 0.0
            detections.append(
                {
                    "box_id": box_id,
                    "bbox": [int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))],
                    "confidence": round(confidence, 4),
                }
            )

        self._save_annotated_image(image_path, detections)
        return detections

    def _save_annotated_image(
        self,
        image_path: Path,
        detections: list[dict[str, Any]],
    ) -> Path:
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        annotated_path = self.debug_dir / f"{image_path.stem}_annotated{image_path.suffix or '.jpg'}"

        with Image.open(image_path) as image:
            image = image.convert("RGB")
            draw = ImageDraw.Draw(image)
            for detection in detections:
                x1, y1, x2, y2 = detection["bbox"]
                draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0), width=3)
                label = f'#{detection["box_id"]} {detection["confidence"]:.2f}'
                text_position = (x1, max(0, y1 - 12))
                draw.text(text_position, label, fill=(255, 0, 0))
            image.save(annotated_path)

        return annotated_path
