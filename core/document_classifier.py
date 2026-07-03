from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

APPOINTMENT_KEYWORDS: list[tuple[str, int]] = [
    ("ใบนัด", 5),
    ("วันนัด", 5),
    ("นัด", 3),
    ("พบแพทย์", 4),
    ("แพทย์นัด", 4),
    ("ข้อปฏิบัติ", 3),
    ("ก่อนนัด", 3),
    ("งดน้ำ", 3),
    ("งดอาหาร", 3),
    ("วันที่", 1),
    ("เวลา", 1),
]

MEDICINE_KEYWORDS: list[tuple[str, int]] = [
    ("ชื่อยา", 5),
    ("วิธีใช้", 5),
    ("วิธีรับประทาน", 5),
    ("รับประทาน", 4),
    ("ครั้งละ", 4),
    ("วันละ", 4),
    ("ก่อนอาหาร", 3),
    ("หลังอาหาร", 3),
    ("ยา", 1),
]

UNKNOWN_SCORE_GAP = 2


class DocumentClassifier:
    def __init__(self, evidence_dir: Path | None = None) -> None:
        self.project_root = PROJECT_ROOT
        self.evidence_dir = evidence_dir or (self.project_root / "debug" / "classification")

    def classify(self, raw_text: str, image_path: str | Path) -> dict[str, Any]:
        raw_text = raw_text or ""
        normalized_text = self._normalize_text(raw_text)

        appointment_score, matched_appointment_keywords = self._score_keywords(
            normalized_text, APPOINTMENT_KEYWORDS
        )
        medicine_score, matched_medicine_keywords = self._score_keywords(
            normalized_text, MEDICINE_KEYWORDS
        )

        score_gap = abs(appointment_score - medicine_score)
        if score_gap < UNKNOWN_SCORE_GAP or (
            appointment_score == 0 and medicine_score == 0
        ):
            document_type = "Unknown"
        elif appointment_score > medicine_score:
            document_type = "Appointment"
        else:
            document_type = "MedicineLabel"

        result = {
            "document_type": document_type,
            "appointment_score": appointment_score,
            "medicine_score": medicine_score,
            "matched_appointment_keywords": matched_appointment_keywords,
            "matched_medicine_keywords": matched_medicine_keywords,
        }

        self._save_evidence(image_path, result)
        return result

    def _normalize_text(self, text: str) -> str:
        return " ".join(text.split()).casefold()

    def _score_keywords(
        self,
        text: str,
        keywords: list[tuple[str, int]],
    ) -> tuple[int, list[dict[str, int | str]]]:
        matched_keywords: list[dict[str, int | str]] = []
        score = 0

        for keyword, weight in keywords:
            occurrences = text.count(keyword.casefold())
            if occurrences <= 0:
                continue

            score += occurrences * weight
            matched_keywords.append({"keyword": keyword, "weight": weight})

        return score, matched_keywords

    def _save_evidence(self, image_path: str | Path, result: dict[str, Any]) -> None:
        image_path = Path(image_path)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_path = self.evidence_dir / f"{image_path.stem}_classification.json"
        evidence_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
