from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.validator import DataValidator
from extractors.appointment_extractor import AppointmentExtractor
from extractors.medicine_extractor import MedicineExtractor

OCR_EVIDENCE_DIR = PROJECT_ROOT / "runtime" / "debug" / "ocr_evidence"


def _assert_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}\nexpected: {expected!r}\nactual:   {actual!r}")


def _load_fixture(stem: str) -> dict[str, Any]:
    path = OCR_EVIDENCE_DIR / f"{stem}_ocr.json"
    if not path.exists():
        raise FileNotFoundError(f"missing OCR evidence: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _has_date_evidence(raw_text: str) -> bool:
    patterns = [
        r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b",
        r"\b\d{1,2}\s*(?:ม\.?ค\.?|ก\.?พ\.?|มี\.?ค\.?|เม\.?ย\.?|พ\.?ค\.?|มิ\.?ย\.?|ก\.?ค\.?|ส\.?ค\.?|ก\.?ย\.?|ต\.?ค\.?|พ\.?ย\.?|ธ\.?ค\.?|"
        r"มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*\d{2,4}\b",
        r"\bวันที่นัด\b",
        r"\bนัดวันที่\b",
        r"\bวันนัด\b",
        r"\bวันที่\b",
    ]
    return any(re.search(pattern, raw_text) for pattern in patterns)


def _has_time_evidence(raw_text: str) -> bool:
    patterns = [
        r"\b\d{1,2}[:.]\d{2}\s*(?:น\.?)?\b",
        r"\b\d{1,2}[:.]\d{1}\s*-\s*\d{1,2}\b",
        r"\bช่วงเช้า\b",
        r"\bช่วงบ่าย\b",
        r"\bเวลา\b",
    ]
    return any(re.search(pattern, raw_text) for pattern in patterns)


def _has_preparation_evidence(raw_text: str) -> bool:
    keywords = [
        "ข้อควรปฏิบัติ",
        "ข้อปฏิบัติ",
        "งดน้ำ",
        "งดอาหาร",
        "งดน้ำงดอาหาร",
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
        "ห้ามรับประทาน",
        "สแกนยืนยันตัวตน",
        "รับยาต่อ",
        "แพ้ยา",
    ]
    lowered = raw_text.casefold()
    return any(keyword.casefold() in lowered for keyword in keywords)


def _has_medicine_name_evidence(raw_text: str) -> bool:
    return bool(
        "ยา" in raw_text
        or "ชื่อยา" in raw_text
        or re.search(r"(?i)\b[A-Za-z][A-Za-z0-9()./+\-]{2,}\s*(?:TAB|CAP|MG|ML|MCG|G)\b", raw_text)
        or re.search(r"(?i)\b[A-Za-z][A-Za-z0-9()./+\-]{2,}\s*\d+\s*(?:MG|ML|MCG|G)\b", raw_text)
        or "เม็ด" in raw_text
    )


def _has_usage_evidence(raw_text: str) -> bool:
    lowered = raw_text.casefold()
    return any(
        keyword in lowered
        for keyword in [
            "วิธีใช้",
            "วิธีรับประทาน",
            "รับประทาน",
            "ทานครั้งละ",
            "กินครั้งละ",
            "ครั้งละ",
            "วันละ",
            "ก่อนอาหาร",
            "หลังอาหาร",
            "พร้อมอาหาร",
            "เช้า",
            "กลางวัน",
            "เย็น",
            "ก่อนนอน",
            "ทุก",
            "ชั่วโมง",
            "เวลามีอาการ",
            "เวลามีไข้",
            "เจ็บคอ",
            "ปวด",
            "ก่อนขางาร",
            "ก่อนอาหาร",
            "ทานครั้งละ",
            "กินครั้งละ",
            "ม0 เม็ด",
        ]
    )


def _note(case_name: str, message: str) -> None:
    print(f"[NOTE] {case_name}: {message}")


def _require_present(case_name: str, field_name: str, has_evidence: bool, value: str) -> None:
    if has_evidence and value == "ไม่พบ":
        raise AssertionError(f"{case_name} {field_name} should be found: {value!r}")
    if not has_evidence:
        _note(case_name, f"{field_name} evidence missing in OCR")


def main() -> int:
    appointment_extractor = AppointmentExtractor()
    medicine_extractor = MedicineExtractor()
    validator = DataValidator()

    a02 = _load_fixture("A02")
    a02_result = appointment_extractor.extract(a02["raw_text"], a02.get("text_regions", []))
    _require_present("A02", "preparation_instruction", _has_preparation_evidence(a02["raw_text"]), a02_result["preparation_instruction"])

    a04 = _load_fixture("A04")
    a04_result = appointment_extractor.extract(a04["raw_text"], a04.get("text_regions", []))
    _require_present("A04", "preparation_instruction", _has_preparation_evidence(a04["raw_text"]), a04_result["preparation_instruction"])

    a05 = _load_fixture("A05")
    a05_result = appointment_extractor.extract(a05["raw_text"], a05.get("text_regions", []))
    _require_present("A05", "appointment_date", _has_date_evidence(a05["raw_text"]), a05_result["appointment_date"])
    _require_present("A05", "appointment_time", _has_time_evidence(a05["raw_text"]), a05_result["appointment_time"])
    _require_present("A05", "preparation_instruction", _has_preparation_evidence(a05["raw_text"]), a05_result["preparation_instruction"])

    m100 = _load_fixture("100")
    m100_result = medicine_extractor.extract(m100["raw_text"], m100.get("text_regions", []))
    _require_present("100", "medicine_name", _has_medicine_name_evidence(m100["raw_text"]), m100_result["medicine_name"])

    m101 = _load_fixture("101")
    m101_result = medicine_extractor.extract(m101["raw_text"], m101.get("text_regions", []))
    _require_present("101", "medicine_name", _has_medicine_name_evidence(m101["raw_text"]), m101_result["medicine_name"])
    _require_present("101", "usage_instruction", _has_usage_evidence(m101["raw_text"]), m101_result["usage_instruction"])

    m102 = _load_fixture("102")
    m102_result = medicine_extractor.extract(m102["raw_text"], m102.get("text_regions", []))
    _require_present("102", "usage_instruction", _has_usage_evidence(m102["raw_text"]), m102_result["usage_instruction"])

    validated = validator.validate(
        "MedicineLabel",
        {
            "medicine_name": "Loratadine TAB 10 MG",
            "usage_instruction": "รับประทานครั้งละ 1 เม็ด วันละ 1 ครั้ง หลังอาหาร เช้า",
        },
    )
    _assert_equal(validated["medicine_name"], "Loratadine TAB 10 MG", "validator medicine_name")
    _assert_equal(
        validated["usage_instruction"],
        "รับประทานครั้งละ 1 เม็ด วันละ 1 ครั้ง หลังอาหาร เช้า",
        "validator usage_instruction",
    )

    print("regression tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
