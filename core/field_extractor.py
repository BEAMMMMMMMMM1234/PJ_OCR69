from __future__ import annotations

from pathlib import Path
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
        structured_data = self._empty_structured_data()

        if document_type == "Appointment":
            structured_data.update(
                self.appointment_extractor.extract(raw_text, text_regions)
            )
        elif document_type == "MedicineLabel":
            structured_data.update(
                self.medicine_extractor.extract(raw_text, text_regions)
            )

        return structured_data

    def _empty_structured_data(self) -> dict[str, str]:
        return {
            "appointment_date": "ไม่พบ",
            "appointment_time": "ไม่พบ",
            "preparation_instruction": "ไม่พบ",
            "medicine_name": "ไม่พบ",
            "usage_instruction": "ไม่พบ",
        }
