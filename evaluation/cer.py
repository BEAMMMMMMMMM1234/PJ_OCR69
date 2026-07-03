from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", str(text).strip())


def levenshtein_distance(a: str, b: str) -> int:
    a_chars = list(a)
    b_chars = list(b)

    if not a_chars:
        return len(b_chars)
    if not b_chars:
        return len(a_chars)

    previous_row = list(range(len(b_chars) + 1))
    for i, a_char in enumerate(a_chars, start=1):
        current_row = [i]
        for j, b_char in enumerate(b_chars, start=1):
            insertion_cost = current_row[j - 1] + 1
            deletion_cost = previous_row[j] + 1
            substitution_cost = previous_row[j - 1] + (a_char != b_char)
            current_row.append(min(insertion_cost, deletion_cost, substitution_cost))
        previous_row = current_row

    return previous_row[-1]


def calculate_cer(reference_text: str, predicted_text: str) -> dict[str, float | int | str]:
    reference_text = _normalize_text(reference_text)
    predicted_text = _normalize_text(predicted_text)

    if reference_text == "":
        cer = 0.0 if predicted_text == "" else 1.0
        return {
            "reference_text": reference_text,
            "predicted_text": predicted_text,
            "reference_length": 0,
            "predicted_length": len(predicted_text),
            "edit_distance": 0 if predicted_text == "" else len(predicted_text),
            "cer": cer,
        }

    distance = levenshtein_distance(reference_text, predicted_text)
    reference_length = len(reference_text)
    cer = distance / reference_length

    return {
        "reference_text": reference_text,
        "predicted_text": predicted_text,
        "reference_length": reference_length,
        "predicted_length": len(predicted_text),
        "edit_distance": distance,
        "cer": cer,
    }
