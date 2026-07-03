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
            return self._validate_appointment(structured_data)
        elif document_type == "MedicineLabel":
            return self._validate_medicine(structured_data)

        return {}

    def _validate_appointment(self, structured_data: dict[str, Any]) -> dict[str, str]:
        return {
            "appointment_date": self._normalize_text(
                structured_data.get("appointment_date", "ไม่พบ")
            ),
            "appointment_time": self._normalize_text(
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

    def _normalize_text(self, value: str) -> str:
        if value == "ไม่พบ":
            return value
        normalized = " ".join(str(value).split())
        return normalized if normalized else "ไม่พบ"

    def _normalize_appointment_instruction(self, value: str) -> str:
        if value == "ไม่พบ":
            return value

        normalized = self._normalize_text(value)
        normalized = normalized.replace("งคอาหาร", "งดอาหาร")
        normalized = normalized.replace("เทียงคืน", "เที่ยงคืน")
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
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized if normalized else "ไม่พบ"
