from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

APPOINTMENT_KEYWORDS: list[tuple[str, int]] = [
    ("ใบนัด", 5),
    ("วันนัด", 5),
    ("นัดหมาย", 5),
    ("มาตามนัด", 5),
    ("วัน/เดือน/ปี", 4),
    ("นัด", 3),
    ("พบแพทย์", 4),
    ("แพทย์นัด", 4),
    ("คลินิก", 4),
    ("ห้องตรวจ", 4),
    ("แผนก", 3),
    ("ผู้ป่วยนอก", 4),
    ("opd", 4),
    ("โรงพยาบาล", 2),
    ("hospital", 2),
    ("request", 2),
    ("requested", 2),
    ("result", 1),
    ("ข้อปฏิบัติ", 3),
    ("ก่อนนัด", 3),
    ("งดน้ำ", 3),
    ("งดอาหาร", 3),
    ("เจาะเลือด", 4),
    ("ตรวจเลือด", 4),
    ("เอกซเรย์", 4),
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

MEDICINE_DOSAGE_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"(?i)\b(?:TAB|CAP|MG|ML|MCG|เม็ด|แคปซูล)\b"), 4, "dosage token"),
    (re.compile(r"(?i)\b[A-Za-z][A-Za-z0-9()./+\-\s]{2,}\b\s+\d+\s*(?:MG|ML|MCG|g|G)\b"), 5, "drug name + dosage"),
    (re.compile(r"(?i)\b\d+\s*(?:MG|ML|MCG|TAB|CAP)\b"), 4, "numeric dosage"),
]

MEDICINE_USAGE_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"(?i)\b(?:รับประทาน|ครั้งละ|วันละ|ก่อนอาหาร|หลังอาหาร|ก่อนนอน)\b"), 4, "usage instruction"),
    (re.compile(r"(?i)\bทุก\s*\d+\s*-\s*\d+\s*ชั่วโมง\b"), 3, "frequency instruction"),
]

MEDICINE_CONTEXT_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"(?i)\bHN\b.*\bยา\b|\bยา\b.*\bHN\b"), 2, "hn and medicine"),
]

UNKNOWN_SCORE_GAP = 2


