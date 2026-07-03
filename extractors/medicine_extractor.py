from __future__ import annotations

import re
from typing import Any


class MedicineExtractor:
    INSTRUCTION_KEYWORDS = [
        "วิธีใช้",
        "วิธีรับประทาน",
        "รับประทาน",
        "ครั้งละ",
        "วันละ",
        "ก่อนอาหาร",
        "หลังอาหาร",
    ]
    NAME_PATTERNS = [
        re.compile(r"^(?:ชื่อยา|ยา)\s*[:\-]?\s*(.+)$"),
        re.compile(r"^(?:Rx|Drug)\s*[:\-]?\s*(.+)$", re.IGNORECASE),
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
        for index, line in enumerate(lines):
            for pattern in self.NAME_PATTERNS:
                match = pattern.search(line)
                if match:
                    candidate = match.group(1).strip()
                    return candidate if candidate else "ไม่พบ"

            lowered = line.casefold()
            if lowered.startswith("ยา") and ":" in line:
                candidate = line.split(":", 1)[1].strip()
                if candidate:
                    return candidate

        return "ไม่พบ"

    def _extract_usage_instruction(self, lines: list[str]) -> str:
        matched_lines: list[str] = []
        for index, line in enumerate(lines):
            if self._has_any_keyword(line):
                matched_lines.append(line)
                if index + 1 < len(lines):
                    next_line = lines[index + 1]
                    if self._looks_like_usage_continuation(next_line):
                        matched_lines.append(next_line)

        unique_lines: list[str] = []
        for line in matched_lines:
            if line not in unique_lines:
                unique_lines.append(line)

        return "\n".join(unique_lines) if unique_lines else "ไม่พบ"

    def _has_any_keyword(self, text: str) -> bool:
        lowered = text.casefold()
        return any(keyword.casefold() in lowered for keyword in self.INSTRUCTION_KEYWORDS)

    def _looks_like_usage_continuation(self, text: str) -> bool:
        lowered = text.casefold().strip()
        if not lowered:
            return False
        if lowered.startswith(("(", "-", "ทุก", "รับประทาน", "ทาน", "กิน", "ครั้งละ", "วันละ", "ก่อน", "หลัง")):
            return True
        return bool(re.search(r"\d", lowered))
