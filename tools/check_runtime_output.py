from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_FINAL_OUTPUT_DIR = PROJECT_ROOT / "runtime" / "final_output"
RUNTIME_DEBUG_FINAL_OUTPUT_DIR = PROJECT_ROOT / "runtime" / "debug" / "final_output"
RUNTIME_OUTPUTS_RESULT_PATH = PROJECT_ROOT / "runtime" / "outputs" / "result.json"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
DEAD_CORE_FILES = [
    PROJECT_ROOT / "core" / "gemma_formatter.py",
    PROJECT_ROOT / "core" / "json_builder.py",
]

APPROVED_TOP_LEVEL_KEYS = {"status", "document_type", "data", "error"}
APPOINTMENT_FIELDS = ("appointment_date", "appointment_time", "preparation_instruction")
MEDICINE_FIELDS = ("medicine_name", "usage_instruction")
LEGACY_SUFFIXES = ("_extracted.json", "_validated.json", "_final.json")


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _validate_payload(path: Path, payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    top_level_keys = set(payload.keys())
    if top_level_keys != APPROVED_TOP_LEVEL_KEYS:
        extra = sorted(top_level_keys - APPROVED_TOP_LEVEL_KEYS)
        missing = sorted(APPROVED_TOP_LEVEL_KEYS - top_level_keys)
        if extra:
            issues.append(f"unexpected top-level keys: {', '.join(extra)}")
        if missing:
            issues.append(f"missing top-level keys: {', '.join(missing)}")

    status = payload.get("status")
    document_type = payload.get("document_type")
    data = payload.get("data")
    error = payload.get("error")

    if status not in {"success", "failed"}:
        issues.append(f"invalid status: {status!r}")

    expected_fields: tuple[str, ...] = ()
    if document_type == "Appointment":
        expected_fields = APPOINTMENT_FIELDS
    elif document_type == "MedicineLabel":
        expected_fields = MEDICINE_FIELDS
    elif document_type != "Unknown":
        issues.append(f"invalid document_type: {document_type!r}")

    if status == "failed":
        if document_type != "Unknown":
            issues.append("failed output must have document_type = 'Unknown'")
        if data not in ({}, None):
            issues.append("failed output must have empty data")
        return issues

    if document_type == "Unknown":
        if data not in ({}, None):
            issues.append("Unknown document_type must have empty data")
        return issues

    if not isinstance(data, dict):
        issues.append("data must be a dict")
        return issues

    data_keys = set(data.keys())
    expected_keys = set(expected_fields)
    if data_keys != expected_keys:
        extra = sorted(data_keys - expected_keys)
        missing = sorted(expected_keys - data_keys)
        if extra:
            issues.append(f"unexpected data keys: {', '.join(extra)}")
        if missing:
            issues.append(f"missing data keys: {', '.join(missing)}")

    for field in expected_fields:
        value = data.get(field, "ไม่พบ")
        if value in (None, ""):
            issues.append(f"{field} is empty")

    if error not in (None, "") and not isinstance(error, str):
        issues.append("error must be string or null")

    return issues


def check_runtime_output() -> dict[str, Any]:
    report: dict[str, Any] = {
        "summary": {
            "total_files": 0,
            "valid_files": 0,
            "invalid_files": 0,
        },
        "files": [],
        "issues": [],
    }

    if RUNTIME_DEBUG_FINAL_OUTPUT_DIR.exists():
        report["issues"].append("runtime/debug/final_output should not exist")

    for path in DEAD_CORE_FILES:
        if path.exists():
            report["issues"].append(f"dead core file still present: {path.relative_to(PROJECT_ROOT)}")

    for path in (
        PROMPTS_DIR / "medicine_prompt.txt",
        PROMPTS_DIR / "appointment_prompt.txt",
    ):
        if not path.exists():
            report["issues"].append(f"missing prompt file: {path.relative_to(PROJECT_ROOT)}")

    if not RUNTIME_FINAL_OUTPUT_DIR.exists():
        report["summary"]["note"] = "runtime/final_output does not exist"
        return report

    json_files = sorted(path for path in RUNTIME_FINAL_OUTPUT_DIR.glob("*.json") if path.is_file())
    report["summary"]["total_files"] = len(json_files)

    for path in json_files:
        payload, load_error = _load_json(path)
        issues: list[str] = []

        if any(path.name.endswith(suffix) for suffix in LEGACY_SUFFIXES):
            issues.append("legacy final-output filename should not remain here")

        if load_error:
            issues.append(f"json load error: {load_error}")
        elif payload is not None:
            issues.extend(_validate_payload(path, payload))

        status = "valid" if not issues else "invalid"
        if status == "valid":
            report["summary"]["valid_files"] += 1
        else:
            report["summary"]["invalid_files"] += 1

        report["files"].append(
            {
                "path": str(path.relative_to(PROJECT_ROOT)),
                "status": status,
                "issues": issues,
            }
        )

    if RUNTIME_OUTPUTS_RESULT_PATH.exists():
        payload, load_error = _load_json(RUNTIME_OUTPUTS_RESULT_PATH)
        issues = []
        if load_error:
            issues.append(f"json load error: {load_error}")
        elif payload is not None:
            issues.extend(_validate_payload(RUNTIME_OUTPUTS_RESULT_PATH, payload))
        report["files"].append(
            {
                "path": str(RUNTIME_OUTPUTS_RESULT_PATH.relative_to(PROJECT_ROOT)),
                "status": "valid" if not issues else "invalid",
                "issues": issues,
            }
        )
        if issues:
            report["summary"]["invalid_files"] += 1
        else:
            report["summary"]["valid_files"] += 1
        report["summary"]["total_files"] += 1

    return report


def main() -> int:
    report = check_runtime_output()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["summary"]["invalid_files"] == 0 and not report["issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
