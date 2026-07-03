from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DataValidator:
    def validate(
        self,
        document_type: str,
        structured_data: dict[str, Any],
    ) -> dict[str, Any]:
        validated_data = deepcopy(structured_data)

        if not validated_data:
            return validated_data

        if document_type == "Appointment":
            validated_data["appointment_date"] = self._normalize_text(
                validated_data.get("appointment_date", "ไม่พบ")
            )
            validated_data["appointment_time"] = self._normalize_text(
                validated_data.get("appointment_time", "ไม่พบ")
            )
            validated_data["preparation_instruction"] = self._normalize_appointment_instruction(
                validated_data.get("preparation_instruction", "ไม่พบ")
            )
        elif document_type == "MedicineLabel":
            validated_data["medicine_name"] = self._normalize_text(
                validated_data.get("medicine_name", "ไม่พบ")
            )
            validated_data["usage_instruction"] = self._normalize_medicine_instruction(
                validated_data.get("usage_instruction", "ไม่พบ")
            )

        return validated_data

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
