from __future__ import annotations

import re
from typing import Any


class AppointmentExtractor:
    DATE_PATTERNS = [
        re.compile(r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b"),
        re.compile(
            r"\b\d{1,2}\s*(?:ม\.?ค\.?|ก\.?พ\.?|มี\.?ค\.?|เม\.?ย\.?|พ\.?ค\.?|มิ\.?ย\.?|ก\.?ค\.?|ส\.?ค\.?|ก\.?ย\.?|ต\.?ค\.?|พ\.?ย\.?|ธ\.?ค\.?|"
            r"มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*\d{2,4}\b"
        ),
    ]
    TIME_PATTERNS = [
        re.compile(r"\b\d{1,2}[:.]\d{2}\s*-\s*\d{1,2}[:.]\d{2}\b"),
        re.compile(r"\b\d{1,2}[:.]\d{2}(?:\s*น\.?)?\b"),
    ]
    PREP_KEYWORDS = [
        "งดน้ำ",
        "งดอาหาร",
        "ก่อนนัด",
        "ข้อปฏิบัติ",
        "เตรียมตัว",
        "คำแนะนำ",
    ]
    DATE_HINTS = ["วันนัด", "วันที่", "วัน", "นัด"]

    def extract(
        self,
        raw_text: str,
        text_regions: list[dict[str, Any]],
    ) -> dict[str, str]:
        lines = self._ordered_lines(raw_text, text_regions)
        return {
            "appointment_date": self._extract_appointment_date(lines),
            "appointment_time": self._extract_appointment_time(lines),
            "preparation_instruction": self._extract_preparation_instruction(lines),
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

    def _extract_appointment_date(self, lines: list[str]) -> str:
        for index, line in enumerate(lines):
            if self._has_any_hint(line, self.DATE_HINTS):
                matched = self._find_first_match(line, self.DATE_PATTERNS)
                if matched:
                    return matched
                if index + 1 < len(lines):
                    matched = self._find_first_match(lines[index + 1], self.DATE_PATTERNS)
                    if matched:
                        return matched

        for line in lines:
            matched = self._find_first_match(line, self.DATE_PATTERNS)
            if matched:
                return matched

        return "ไม่พบ"

    def _extract_appointment_time(self, lines: list[str]) -> str:
        for index, line in enumerate(lines):
            if "เวลา" in line:
                matched = self._find_first_match(line, self.TIME_PATTERNS)
                if matched:
                    return matched
                if index + 1 < len(lines):
                    matched = self._find_first_match(lines[index + 1], self.TIME_PATTERNS)
                    if matched:
                        return matched

        for line in lines:
            matched = self._find_first_match(line, self.TIME_PATTERNS)
            if matched:
                return matched

        return "ไม่พบ"

    def _extract_preparation_instruction(self, lines: list[str]) -> str:
        matched_lines: list[str] = []
        for index, line in enumerate(lines):
            if self._has_any_hint(line, self.PREP_KEYWORDS):
                matched_lines.append(line)
                if index + 1 < len(lines):
                    next_line = lines[index + 1]
                    if self._looks_like_preparation_continuation(next_line):
                        matched_lines.append(next_line)

        unique_lines = []
        for line in matched_lines:
            if line not in unique_lines:
                unique_lines.append(line)

        return "\n".join(unique_lines) if unique_lines else "ไม่พบ"

    def _find_first_match(self, text: str, patterns: list[re.Pattern[str]]) -> str:
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return match.group(0).strip()
        return ""

    def _has_any_hint(self, text: str, hints: list[str]) -> bool:
        lowered = text.casefold()
        return any(hint.casefold() in lowered for hint in hints)

    def _looks_like_header(self, text: str) -> bool:
        lowered = text.casefold()
        header_hints = [
            "hn",
            "ชื่อ",
            "นามสกุล",
            "แผนก",
            "ผู้พิมพ",
            "โทร",
            "บัตร",
            "แพทย์",
            "วันที่",
            "เวลา",
        ]
        return any(hint in lowered for hint in header_hints)

    def _looks_like_preparation_continuation(self, text: str) -> bool:
        lowered = text.casefold().strip()
        if not lowered:
            return False
        if self._looks_like_header(lowered):
            return False
        return lowered.startswith(("(", "-", "งด", "ก่อน", "เตรียม", "คำแนะนำ", "และ", "หรือ"))
