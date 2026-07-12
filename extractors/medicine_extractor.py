from __future__ import annotations

import re
from typing import Any


class MedicineExtractor:
    INSTRUCTION_KEYWORDS = [
        "วิธีใช้",
        "วิธีรับประทาน",
        "รับประทาน",
        "ทานครั้งละ",
        "กินครั้งละ",
        "ครั้งละ",
        "วันละ",
        "ก่อนอาหาร",
        "หลังอาหาร",
        "พร้อมอาหาร",
    ]
    CONTINUATION_KEYWORDS = [
        "เช้า",
        "กลางวัน",
        "เย็น",
        "ก่อนนอน",
        "ทุก",
        "ชั่วโมง",
        "เวลาเจ็บ",
        "เวลามีอาการ",
        "เวลามีไข้",
    ]
    NOISE_PATTERNS = [
        re.compile(r"^\s*\[\s*\d+\s*[A-Za-zก-๙]*\s*\]\s*$"),
        re.compile(r"^\s*\d+\s*(?:TAB|tab|เม็ด|แผง|กล่อง)\s*$"),
        re.compile(r"^\s*ม0\s*เม็ด\s*$", re.IGNORECASE),
        re.compile(r"^\s*(?:จำนวน|คงเหลือ)\b.*$", re.IGNORECASE),
        re.compile(r"^\s*hn\s*[:：]?\s*\d+", re.IGNORECASE),
        re.compile(r"^\s*(?:โรงพยาบาล|hospital|university)\b", re.IGNORECASE),
        re.compile(r"^\s*(?:ชื่อผู้ป่วย|patient|ชื่อ)\b", re.IGNORECASE),
        re.compile(r"^\s*\d{1,2}[:.]\d{1,2}(?:[:.-]\d{1,2})?\s*(?:น\.?)?\s*$", re.IGNORECASE),
    ]
    NAME_PATTERNS = [
        re.compile(r"^(?:ชื่อยา|ยา)\s*[:\-]?\s*(.+)$", re.IGNORECASE),
        re.compile(r"^(?:Rx|Drug)\s*[:\-]?\s*(.+)$", re.IGNORECASE),
        re.compile(
            r"(?i)\b([A-Za-z][A-Za-z0-9()./+\-]{2,}(?:\s+[A-Za-z0-9()./+\-]{1,})*)\s*[<:=\-]?\s*(\d+\s*(?:MG|ML|MCG|G|TAB|CAP)\b(?:[^\n]*)?)"
        ),
    ]
    NAME_CANDIDATE_PATTERNS = [
        re.compile(
            r"(?i)\b[A-Za-z][A-Za-z0-9()./+\-\s]{2,}\b(?:TAB|CAP|MG|ML|MCG|G)\b(?:[^\n]*)"
        ),
        re.compile(
            r"(?i)\b[A-Za-z][A-Za-z0-9()./+\-\s]{2,}\b(?:\d+\s*(?:MG|ML|MCG|g|G))\b(?:[^\n]*)"
        ),
    ]
    MEDICINE_HINT_PATTERNS = [
        re.compile(r"(?i)\b(?:TAB|CAP|MG|ML|MCG|เม็ด|แคปซูล)\b"),
        re.compile(r"(?i)\b\d+\s*(?:MG|ML|MCG|g|G|mg|ml)\b"),
        re.compile(r"(?i)\b(?:\d+\s*(?:TAB|CAP)|(?:TAB|CAP)\s*\d+)\b"),
    ]
    USAGE_PATTERNS = [
        re.compile(
            r"(?i)\b(?:รับประทาน|ทานครั้งละ|กินครั้งละ|ครั้งละ|วันละ|ก่อนอาหาร|หลังอาหาร|พร้อมอาหาร|เช้า|กลางวัน|เย็น|ก่อนนอน|ทุก\s*\d+|ชั่วโมง|เวลามีอาการ|เวลามีไข้|เจ็บคอ|ปวด)\b"
        ),
    ]
    NOTE_PATTERNS = [
        re.compile(r"(?i)\b(?:ยาแก้แพ้|ยาแก้ปวด|ลดไข้|ลดไช้|แก้ปวด|แก้แพ้|ลคน้ำมูก|น้ำมูก)\b"),
        re.compile(r"(?i)\b(?:hospital|university|โรงพยาบาล|hn)\b"),
    ]

    def extract(
        self,
        raw_text: str,
        text_regions: list[dict[str, Any]],
    ) -> dict[str, str]:
        lines = self._ordered_lines(raw_text, text_regions)
        return {
            "medicine_name": self._extract_medicine_name(lines),
            "usage_instruction": self._extract_usage_instruction(lines),
        }

    def _ordered_lines(
        self,
        raw_text: str,
        text_regions: list[dict[str, Any]],
    ) -> list[str]:
        if text_regions:
            sorted_regions = sorted(
                text_regions,
                key=lambda item: (
                    item.get("bbox", [0, 0, 0, 0])[1],
                    item.get("bbox", [0, 0, 0, 0])[0],
                ),
            )
            lines = [str(region.get("ocr_text", "")).strip() for region in sorted_regions]
        else:
            lines = [line.strip() for line in raw_text.splitlines()]
        return [line for line in lines if line]

    def _extract_medicine_name(self, lines: list[str]) -> str:
        candidates: list[tuple[int, int, str]] = []

        for index, line in enumerate(lines):
            normalized_line = self._normalize_line(line)
            if not normalized_line or self._is_noise_line(normalized_line):
                continue

            for pattern in self.NAME_PATTERNS:
                match = pattern.search(normalized_line)
                if not match:
                    continue
                candidate = self._normalize_candidate(match.group(1))
                score = self._score_medicine_candidate(candidate, normalized_line, index, lines) + 3
                if candidate and score > 0:
                    candidates.append((score, index, candidate))

            prefix_removed = self._strip_medicine_prefix(normalized_line)
            if prefix_removed and prefix_removed != normalized_line:
                score = self._score_medicine_candidate(prefix_removed, normalized_line, index, lines) + 2
                if prefix_removed and score > 0:
                    candidates.append((score, index, prefix_removed))

            for pattern in self.NAME_CANDIDATE_PATTERNS:
                if not pattern.search(normalized_line):
                    continue
                candidate = self._normalize_candidate(normalized_line)
                score = self._score_medicine_candidate(candidate, normalized_line, index, lines)
                if candidate and score > 0:
                    candidates.append((score, index, candidate))

            extracted_from_line = self._extract_name_from_line(normalized_line)
            if extracted_from_line:
                score = self._score_medicine_candidate(extracted_from_line, normalized_line, index, lines) + 4
                if score > 0:
                    candidates.append((score, index, extracted_from_line))

        if not candidates:
            return "ไม่พบ"

        candidates.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        return candidates[0][2] if candidates[0][2] else "ไม่พบ"

    def _extract_usage_instruction(self, lines: list[str]) -> str:
        matched_lines: list[str] = []
        active = False

        for line in lines:
            normalized_line = self._normalize_line(line)
            if not normalized_line or self._is_noise_line(normalized_line):
                continue

            if self._is_usage_instruction_line(normalized_line):
                cleaned = self._clean_usage_line(normalized_line)
                if cleaned:
                    if not self._looks_like_quantity_only(cleaned):
                        matched_lines.append(cleaned)
                    active = True
                continue

            if active and self._looks_like_usage_continuation(normalized_line):
                cleaned = self._clean_usage_line(normalized_line)
                if cleaned and not self._looks_like_quantity_only(cleaned):
                    matched_lines.append(cleaned)
                continue

            if active and self._looks_like_medicine_note(normalized_line):
                continue

            if active and not self._looks_like_usage_continuation(normalized_line):
                active = False

        unique_lines: list[str] = []
        for line in matched_lines:
            if line not in unique_lines:
                unique_lines.append(line)

        return " ".join(unique_lines) if unique_lines else "ไม่พบ"

    def _normalize_line(self, text: str) -> str:
        cleaned = str(text or "").strip()
        cleaned = cleaned.replace("：", ":")
        cleaned = self._normalize_ocr_typos(cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    def _normalize_ocr_typos(self, text: str) -> str:
        cleaned = str(text or "")
        replacements = [
            ("ก่อนขางาร", "ก่อนอาหาร"),
            ("ขางาร", "อาหาร"),
            ("อาหา ", "อาหาร "),
            ("อาหา$", "อาหาร"),
            ("ทานครั้งละ", "รับประทานครั้งละ"),
            ("กินครั้งละ", "รับประทานครั้งละ"),
            ("ม0 เม็ด", ""),
            ("0 pmoocim Su mg", ""),
        ]
        for old, new in replacements:
            cleaned = cleaned.replace(old, new)
        cleaned = re.sub(r"(?i)\b(?:ก่อน)?ขางาร\b", "อาหาร", cleaned)
        cleaned = re.sub(r"(?i)\b(?:ก่อน)?อาหา\b", "อาหาร", cleaned)
        return cleaned

    def _normalize_candidate(self, text: str) -> str:
        candidate = str(text or "").strip()
        candidate = re.sub(r"^[\s:.\-]+", "", candidate)
        candidate = re.sub(r"^\((.*)\)$", r"\1", candidate).strip()
        candidate = re.sub(r"^\bยา\b\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*[\(\[].*$", "", candidate).strip()
        candidate = re.sub(r"\b\d+\s*(?:TAB|CAP|MG|ML|MCG|G)\b.*$", "", candidate, flags=re.IGNORECASE).strip()
        candidate = re.sub(r"(?i)\b(?:TAB|CAP|MG|ML|MCG|G)\b", lambda m: f" {m.group(0).upper()} ", candidate)
        candidate = re.sub(r"\s+", " ", candidate).strip()
        candidate = re.sub(r"\s+", " ", candidate).strip()
        return candidate

    def _is_noise_line(self, text: str) -> bool:
        lowered = text.casefold().strip()
        if not lowered:
            return True
        if any(pattern.match(text) for pattern in self.NOISE_PATTERNS):
            return True
        if re.search(r"\b(?:ชื่อ|dob|age|patient|โรงพยาบาล|hospital|university)\b", lowered, re.IGNORECASE):
            return True
        return False

    def _strip_medicine_prefix(self, text: str) -> str:
        stripped = re.sub(r"^(?:ชื่อยา|ยา)\s*[:\-]?\s*", "", text, flags=re.IGNORECASE).strip()
        return self._normalize_candidate(stripped)

    def _extract_name_from_line(self, text: str) -> str:
        line = str(text or "").strip()
        if not line:
            return ""
        line = line.replace("<", " ")
        line = re.sub(r"\s+", " ", line).strip()
        for pattern in self.NAME_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            if match.lastindex and match.lastindex >= 2:
                candidate = f"{match.group(1)} {match.group(2)}"
            else:
                candidate = match.group(1)
            candidate = self._normalize_candidate(candidate)
            if candidate and not self._looks_like_medicine_note(candidate):
                return candidate
        for pattern in self.NAME_CANDIDATE_PATTERNS:
            match = pattern.search(line)
            if match:
                candidate = self._normalize_candidate(match.group(0))
                if candidate and not self._looks_like_medicine_note(candidate):
                    return candidate
        return ""

    def _score_medicine_candidate(
        self,
        candidate: str,
        source_line: str,
        index: int,
        lines: list[str],
    ) -> int:
        lowered = candidate.casefold()
        source_lowered = source_line.casefold()
        score = 0

        if self._looks_like_medicine_note(candidate):
            return 0
        if any(pattern.search(candidate) for pattern in self.MEDICINE_HINT_PATTERNS):
            score += 5
        if re.search(r"\b[A-Za-z].*\d", candidate):
            score += 3
        if re.search(r"\b(?:TAB|CAP|MG|ML|MCG)\b", candidate, re.IGNORECASE):
            score += 4
        if re.search(r"(?i)\b(?:\d+\s*(?:TAB|CAP)|(?:TAB|CAP)\s*\d+)\b", candidate):
            score += 2
        if re.search(r"\(\s*[A-Za-zก-๙0-9\- ]+\s*\)$", candidate):
            score += 1
        if source_lowered.startswith(("ยา", "ชื่อยา", "drug", "rx")):
            score += 4
        if index > 0 and self._is_usage_instruction_line(lines[index - 1]):
            score += 1
        if len(candidate) >= 5:
            score += 1
        if any(noise in lowered for noise in ("hn", "hospital", "university", "patient")):
            score -= 6
        return score

    def _has_any_keyword(self, text: str) -> bool:
        lowered = text.casefold()
        return any(keyword.casefold() in lowered for keyword in self.INSTRUCTION_KEYWORDS)

    def _is_usage_instruction_line(self, text: str) -> bool:
        return self._has_any_keyword(text) or any(
            pattern.search(text) for pattern in self.USAGE_PATTERNS
        )

    def _looks_like_usage_continuation(self, text: str) -> bool:
        lowered = text.casefold().strip()
        if not lowered:
            return False
        if any(pattern.match(text) for pattern in self.NOISE_PATTERNS):
            return False
        if self._looks_like_medicine_note(lowered):
            return False
        if lowered.startswith(("(", "-", "ทุก", "รับประทาน", "ทาน", "กิน", "ครั้งละ", "วันละ", "ก่อน", "หลัง")):
            return True
        return any(keyword.casefold() in lowered for keyword in self.CONTINUATION_KEYWORDS) or bool(
            re.search(r"\d", lowered)
        )

    def _looks_like_medicine_note(self, text: str) -> bool:
        lowered = text.casefold().strip()
        if not lowered:
            return False
        return any(pattern.search(lowered) for pattern in self.NOTE_PATTERNS)

    def _looks_like_quantity_only(self, text: str) -> bool:
        lowered = text.casefold().strip()
        if not lowered:
            return True
        return bool(
            re.fullmatch(r"\[?\s*\d+\s*(?:tab|cap|เม็ด|แผง|กล่อง)\s*\]?", lowered, flags=re.IGNORECASE)
            or re.fullmatch(r"\d+\s*(?:tab|cap|เม็ด|แผง|กล่อง)", lowered, flags=re.IGNORECASE)
        )

    def _clean_usage_line(self, text: str) -> str:
        cleaned = str(text).strip()
        if any(pattern.match(cleaned) for pattern in self.NOISE_PATTERNS):
            return ""
        cleaned = self._normalize_ocr_typos(cleaned)
        cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
        cleaned = re.sub(r"\bม0\s*เม็ด\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace("ลดไช้", "")
        cleaned = cleaned.replace("ลคน้ำมูก", "")
        cleaned = cleaned.replace("น้ำมูก", "")
        cleaned = re.sub(r"\b(?:ยาแก้แพ้|ยาแก้ปวด|ลดไข้|แก้ปวด|แก้แพ้)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
