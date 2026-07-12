from __future__ import annotations

from typing import Any


SCHEMA_FIELDS = {
    "Appointment": ("appointment_date", "appointment_time", "preparation_instruction"),
    "MedicineLabel": ("medicine_name", "usage_instruction"),
}


class FinalOutputFormatter:
    def format(
        self,
        status: str,
        document_type: str,
        cleaned_data: dict[str, Any] | None,
        error: str | None,
    ) -> dict[str, Any]:
        if status != "success":
            return {
                "status": "failed",
                "document_type": "Unknown",
                "data": {},
                "error": error or "pipeline failed",
            }

        document_type = document_type if document_type in SCHEMA_FIELDS else "Unknown"
        if document_type == "Unknown":
            return {
                "status": "success",
                "document_type": "Unknown",
                "data": {},
                "error": error,
            }

        data = cleaned_data or {}
        selected: dict[str, Any] = {}
        for field in SCHEMA_FIELDS[document_type]:
            value = data.get(field, "ไม่พบ")
            if value in (None, ""):
                value = "ไม่พบ"
            selected[field] = value

        result = {
            "status": "success",
            "document_type": document_type,
            "data": selected,
        }
        # Only include error field if there actually is an error
        if error:
            result["error"] = error
        return result
