from __future__ import annotations

import re
from typing import Any


class DataValidator:
    def validate(
        self,
        document_type: str,
        structured_data: dict[str, Any],
    ) -> dict[str, Any]:
        if document_type == "Appointment":
            validated = self._validate_appointment(structured_data)
        elif document_type == "MedicineLabel":
            validated = self._validate_medicine(structured_data)
        else:
            return {}

        return self._safe_validate(structured_data, validated)

    def _validate_appointment(self, structured_data: dict[str, Any]) -> dict[str, str]:
        return {
            "appointment_date": self._normalize_text(
                structured_data.get("appointment_date", "ไม่พบ")
            ),
            "appointment_time": self._normalize_appointment_time(
                structured_data.get("appointment_time", "ไม่พบ")
            ),
            "preparation_instruction": self._normalize_appointment_instruction(
                structured_data.get("preparation_instruction", "ไม่พบ")
            ),
        }

    def _validate_medicine(self, structured_data: dict[str, Any]) -> dict[str, str]:
        return {
            "medicine_name": self._normalize_text(structured_data.get("medicine_name", "ไม่พบ")),
            "usage_instruction": self._normalize_medicine_instruction(
                structured_data.get("usage_instruction", "ไม่พบ")
            ),
        }

    def _safe_validate(
        self,
        structured_data: dict[str, Any],
        validated_data: dict[str, Any],
    ) -> dict[str, Any]:
        safe_data = dict(validated_data)
        for field, original_value in structured_data.items():
            original_text = self._normalize_text(str(original_value))
            validated_text = self._normalize_text(str(safe_data.get(field, "ไม่พบ")))

            if original_text != "ไม่พบ" and validated_text == "ไม่พบ":
                safe_data[field] = original_text
                continue

            if original_text != "ไม่พบ" and not validated_text:
                safe_data[field] = original_text
                continue

            if field == "medicine_name" and self._looks_like_medicine_name(original_text):
                if validated_text == "ไม่พบ":
                    safe_data[field] = original_text
                continue

            if field == "usage_instruction" and self._looks_like_usage_instruction(original_text):
                if validated_text == "ไม่พบ":
                    safe_data[field] = original_text

        return safe_data

    def _normalize_text(self, value: str) -> str:
        if value == "ไม่พบ":
            return value
        normalized = " ".join(str(value).split())
        return normalized if normalized else "ไม่พบ"

    def _normalize_appointment_instruction(self, value: str) -> str:
        if value == "ไม่พบ":
            return value

        normalized = self._normalize_text(value)
        normalized = normalized.replace("งดน้ำงดอาหา", "งดน้ำงดอาหาร")
        normalized = normalized.replace("งคอาหาร", "งดอาหาร")
        normalized = re.sub(r"งดน้ำงดอาหารร+", "งดน้ำงดอาหาร", normalized)
        normalized = normalized.replace("เทียงคืน", "เที่ยงคืน")
        normalized = normalized.replace("ลัง 0 .", "หลัง")
        normalized = re.sub(r"(?<!ห)ลัง", "หลัง", normalized)
        normalized = self._normalize_time_text(normalized)
        normalized = re.sub(r"หลังเวลา\s*240\s*น\.?", "หลังเวลา 24.00 น.", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized if normalized else "ไม่พบ"

    def _normalize_medicine_instruction(self, value: str) -> str:
        if value == "ไม่พบ":
            return value

        normalized = self._normalize_text(value)
        normalized = normalized.replace("ครัง", "ครั้ง")
        normalized = normalized.replace("เมด", "เม็ด")
        normalized = normalized.replace("หลงอาหาร", "หลังอาหาร")
        normalized = re.sub(r"\[[^\]]*\]", "", normalized)
        normalized = re.sub(r"\bม0\s*เม็ด\b", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"^\s*\d+\s*(?:TAB|CAP|เม็ด)\s*$", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bจำนวน\b.*?(?=$|\s{2,})", "", normalized)
        normalized = re.sub(r"\bคงเหลือ\b.*?(?=$|\s{2,})", "", normalized)
        normalized = normalized.replace("ลดไช้", "")
        normalized = normalized.replace("ลคน้ำมูก", "")
        normalized = normalized.replace("น้ำมูก", "")
        normalized = re.sub(r"\b(?:ยาแก้แพ้|ยาแก้ปวด|ลดไข้|แก้ปวด|แก้แพ้)\b", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized if normalized else "ไม่พบ"

    def _normalize_appointment_time(self, value: str) -> str:
        if value == "ไม่พบ":
            return value

        normalized = self._normalize_text(value)
        normalized = self._normalize_time_text(normalized)
        normalized = re.sub(r"^\s*เวลา\s+", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized if normalized else "ไม่พบ"

    def _normalize_time_text(self, value: str) -> str:
        normalized = value
        normalized = re.sub(
            r"\b(\d{1,2}):(\d)-(\d{1,2})\b",
            lambda match: f"{int(match.group(1)):02d}:{int(match.group(2)):02d}-{int(match.group(3)):02d}:00",
            normalized,
        )
        normalized = re.sub(r"\b(\d{1,2}):(\d{2})\s*น\.?", r"\1:\2 น", normalized)
        normalized = re.sub(r"\bเวลา\s*:\s*", "เวลา ", normalized)
        return normalized

    def _looks_like_medicine_name(self, value: str) -> bool:
        lowered = value.casefold()
        return bool(
            re.search(r"\b(?:tab|cap|mg|ml|mcg|เม็ด|แคปซูล)\b", lowered)
            or re.search(r"\b[A-Za-z][A-Za-z0-9()./+\-\s]*\d", value)
        )

    def _looks_like_usage_instruction(self, value: str) -> bool:
        lowered = value.casefold()
        return any(
            keyword in lowered
            for keyword in [
                "รับประทาน",
                "ครั้งละ",
                "วันละ",
                "ก่อนอาหาร",
                "หลังอาหาร",
                "เช้า",
                "กลางวัน",
                "เย็น",
                "ก่อนนอน",
                "ทุก",
                "ชั่วโมง",
                "เวลามีไข้",
                "เวลามีอาการ",
                "ปวด",
            ]
        )
