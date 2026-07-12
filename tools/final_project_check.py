from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
CHECK_REPORT_PATH = REPORTS_DIR / "final_project_check.md"

REQUIRED_FILES = [
    PROJECT_ROOT / "main.py",
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "Dockerfile",
    PROJECT_ROOT / "docker-compose.yml",
    PROJECT_ROOT / "requirements.txt",
    PROJECT_ROOT / "requirements-docker.txt",
    PROJECT_ROOT / "models" / "yolo" / "best.pt",
]

REQUIRED_DIRECTORIES = [
    PROJECT_ROOT / "core",
    PROJECT_ROOT / "extractors",
    PROJECT_ROOT / "evaluation" / "appointment" / "images",
    PROJECT_ROOT / "evaluation" / "appointment" / "ground_truth",
    PROJECT_ROOT / "evaluation" / "medicine" / "images",
    PROJECT_ROOT / "evaluation" / "medicine" / "ground_truth",
    PROJECT_ROOT / "runtime" / "debug",
    PROJECT_ROOT / "runtime" / "final_output",
    PROJECT_ROOT / "runtime" / "outputs",
    PROJECT_ROOT / "runtime" / "logs",
]


def _check_paths(paths: list[Path]) -> list[str]:
    return [str(path.relative_to(PROJECT_ROOT)) for path in paths if not path.exists()]


def _has_gitignore_pattern(pattern: str) -> bool:
    gitignore = PROJECT_ROOT / ".gitignore"
    if not gitignore.exists():
        return False
    text = gitignore.read_text(encoding="utf-8")
    return pattern in text


def _run_smoke_test() -> tuple[bool, str]:
    image = PROJECT_ROOT / "evaluation" / "appointment" / "images" / "A01.jpg"
    if not image.exists():
        return False, f"missing smoke test image: {image}"
    try:
        completed = subprocess.run(
            [sys.executable, "main.py", str(image), "--production"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "smoke test failed"
        return False, message
    output_path = PROJECT_ROOT / "runtime" / "outputs" / "result.json"
    if not output_path.exists():
        return False, "runtime/outputs/result.json was not created"
    return True, output_path.as_posix()


def build_report() -> dict[str, Any]:
    for directory in REQUIRED_DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)
    missing_files = _check_paths(REQUIRED_FILES)
    missing_dirs = _check_paths(REQUIRED_DIRECTORIES)
    runtime_ignore_ok = all(
        _has_gitignore_pattern(pattern)
        for pattern in ["runtime/debug/", "runtime/outputs/", "runtime/logs/", "runtime/final_output/"]
    )
    smoke_ok, smoke_detail = _run_smoke_test()

    return {
        "summary": {
            "missing_files": missing_files,
            "missing_directories": missing_dirs,
            "runtime_gitignore_ok": runtime_ignore_ok,
            "smoke_test_ok": smoke_ok,
            "smoke_test_detail": smoke_detail,
        },
        "status": "pass" if not missing_files and not missing_dirs and runtime_ignore_ok and smoke_ok else "fail",
    }


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    CHECK_REPORT_PATH.write_text(
        "# Final Project Check\n\n```json\n"
        + json.dumps(report, ensure_ascii=False, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
