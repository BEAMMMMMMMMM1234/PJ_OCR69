from __future__ import annotations

from typing import Any


class GemmaFormatter:
    def format(
        self,
        document_type: str,
        validated_data: dict[str, Any],
    ) -> dict[str, Any]:
        if document_type == "Appointment":
            return {
                "appointment_date": validated_data.get("appointment_date", "ไม่พบ"),
                "appointment_time": validated_data.get("appointment_time", "ไม่พบ"),
                "preparation_instruction": validated_data.get(
                    "preparation_instruction", "ไม่พบ"
                ),
            }
        if document_type == "MedicineLabel":
            return {
                "medicine_name": validated_data.get("medicine_name", "ไม่พบ"),
                "usage_instruction": validated_data.get("usage_instruction", "ไม่พบ"),
            }
        return {}
