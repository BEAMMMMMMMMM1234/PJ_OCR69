from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORT_PATH = REPORTS_DIR / "consolidation_check.md"

RUNTIME_DIR = PROJECT_ROOT / "runtime"
ARCHIVE_DIR = PROJECT_ROOT / "archive"
DOCS_DIR = PROJECT_ROOT / "docs"
EVALUATION_DIR = PROJECT_ROOT / "evaluation"

EXPECTED_RUNTIME_DIRS = {"debug", "final_output", "outputs", "logs"}
EXPECTED_RUNTIME_OUTPUTS = {"result.json"}
ARCHIVE_EXPECTED_DIRS = [
    "archive/legacy/docs_audit",
    "archive/legacy/duplicate_reports",
    "archive/legacy/evaluation_generated",
    "archive/legacy/runtime_outputs",
    "archive/legacy/visual_tools",
]
DOCS_AUDIT_FILES = {
    "project_cleanup_report.md",
    "project_file_inventory.json",
    "structure_consistency_report.md",
    "structure_inventory.json",
    "refactor_notes.md",
    "dead_code_report.md",
    "project_architecture_review.md",
    "executive_summary.md",
    "_audit_summary.json",
}


def _list_dirnames(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted(item.name for item in path.iterdir() if item.is_dir())


def _list_files(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted(item.name for item in path.iterdir() if item.is_file())


def _check_evaluation_generated_dirs() -> dict[str, list[str]]:
    issues: dict[str, list[str]] = {}
    for doc in ["appointment", "medicine"]:
        doc_dir = EVALUATION_DIR / doc
        for child in ["predictions", "reports"]:
            target = doc_dir / child
            if not target.exists():
                continue
            files = [item.name for item in target.iterdir() if item.is_file() and item.name != ".gitkeep"]
            if files:
                issues[f"{doc}/{child}"] = files
    return issues


def build_report() -> dict[str, Any]:
    runtime_dirs = sorted(_list_dirnames(RUNTIME_DIR))
    runtime_files = _list_files(RUNTIME_DIR)
    runtime_outputs = _list_files(RUNTIME_DIR / "outputs")
    reports_files = _list_files(REPORTS_DIR)
    docs_files = _list_files(DOCS_DIR)

    runtime_ok = set(runtime_dirs) == EXPECTED_RUNTIME_DIRS
    runtime_no_reports = "reports" not in runtime_dirs and "report_summary.json" not in runtime_files
    runtime_outputs_ok = set(runtime_outputs) == EXPECTED_RUNTIME_OUTPUTS
    evaluation_issues = _check_evaluation_generated_dirs()
    docs_audit_remaining = sorted(DOCS_AUDIT_FILES.intersection(docs_files))
    archive_presence = [path for path in ARCHIVE_EXPECTED_DIRS if (PROJECT_ROOT / path).exists()]

    status = (
        runtime_ok
        and runtime_no_reports
        and runtime_outputs_ok
        and not evaluation_issues
        and not docs_audit_remaining
        and bool(archive_presence)
    )

    return {
        "status": "pass" if status else "fail",
        "runtime": {
            "top_level_dirs": runtime_dirs,
            "top_level_files": runtime_files,
            "outputs_files": runtime_outputs,
            "ok": runtime_ok,
            "no_runtime_reports": runtime_no_reports,
            "outputs_ok": runtime_outputs_ok,
        },
        "reports": {
            "files": reports_files,
        },
        "evaluation": {
            "generated_dir_issues": evaluation_issues,
        },
        "docs": {
            "audit_files_remaining": docs_audit_remaining,
        },
        "archive": {
            "expected_paths_present": archive_presence,
        },
    }


def _build_markdown(report: dict[str, Any]) -> str:
    runtime = report["runtime"]
    evaluation = report["evaluation"]
    docs = report["docs"]
    archive = report["archive"]
    lines = [
        "# Consolidation Check",
        "",
        "## Status",
        f"- Result: `{report['status']}`",
        "",
        "## Runtime",
        f"- Top-level dirs: `{', '.join(runtime['top_level_dirs'])}`",
        f"- Top-level files: `{', '.join(runtime['top_level_files'])}`",
        f"- Outputs: `{', '.join(runtime['outputs_files'])}`",
        f"- runtime ok: `{runtime['ok']}`",
        f"- no runtime reports: `{runtime['no_runtime_reports']}`",
        f"- outputs ok: `{runtime['outputs_ok']}`",
        "",
        "## Reports",
        f"- Files: `{', '.join(report['reports']['files'])}`",
        "",
        "## Evaluation",
    ]
    if evaluation["generated_dir_issues"]:
        for key, values in evaluation["generated_dir_issues"].items():
            lines.append(f"- `{key}`: {', '.join(values)}")
    else:
        lines.append("- No generated files remain under evaluation predictions/reports.")
    lines.extend(
        [
            "",
            "## Docs",
        ]
    )
    if docs["audit_files_remaining"]:
        lines.extend(f"- `{item}`" for item in docs["audit_files_remaining"])
    else:
        lines.append("- No audit temporary docs remain in `docs/`.")
    lines.extend(
        [
            "",
            "## Archive",
        ]
    )
    lines.extend(f"- `{item}`" for item in archive["expected_paths_present"])
    lines.extend(
        [
            "",
            "## Next Actions",
            "1. Keep `runtime/final_output/*.json` for per-image handoff and `runtime/outputs/result.json` for the latest run.",
            "2. Use `reports/` for project-level reports.",
            "3. Keep legacy artifacts in `archive/legacy/` for rollback only.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    REPORT_PATH.write_text(_build_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
