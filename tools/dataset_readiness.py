from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def build_readiness_report() -> dict[str, object]:
    appointment_images = PROJECT_ROOT / "evaluation" / "appointment" / "images"
    appointment_ground_truth = PROJECT_ROOT / "evaluation" / "appointment" / "ground_truth"
    medicine_images = PROJECT_ROOT / "evaluation" / "medicine" / "images"
    medicine_ground_truth = PROJECT_ROOT / "evaluation" / "medicine" / "ground_truth"

    return {
        "appointment_images_exists": appointment_images.exists(),
        "appointment_ground_truth_exists": appointment_ground_truth.exists(),
        "medicine_images_exists": medicine_images.exists(),
        "medicine_ground_truth_exists": medicine_ground_truth.exists(),
        "ready": all(
            [
                appointment_images.exists(),
                appointment_ground_truth.exists(),
                medicine_images.exists(),
                medicine_ground_truth.exists(),
            ]
        ),
    }


def main() -> int:
    report = build_readiness_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