class DocumentClassifier:
    def __init__(self, evidence_dir: Path | None = None) -> None:
        self.project_root = PROJECT_ROOT
        self.evidence_dir = evidence_dir or (self.project_root / "runtime" / "debug" / "classification")

    def classify(self, raw_text: str, image_path: str | Path) -> dict[str, Any]:
        raw_text = raw_text or ""
        normalized_text = self._normalize_text(raw_text)

        appointment_score, matched_appointment_keywords = self._score_keywords(
            normalized_text, APPOINTMENT_KEYWORDS
        )
        medicine_score, matched_medicine_keywords = self._score_keywords(
            normalized_text, MEDICINE_KEYWORDS
        )
        medicine_pattern_hits = self._score_medicine_patterns(normalized_text)
        matched_medicine_patterns = medicine_pattern_hits["matched_patterns"]
        medicine_score += medicine_pattern_hits["score"]
        medicine_groups = medicine_pattern_hits["groups"]

        score_gap = abs(appointment_score - medicine_score)
        fallback_reason = None
        decision_reason = None

        if self._has_strong_appointment_evidence(
            appointment_score=appointment_score,
            matched_appointment_keywords=matched_appointment_keywords,
            text=normalized_text,
        ):
            document_type = "Appointment"
            decision_reason = "strong appointment evidence"
        elif self._has_strong_medicine_evidence(
            medicine_score=medicine_score,
            medicine_groups=medicine_groups,
            matched_medicine_keywords=matched_medicine_keywords,
            matched_medicine_patterns=matched_medicine_patterns,
            text=normalized_text,
        ):
            document_type = "MedicineLabel"
            decision_reason = "strong medicine evidence"
        elif appointment_score > medicine_score and score_gap >= UNKNOWN_SCORE_GAP:
            document_type = "Appointment"
            decision_reason = "appointment score higher"
        elif medicine_score > appointment_score and score_gap >= UNKNOWN_SCORE_GAP:
            document_type = "MedicineLabel"
            decision_reason = "medicine score higher"
        else:
            if self._looks_like_appointment_document(normalized_text, matched_appointment_keywords):
                document_type = "Appointment"
                fallback_reason = "appointment tie-break fallback"
                decision_reason = "appointment tie-break fallback"
            elif self._looks_like_medicine_document(normalized_text, medicine_groups, matched_medicine_patterns):
                document_type = "MedicineLabel"
                fallback_reason = "medicine tie-break fallback"
                decision_reason = "medicine tie-break fallback"
            else:
                document_type = "Unknown"
                fallback_reason = "no strong evidence"
                decision_reason = "no strong evidence"

        if document_type == "MedicineLabel" and medicine_score == 0 and matched_medicine_patterns:
            medicine_score = 1
        if document_type == "Appointment" and appointment_score == 0 and matched_appointment_keywords:
            appointment_score = 1

        result = {
            "document_type": document_type,
            "appointment_score": appointment_score,
            "medicine_score": medicine_score,
            "matched_appointment_keywords": matched_appointment_keywords,
            "matched_medicine_keywords": matched_medicine_keywords,
            "matched_medicine_patterns": matched_medicine_patterns,
            "fallback_reason": fallback_reason,
            "decision_reason": decision_reason,
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

    def _score_medicine_patterns(self, text: str) -> dict[str, Any]:
        matched_patterns: list[str] = []
        score = 0
        groups: set[str] = set()

        for pattern, weight, label in MEDICINE_DOSAGE_PATTERNS:
            if pattern.search(text):
                matched_patterns.append(label)
                score += weight
                groups.add("dosage")

        for pattern, weight, label in MEDICINE_USAGE_PATTERNS:
            if pattern.search(text):
                matched_patterns.append(label)
                score += weight
                groups.add("usage")

        for pattern, weight, label in MEDICINE_CONTEXT_PATTERNS:
            if pattern.search(text):
                matched_patterns.append(label)
                score += weight
                groups.add("context")

        if re.search(r"\bยา\b", text, re.IGNORECASE):
            matched_patterns.append("medicine keyword")

        matched_patterns = list(dict.fromkeys(matched_patterns))
        return {
            "matched_patterns": matched_patterns,
            "score": score,
            "groups": groups,
        }

    def _has_strong_medicine_evidence(
        self,
        text: str,
        medicine_score: int,
        medicine_groups: set[str],
        matched_medicine_keywords: list[dict[str, int | str]],
        matched_medicine_patterns: list[str],
    ) -> bool:
        has_dosage_group = "dosage" in medicine_groups
        has_usage_group = "usage" in medicine_groups
        has_context_group = "context" in medicine_groups
        has_name_or_label = any(
            item.get("keyword") in {"ชื่อยา", "วิธีใช้", "วิธีรับประทาน"} for item in matched_medicine_keywords
        )
        has_medicine_word = any(item.get("keyword") == "ยา" for item in matched_medicine_keywords)
        has_two_groups = sum(
            1
            for flag in (has_dosage_group, has_usage_group, has_context_group, has_name_or_label)
            if flag
        ) >= 2
        if has_name_or_label and (has_dosage_group or has_usage_group):
            return True
        if has_dosage_group and has_usage_group:
            return True
        if has_two_groups and medicine_score >= 5:
            return True
        if has_medicine_word and (has_dosage_group or has_usage_group) and medicine_score >= 4:
            return True
        if matched_medicine_patterns and has_two_groups:
            return True
        return False

    def _has_strong_appointment_evidence(
        self,
        appointment_score: int,
        matched_appointment_keywords: list[dict[str, int | str]],
        text: str,
    ) -> bool:
        strong_keywords = {
            "ใบนัด",
            "วันนัด",
            "นัดหมาย",
            "มาตามนัด",
            "พบแพทย์",
            "คลินิก",
            "ห้องตรวจ",
            "ผู้ป่วยนอก",
            "งดน้ำ",
            "งดอาหาร",
            "เจาะเลือด",
            "ตรวจเลือด",
            "เอกซเรย์",
            "request",
            "requested",
            "result",
        }
        matched = {str(item.get("keyword", "")).casefold() for item in matched_appointment_keywords}
        if matched & strong_keywords:
            return True
        if appointment_score >= 8 and len(matched & strong_keywords) >= 2:
            return True
        if re.search(r"(?i)\b(?:คลินิก|ห้องตรวจ|ผู้ป่วยนอก)\b", text) and (
            re.search(r"(?i)\b(?:นัด|วันนัด|มาตามนัด|พบแพทย์|request|requested|result)\b", text)
        ):
            return True
        if re.search(r"(?i)\b(?:งดน้ำ|งดอาหาร|เจาะเลือด|ตรวจเลือด|เอกซเรย์)\b", text) and re.search(
            r"(?i)\b(?:นัด|วันนัด|พบแพทย์|คลินิก|ห้องตรวจ|request|requested|result)\b",
            text,
        ):
            return True
        return False

    def _looks_like_medicine_document(
        self,
        text: str,
        medicine_groups: set[str],
        matched_medicine_patterns: list[str],
    ) -> bool:
        has_two_groups = len({"dosage", "usage", "context"} & medicine_groups) >= 2
        if not has_two_groups:
            return False
        has_drug_token = bool(re.search(r"(?i)\b(?:TAB|CAP|MG|ML|MCG|เม็ด|แคปซูล)\b", text))
        has_name_candidate = bool(
            re.search(r"(?i)\b[A-Za-z][A-Za-z0-9()./+\-\s]{2,}\b\s+(?:TAB|CAP|MG|ML|MCG)\b", text)
        )
        has_usage = bool(re.search(r"(?i)\b(?:รับประทาน|ครั้งละ|วันละ|ก่อนอาหาร|หลังอาหาร|เวลามีไข้|ปวด)\b", text))
        if has_name_candidate and (has_usage or has_drug_token):
            return True
        if has_drug_token and has_usage:
            return True
        if has_name_candidate and "medicine keyword" in matched_medicine_patterns:
            return True
        return False

    def _looks_like_appointment_document(self, text: str, matched_appointment_keywords: list[dict[str, int | str]]) -> bool:
        appointment_hits = sum(1 for keyword, _ in APPOINTMENT_KEYWORDS if keyword.casefold() in text)
        strong_hits = {
            str(item.get("keyword", "")).casefold()
            for item in matched_appointment_keywords
            if str(item.get("keyword", "")).casefold()
            in {
                "ใบนัด",
                "วันนัด",
                "นัดหมาย",
                "มาตามนัด",
                "พบแพทย์",
                "คลินิก",
                "ห้องตรวจ",
                "ผู้ป่วยนอก",
            }
        }
        return appointment_hits >= 2 or bool(strong_hits) or bool(
            re.search(r"(?i)\b(?:วันนัด|พบแพทย์|ห้องตรวจ|คลินิก|งดน้ำ|งดอาหาร|lab|request|requested|result)\b", text)
        )

    def _save_evidence(self, image_path: str | Path, result: dict[str, Any]) -> None:
        image_path = Path(image_path)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_path = self.evidence_dir / f"{image_path.stem}_classification.json"
        evidence_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
