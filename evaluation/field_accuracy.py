from __future__ import annotations

import re
from typing import Any

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_value(value: Any) -> str:
    if value is None:
        return "ไม่พบ"
    return _WHITESPACE_RE.sub(" ", str(value).strip())


def calculate_field_accuracy(
    ground_truth_final_data: dict[str, Any],
    prediction_final_data: dict[str, Any],
) -> dict[str, Any]:
    ground_truth_final_data = ground_truth_final_data or {}
    prediction_final_data = prediction_final_data or {}

    field_names = list(ground_truth_final_data.keys())
    details: dict[str, dict[str, Any]] = {}
    correct_count = 0

    for field_name in field_names:
        expected = _normalize_value(ground_truth_final_data.get(field_name, "ไม่พบ"))
        predicted = _normalize_value(prediction_final_data.get(field_name, "ไม่พบ"))
        is_correct = expected == predicted
        if is_correct:
            correct_count += 1

        details[field_name] = {
            "expected": expected,
            "predicted": predicted,
            "correct": is_correct,
        }

    total_fields = len(field_names)
    field_accuracy = 0.0 if total_fields == 0 else correct_count / total_fields

    return {
        "total_fields": total_fields,
        "correct_fields": correct_count,
        "field_accuracy": field_accuracy,
        "details": details,
    }
