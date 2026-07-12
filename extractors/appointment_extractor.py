from __future__ import annotations

import logging
import re
from typing import Any

LOGGER = logging.getLogger("pj_ocr69.appointment_extractor")


class AppointmentExtractor:
    DATE_PATTERNS = [
        re.compile(r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b"),
        re.compile(r"\b\d{1,2}\s*[\/\-\.]\s*\d{1,2}\s*[\/\-\.]\s*\d{2,4}\b"),
        re.compile(
            r"\b\d{1,2}\s*(?:ม\.?ค\.?|ก\.?พ\.?|มี\.?ค\.?|เม\.?ย\.?|พ\.?ค\.?|มิ\.?ย\.?|ก\.?ค\.?|ส\.?ค\.?|ก\.?ย\.?|ต\.?ค\.?|พ\.?ย\.?|ธ\.?ค\.?|"
            r"มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*\d{2,4}\b"
        ),
        re.compile(
            r"\b(?:วัน(?:จันทร|อังคาร|พุธ|พฤหัสบดี|ศุกร์|เสาร์|อาทิตย์)|วัน[ก-ฮ]+)?(?:ที่)?\s*\d{1,2}\s*"
            r"(?:ม\.?ค\.?|ก\.?พ\.?|มี\.?ค\.?|เม\.?ย\.?|พ\.?ค\.?|มิ\.?ย\.?|ก\.?ค\.?|ส\.?ค\.?|ก\.?ย\.?|ต\.?ค\.?|พ\.?ย\.?|ธ\.?ค\.?|"
            r"มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*\d{2,4}\b"
        ),
    ]
    TIME_PATTERNS = [
        re.compile(r"\b\d{1,2}[:.]\d{2}\s*-\s*\d{1,2}[:.]\d{2}\b"),
        re.compile(r"\b\d{1,2}[:.]\d{2}\s*[-–—]\s*\d{1,2}[:.]\d{2}\b"),
        re.compile(r"\b\d{1,2}:\d-\d{1,2}\b"),
        re.compile(r"\b\d{1,2}[.]\d{2}(?:\s*น\.?)?\b"),
        re.compile(r"\b\d{1,2}[:.]\d{2}(?:\s*น\.?)?\b"),
    ]
    PREP_KEYWORDS = [
        "ข้อควรปฏิบัติ",
        "ข้อปฏิบัติ",
        "หมายเหตุ",
        "งดน้ำ",
        "งดอาหาร",
        "งดน้ำงดอาหาร",
        "ก่อนนัด",
        "หลังเที่ยงคืน",
        "หลังเวลา",
        "เจาะเลือด",
        "ตรวจเลือด",
        "เอกซเรย์",
        "x-ray",
        "นำบัตร",
        "นำยาเดิม",
        "นำผลตรวจ",
        "มาตามนัด",
        "ก่อนพบแพทย์",
        "ติดต่อ",
        "ห้องตรวจ",
        "กรุณา",
        "เตรียมตัว",
        "คำแนะนำ",
        "ห้ามรับประทาน",
        "สแกนยืนยันตัวตน",
        "รับยาต่อ",
        "แพ้ยา",
    ]
    PREP_BOUNDARY_PATTERNS = [
        re.compile(r"\b(?:fu|cbc|fbs|lipid)\b", re.IGNORECASE),
        re.compile(r"\b(?:lab|แล็บ|laboratory)\b", re.IGNORECASE),
        re.compile(r"\b(?:call center|center)\b", re.IGNORECASE),
        re.compile(r"\b(?:เบอร์|โทร|phone|tel)\b", re.IGNORECASE),
        re.compile(r"\b(?:รถมาตามนัด|เลื่อนวันนัด|วันนัดหมาย|แจ้ง)\b", re.IGNORECASE),
        re.compile(r"\b(?:ผลตรวจ|ผลการตรวจ)\b", re.IGNORECASE),
    ]
    DATE_HINTS = ["วันนัด", "วันที่นัด", "นัดวันที่", "วันที่", "วัน", "นัด", "appointment", "request", "make date"]
    TIME_HINTS = ["เวลา", "นัด", "appointment", "requested"]
    HEADER_HINTS = [
        "นัด",
        "ใบนัด",
        "นัดหมาย",
        "วันนัด",
        "โรงพยาบาล",
        "รพ.",
        "คลินิก",
        "แผนก",
        "ผู้ป่วย",
        "วันที่",
        "เวลา",
        "appointment",
        "hospital",
        "clinic",
        "date",
        "time",
        "patient",
    ]

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

        normalized: list[str] = []
        for line in lines:
            normalized_line = self._normalize_line(line)
            if normalized_line:
                normalized.append(normalized_line)

        LOGGER.debug("_ordered_lines -> normalized (%d): %s", len(normalized), normalized)
        return normalized

    def _extract_appointment_date(self, lines: list[str]) -> str:
        for index, line in enumerate(lines):
            if self._has_any_hint(line, self.DATE_HINTS):
                matched = self._normalize_date(self._find_first_match(line, self.DATE_PATTERNS))
                if matched:
                    return matched
                if index + 1 < len(lines):
                    matched = self._normalize_date(self._find_first_match(lines[index + 1], self.DATE_PATTERNS))
                    if matched:
                        return matched

        for line in lines:
            matched = self._normalize_date(self._find_first_match(line, self.DATE_PATTERNS))
            if matched:
                return matched

        return "ไม่พบ"

    def _extract_appointment_time(self, lines: list[str]) -> str:
        for index, line in enumerate(lines):
            if self._has_any_hint(line, self.TIME_HINTS):
                matched = self._normalize_time(self._find_first_match(line, self.TIME_PATTERNS))
                if matched:
                    return matched
                if index + 1 < len(lines):
                    matched = self._normalize_time(self._find_first_match(lines[index + 1], self.TIME_PATTERNS))
                    if matched:
                        return matched

        for line in lines:
            matched = self._normalize_time(self._find_first_match(line, self.TIME_PATTERNS))
            if matched:
                return matched

        for line in lines:
            lowered = line.casefold()
            if any(keyword in lowered for keyword in ("ช่วงเช้า", "ช่วงบ่าย", "เช้า", "บ่าย", "เย็น")):
                return self._clean_instruction_line(line)

        return "ไม่พบ"

    def _extract_preparation_instruction(self, lines: list[str]) -> str:
        if not lines:
            return "ไม่พบ"

        start_index = self._find_instruction_start(lines)
        LOGGER.debug("_extract_preparation_instruction -> start_index: %s", start_index)
        if start_index is None:
            return "ไม่พบ"

        collected: list[str] = []
        first_line = self._normalize_line(lines[start_index])
        LOGGER.debug("_extract_preparation_instruction -> first_line: %s", first_line)
        if first_line and not self._is_instruction_header(first_line):
            if self._looks_like_instruction_content(first_line):
                collected.append(first_line)

        for index in range(start_index + 1, len(lines)):
            line = self._normalize_line(lines[index])
            if not line:
                continue
            if self._is_instruction_boundary(line):
                break
            if self._looks_like_instruction_continuation(line):
                if line not in collected:
                    collected.append(line)
                continue
            if self._has_any_hint(line, self.PREP_KEYWORDS):
                if line not in collected:
                    collected.append(line)
                continue
            if collected and self._looks_like_preparation_continuation(line):
                if line not in collected:
                    collected.append(line)
                continue
            if collected:
                break

        unique_lines: list[str] = []
        for line in collected:
            if line not in unique_lines:
                unique_lines.append(line)

        LOGGER.debug("_extract_preparation_instruction -> collected unique: %s", unique_lines)
        return " ".join(unique_lines) if unique_lines else "ไม่พบ"

    def _find_instruction_start(self, lines: list[str]) -> int | None:
        for index, line in enumerate(lines):
            LOGGER.debug("_find_instruction_start checking index=%d line=%s", index, line)
            if self._is_instruction_header(line):
                LOGGER.debug("_find_instruction_start -> matched is_instruction_header at %d", index)
                return index
            if self._looks_like_instruction_content(line):
                LOGGER.debug("_find_instruction_start -> matched looks_like_instruction_content at %d", index)
                return index
        LOGGER.debug("_find_instruction_start -> no start found")
        return None

    def _find_first_match(self, text: str, patterns: list[re.Pattern[str]]) -> str:
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return match.group(0).strip()
        return ""

    def _has_any_hint(self, text: str, hints: list[str]) -> bool:
        lowered = text.casefold()
        return any(hint.casefold() in lowered for hint in hints)

    def _is_instruction_header(self, text: str) -> bool:
        lowered = text.casefold().strip()
        return lowered in {"คำสั่งแพทย์", "คำสั่ง", "instruction", "instructions"}

    def _looks_like_instruction_content(self, text: str) -> bool:
        lowered = text.casefold()
        if self._is_instruction_header(lowered):
            return False
        if self._is_instruction_boundary(lowered):
            return False
        if self._looks_like_header(lowered):
            return False
        # Avoid matching recipient/name lines that may contain 'ผู้รับ' or honorifics
        if any(h in lowered for h in ("ผู้รับ", "นาย", "นาง", "น.ส", "นางสาว", "ดร")):
            return False

        return bool(
            self._has_any_hint(text, self.PREP_KEYWORDS)
            or any(token in lowered for token in ("งด", "ก่อน", "หลัง", "เตรียม", "กรุณา", "รับ", "ห้าม", "คำแนะนำ"))
        )

    def _looks_like_header(self, text: str) -> bool:
        if text is None:
            return False
        lowered = str(text).casefold().strip()
        if not lowered:
            return False

        # Normalize common OCR mistakes for header matching
        lowered = lowered.replace("โรงบาล", "โรงพยาบาล")
        lowered = lowered.replace("รพ", "รพ.")
        lowered = lowered.replace("นด", "นัด")
        lowered = lowered.replace("วนั", "วัน")
        lowered = lowered.replace("ดเวล", "เวลา")
        lowered = lowered.replace("แผนก", "แผนก")

        # If line contains any strong header hint, treat as header-like
        if self._has_any_hint(lowered, self.HEADER_HINTS):
            return True

        # Recognize common header phrases with fuzzy-ish matching
        if any(keyword in lowered for keyword in ("นัด", "วันที่", "เวลา", "โรงพยาบาล", "คลินิก", "ผู้ป่วย", "appointment", "hospital", "clinic", "date", "time", "patient")):
            return True

        # Avoid matching short unrelated lines
        if len(lowered) <= 3:
            return False

        return False

    def _looks_like_preparation_continuation(self, text: str) -> bool:
        lowered = text.casefold().strip()
        if not lowered:
            return False
        if self._looks_like_header(lowered):
            return False
        if self._is_instruction_boundary(lowered):
            return False
        return lowered.startswith(
            ("(", "-", "งด", "ก่อน", "เตรียม", "คำแนะนำ", "และ", "หรือ", "รับ", "นำ", "ห้าม", "ติดต่อ", "กรุณา")
        )

    def _looks_like_instruction_continuation(self, text: str) -> bool:
        if self._is_instruction_boundary(text):
            return False
        if self._looks_like_header(text):
            return False
        if self._has_any_hint(text, self.PREP_KEYWORDS):
            return True
        lowered = text.casefold()
        return bool(
            any(token in lowered for token in ("งด", "ก่อน", "หลัง", "เตรียม", "กรุณา", "รับ", "ห้าม", "คำแนะนำ", "และ", "หรือ"))
        )

    def _is_instruction_boundary(self, text: str) -> bool:
        lowered = text.casefold().strip()
        if not lowered:
            return False
        for pattern in self.PREP_BOUNDARY_PATTERNS:
            if pattern.search(lowered):
                return True
        return False

    def _normalize_line(self, text: str) -> str:
        cleaned = str(text or "").strip()
        cleaned = cleaned.replace("“", "").replace("”", "").replace('"', "")
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = self._normalize_ocr_text(cleaned)
        return cleaned.strip()

    def _normalize_ocr_text(self, text: str) -> str:
        cleaned = str(text or "")
        cleaned = cleaned.replace("งดน้ำงดอาหา", "งดน้ำงดอาหาร")
        cleaned = re.sub(r"ง[กข]อาหาร", "งดอาหาร", cleaned)
        cleaned = re.sub(r"\bเทียงคืน\b", "เที่ยงคืน", cleaned)
        cleaned = re.sub(r"\b240\s*น\.?\b", "24.00 น.", cleaned)
        cleaned = re.sub(r"\bเวลา\s*:\s*", "เวลา ", cleaned)
        cleaned = re.sub(r"\b(\d{1,2}):(\d)-(\d{1,2})\b", lambda m: f"{int(m.group(1)):02d}:{int(m.group(2)):02d}-{int(m.group(3)):02d}:00", cleaned)
        cleaned = re.sub(r"\b(\d{1,2}):(\d{2})\s*น\.?", r"\1:\2 น", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _clean_instruction_line(self, text: str) -> str:
        return self._normalize_line(text)

    def _normalize_date(self, text: str) -> str:
        if not text:
            return ""
        cleaned = str(text).strip()
        cleaned = re.sub(r"\bวัน(?:จันทร|อังคาร|พุธ|พฤหัสบดี|ศุกร์|เสาร์|อาทิตย์)\s*ที่?\s*", "", cleaned)
        cleaned = re.sub(r"\bวัน[ก-ฮ]+\s*ที่?\s*", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _normalize_time(self, text: str) -> str:
        if not text:
            return ""
        cleaned = str(text).strip()
        cleaned = re.sub(r"\bเวลา\s*[:：]?\s*", "", cleaned)
        cleaned = re.sub(
            r"\b(\d{1,2})\s*[:.]\s*(\d{1})\s*[-–—]\s*(\d{1,2})\b",
            lambda m: f"{int(m.group(1)):02d}:{int(m.group(2)):02d}-{int(m.group(3)):02d}:00",
            cleaned,
        )
        cleaned = re.sub(r"\b(\d{1,2})\s*[.]\s*(\d{2})\s*น\.?", r"\1.\2 น", cleaned)
        cleaned = re.sub(r"\b(\d{1,2})\s*[:.]\s*(\d{2})\s*น\.?", r"\1:\2 น", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
