from __future__ import annotations

from typing import Any

from extractors.appointment_extractor import AppointmentExtractor
from extractors.medicine_extractor import MedicineExtractor


class FieldExtractor:
    def __init__(self) -> None:
        self.appointment_extractor = AppointmentExtractor()
        self.medicine_extractor = MedicineExtractor()

    def extract(
        self,
        document_type: str,
        raw_text: str,
        text_regions: list[dict[str, Any]],
    ) -> dict[str, str]:
        if document_type == "Appointment":
            return self._appointment_schema(
                self.appointment_extractor.extract(raw_text, text_regions)
            )
        elif document_type == "MedicineLabel":
            return self._medicine_schema(
                self.medicine_extractor.extract(raw_text, text_regions)
            )

        return {}

    def _appointment_schema(self, data: dict[str, str]) -> dict[str, str]:
        return {
            "appointment_date": data.get("appointment_date", "ไม่พบ"),
            "appointment_time": data.get("appointment_time", "ไม่พบ"),
            "preparation_instruction": data.get("preparation_instruction", "ไม่พบ"),
        }

    def _medicine_schema(self, data: dict[str, str]) -> dict[str, str]:
        return {
            "medicine_name": data.get("medicine_name", "ไม่พบ"),
            "usage_instruction": data.get("usage_instruction", "ไม่พบ"),
        }
