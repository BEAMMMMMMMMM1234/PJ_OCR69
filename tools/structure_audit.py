from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
INVENTORY_PATH = DOCS_DIR / "structure_inventory.json"
REPORT_PATH = DOCS_DIR / "structure_consistency_report.md"

SKIP_NAMES = {".git", ".venv", "__pycache__", ".DS_Store"}
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}

EXPECTED_DIRECTORIES = [
    "core",
    "extractors",
    "evaluation",
    "evaluation/appointment/images",
    "evaluation/appointment/ground_truth",
    "evaluation/medicine/images",
    "evaluation/medicine/ground_truth",
    "models",
    "models/yolo",
    "models/paddle",
    "runtime",
    "runtime/debug",
    "runtime/final_output",
    "runtime/outputs",
    "runtime/logs",
    "reports",
    "tools",
    "docs",
    "archive",
]

EXPECTED_FILES = [
    "models/yolo/best.pt",
    "Dockerfile",
    "docker-compose.yml",
    ".dockerignore",
    "README.md",
    "requirements.txt",
    "requirements-docker.txt",
    "main.py",
]

ANALYZE_PATHS = [
    "main.py",
    "Dockerfile",
    "docker-compose.yml",
    "README.md",
    "Makefile",
    "evaluation/cer.py",
    "evaluation/field_accuracy.py",
    "evaluation/evaluate.py",
    "evaluation/prepare_dataset.py",
    "evaluation/validate_dataset.py",
    "evaluation/run_detection_ocr_report.py",
    "tools/project_audit.py",
    "tools/structure_audit.py",
]

PATH_REFERENCE_PATTERNS = [
    "data/test_images",
    "evaluation/appointment/images",
    "evaluation/appointment/ground_truth",
    "evaluation/medicine/images",
    "evaluation/medicine/ground_truth",
    "archive/legacy/visual_tools",
    "evaluation/*/predictions",
    "evaluation/*/reports",
    "models/yolo/best.pt",
    "models/paddle",
    "archive/legacy",
    "debug/",
    "outputs/",
]


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _is_skipped(path: Path) -> bool:
    return any(part in SKIP_NAMES for part in path.parts)


def _iter_project_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(PROJECT_ROOT.rglob("*")):
        if path.is_dir():
            continue
        if _is_skipped(path):
            continue
        files.append(path)
    return files


def _categorize_file(path: Path) -> str:
    rel = path.relative_to(PROJECT_ROOT).as_posix()
    suffix = path.suffix

    if rel.startswith("archive/"):
        return "archive"
    if rel.startswith("models/"):
        return "model"
    if rel.startswith("evaluation/appointment/images/") or rel.startswith("evaluation/medicine/images/"):
        return "evaluation_image"
    if rel.startswith("evaluation/appointment/ground_truth/") or rel.startswith("evaluation/medicine/ground_truth/"):
        return "ground_truth"
    if rel.startswith("evaluation/appointment/predictions/") or rel.startswith("evaluation/medicine/predictions/"):
        return "generated_output"
    if rel.startswith("evaluation/appointment/reports/") or rel.startswith("evaluation/medicine/reports/"):
        return "generated_output"
    if rel.startswith("archive/legacy/visual_tools/") or rel in {
        "evaluation/summary_report.json",
        "evaluation/evaluation_report.json",
        "evaluation/dataset_validation_report.json",
        "evaluation/report.json",
        "evaluation/batch_report.json",
        "evaluation/detection_ocr_report.json",
        "evaluation/detection_ocr_report.md",
    }:
        return "generated_output"
    if rel.startswith("runtime/final_output/"):
        return "generated_output"
    if rel.startswith("runtime/debug/"):
        return "generated_debug"
    if rel.startswith("runtime/outputs/") or rel.startswith("reports/"):
        return "generated_output"
    if rel.startswith("debug/"):
        return "generated_debug"
    if rel.startswith("outputs/"):
        return "generated_output"
    if rel in {".dockerignore", "Dockerfile", "docker-compose.yml", "requirements.txt", "requirements-docker.txt", "Makefile"}:
        return "docker_config"
    if rel.startswith("docs/") or rel == "README.md":
        return "documentation"
    if rel.startswith("core/") or rel.startswith("extractors/") or rel.startswith("evaluation/") or rel.startswith("tools/") or rel == "main.py":
        if suffix == ".py":
            return "source_code"
        return "documentation" if suffix in {".md", ".json"} and rel.startswith("docs/") else "unknown"
    if rel.startswith("data/test_images/"):
        return "sample_input"
    if suffix in {".json", ".md"} and rel.startswith("evaluation/"):
        return "generated_output"
    return "unknown"


def _list_images(images_dir: Path) -> dict[str, list[str]]:
    by_stem: dict[str, list[str]] = defaultdict(list)
    if not images_dir.exists():
        return by_stem
    for item in images_dir.iterdir():
        if item.is_file() and item.suffix in ALLOWED_IMAGE_SUFFIXES:
            by_stem[item.stem].append(str(item))
    return by_stem


def _check_required_pairs(base_dir: Path, prefix: str) -> dict[str, Any]:
    images_dir = base_dir / "images"
    gt_dir = base_dir / "ground_truth"
    image_stems = _list_images(images_dir)

    missing_images: list[str] = []
    missing_ground_truth: list[str] = []
    for index in range(1, 26):
        stem = f"{prefix}{index:02d}"
        gt_path = gt_dir / f"{stem}.json"
        if not gt_path.exists():
            missing_ground_truth.append(str(gt_path))
        if stem not in image_stems:
            missing_images.append(str(images_dir / f"{stem}.<ext>"))

    return {
        "images_dir": str(images_dir),
        "ground_truth_dir": str(gt_dir),
        "missing_images": missing_images,
        "missing_ground_truth": missing_ground_truth,
    }


def _collect_path_references(path: Path) -> list[str]:
    try:
        text = _load_text(path)
    except Exception:
        return []

    matches: list[str] = []
    for needle in PATH_REFERENCE_PATTERNS:
        if needle in text:
            if needle == "data/test_images" and (
                "legacy" in text.lower()
                or "sample only" in text.lower()
                or "tools/" in path.as_posix()
            ):
                continue
            matches.append(needle)

    # Capture obvious relative file references such as `something/file.ext`.
    regex_matches = set(
        re.findall(r"(?<![A-Za-z0-9_.-])(?:[A-Za-z0-9_.-]+/)+(?:[A-Za-z0-9_.-]+)", text)
    )
    for item in sorted(regex_matches):
        if item.startswith(("http://", "https://")):
            continue
        if item.count("/") < 1:
            continue
        if item == "data/test_images" and (
            "legacy" in text.lower()
            or "sample only" in text.lower()
            or "tools/" in path.as_posix()
        ):
            continue
        matches.append(item)
    return sorted(dict.fromkeys(matches))


def _path_exists(ref: str) -> bool:
    if "*" in ref:
        return any(PROJECT_ROOT.glob(ref))
    return (PROJECT_ROOT / ref).exists()


def _load_dockerignore_patterns() -> list[str]:
    path = PROJECT_ROOT / ".dockerignore"
    if not path.exists():
        return []
    return [line.strip() for line in _load_text(path).splitlines() if line.strip() and not line.startswith("#")]


def _dockerignore_issues(patterns: list[str]) -> list[str]:
    issues: list[str] = []
    protected_paths = [
        "models/",
        "evaluation/*/images/",
        "evaluation/*/ground_truth/",
        "core/",
        "extractors/",
        "main.py",
        "requirements-docker.txt",
    ]
    for protected in protected_paths:
        if protected in patterns:
            issues.append(f"protected path is ignored: {protected}")
    return issues


def build_inventory() -> dict[str, Any]:
    files = _iter_project_files()
    categories: Counter[str] = Counter()
    inventory: list[dict[str, Any]] = []

    for path in files:
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        category = _categorize_file(path)
        categories[category] += 1
        inventory.append(
            {
                "path": rel,
                "category": category,
                "size_bytes": path.stat().st_size,
            }
        )

    required_dirs = []
    missing_required_directories = []
    for rel_dir in EXPECTED_DIRECTORIES:
        abs_dir = PROJECT_ROOT / rel_dir
        required_dirs.append(rel_dir)
        if not abs_dir.exists():
            missing_required_directories.append(rel_dir)

    missing_required_files = []
    for rel_file in EXPECTED_FILES:
        abs_file = PROJECT_ROOT / rel_file
        if not abs_file.exists():
            missing_required_files.append(rel_file)

    evaluation_layout = {
        "appointment": _check_required_pairs(PROJECT_ROOT / "evaluation" / "appointment", "A"),
        "medicine": _check_required_pairs(PROJECT_ROOT / "evaluation" / "medicine", "M"),
    }

    referenced_files: dict[str, list[str]] = {}
    broken_references: list[dict[str, Any]] = []
    outdated_path_references: list[dict[str, Any]] = []
    legacy_sample_refs: list[dict[str, Any]] = []

    for rel in ANALYZE_PATHS:
        path = PROJECT_ROOT / rel
        if not path.exists():
            continue
        refs = _collect_path_references(path)
        referenced_files[rel] = refs
        for ref in refs:
            if ref == "data/test_images":
                legacy_sample_refs.append({"file": rel, "reference": ref})
            if not _path_exists(ref):
                broken_references.append({"file": rel, "reference": ref})
            if ref == "data/test_images":
                outdated_path_references.append(
                    {
                        "file": rel,
                        "reference": ref,
                        "note": "legacy sample path; quick test should prefer evaluation/*/images/",
                    }
                )

    dockerignore_patterns = _load_dockerignore_patterns()
    dockerignore_issues = _dockerignore_issues(dockerignore_patterns)

    docker_issues: list[str] = []
    dockerfile = PROJECT_ROOT / "Dockerfile"
    docker_compose = PROJECT_ROOT / "docker-compose.yml"
    if dockerfile.exists():
        docker_text = _load_text(dockerfile)
        if "COPY . /app" not in docker_text:
            docker_issues.append("Dockerfile missing COPY . /app")
        if "requirements-docker.txt" not in docker_text:
            docker_issues.append("Dockerfile does not use requirements-docker.txt")
        if "requirements.txt" in docker_text and "requirements-docker.txt" not in docker_text:
            docker_issues.append("Dockerfile may still rely on requirements.txt")
    else:
        docker_issues.append("Dockerfile missing")
    if docker_compose.exists():
        compose_text = _load_text(docker_compose)
        if ".:/app" not in compose_text and "source: .\n" not in compose_text:
            docker_issues.append("docker-compose.yml missing volume mount .:/app")
        if "OLLAMA_HOST" not in compose_text:
            docker_issues.append("docker-compose.yml missing OLLAMA_HOST")
    else:
        docker_issues.append("docker-compose.yml missing")
    docker_issues.extend(dockerignore_issues)

    sample_input_files = [item for item in inventory if item["category"] == "sample_input"]
    archive_files = [item for item in inventory if item["category"] == "archive"]
    generated_debug_files = [item for item in inventory if item["category"] == "generated_debug"]
    generated_output_files = [item for item in inventory if item["category"] == "generated_output"]

    report = {
        "project_root": str(PROJECT_ROOT),
        "summary": {
            "total_files": len(files),
            "category_counts": dict(categories),
        },
        "required": {
            "directories": required_dirs,
            "missing_directories": missing_required_directories,
            "missing_files": missing_required_files,
        },
        "evaluation_layout": evaluation_layout,
        "path_references": referenced_files,
        "outdated_path_references": outdated_path_references,
        "broken_references": broken_references,
        "legacy_sample_references": legacy_sample_refs,
        "docker_issues": docker_issues,
        "inventory": inventory,
        "recommendations": {
            "keep": [
                "core/",
                "extractors/",
                "evaluation/*/images/",
                "evaluation/*/ground_truth/",
                "models/yolo/best.pt",
                "models/paddle/",
                "main.py",
                "requirements.txt",
                "requirements-docker.txt",
            ],
            "ignore": [
                "debug/",
                "outputs/",
                "runtime/debug/",
                "runtime/final_output/",
                "runtime/outputs/",
                "runtime/logs/",
                "evaluation/*/predictions/",
                "evaluation/*/reports/",
                "evaluation/summary_report.json",
                "evaluation/evaluation_report.json",
                "evaluation/dataset_validation_report.json",
                "evaluation/report.json",
                "evaluation/batch_report.json",
                "evaluation/detection_ocr_report.json",
                "evaluation/detection_ocr_report.md",
                "archive/legacy/visual_tools/",
            ],
            "archive": [
                "archive/legacy/",
                "legacy sample reference paths in docs and Docker",
                "old accidental files if any appear again, e.g. *.pymv / *.pytouch",
            ],
        },
        "generated_groups": {
            "sample_input_files": sample_input_files,
            "archive_files": archive_files,
            "generated_debug_files": generated_debug_files,
            "generated_output_files": generated_output_files,
        },
    }
    return report


def _markdown_list(items: list[str]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- `{item}`" for item in items)


def _markdown_dict_list(items: list[dict[str, Any]]) -> str:
    if not items:
        return "- none"
    lines = []
    for item in items:
        parts = ", ".join(f"`{k}`: `{v}`" for k, v in item.items())
        lines.append(f"- {parts}")
    return "\n".join(lines)


def build_report_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    required = report["required"]
    layout = report["evaluation_layout"]
    recommendations = report["recommendations"]
    generated = report["generated_groups"]

    lines = [
        "# Structure Consistency Report",
        "",
        "## 1. Current Project Structure",
        f"- Total files scanned: `{summary['total_files']}`",
        f"- Runtime debug files: `{generated['generated_debug_files'].__len__()}`",
        f"- Runtime output files: `{generated['generated_output_files'].__len__()}`",
        "",
        "## 2. Expected Project Structure",
        "```text",
        "PJ_OCR69/",
        "├── core/",
        "├── extractors/",
        "├── evaluation/",
        "│   ├── appointment/",
        "│   │   ├── images/",
        "│   │   ├── ground_truth/",
        "│   │   ├── predictions/",
        "│   │   └── reports/",
        "│   ├── medicine/",
        "│   │   ├── images/",
        "│   │   ├── ground_truth/",
        "│   │   ├── predictions/",
        "│   │   └── reports/",
        "│   ├── prepare_dataset.py",
        "│   ├── validate_dataset.py",
        "│   ├── evaluate.py",
        "│   └── run_detection_ocr_report.py",
        "├── models/",
        "│   ├── yolo/best.pt",
        "│   └── paddle/",
        "├── runtime/",
        "│   ├── debug/",
        "│   ├── outputs/",
        "│   └── logs/",
        "├── reports/",
        "├── tools/",
        "├── docs/",
        "├── archive/",
        "├── Dockerfile",
        "├── docker-compose.yml",
        "├── requirements.txt",
        "├── requirements-docker.txt",
        "├── README.md",
        "└── main.py",
        "```",
        "",
        "## 3. Dataset Location",
        f"- Appointment images missing: {len(layout['appointment']['missing_images'])}",
        f"- Appointment ground truth missing: {len(layout['appointment']['missing_ground_truth'])}",
        f"- Medicine images missing: {len(layout['medicine']['missing_images'])}",
        f"- Medicine ground truth missing: {len(layout['medicine']['missing_ground_truth'])}",
        "",
        "## 4. Docker Path Consistency",
        f"- Docker issues: {len(report['docker_issues'])}",
        _markdown_list(report["docker_issues"]),
        "",
        "## 5. Broken or Outdated Path References",
        f"- Broken references: {len(report['broken_references'])}",
        _markdown_dict_list(report["broken_references"]),
        "",
        "### Outdated References",
        _markdown_dict_list(report["outdated_path_references"]),
        "",
        "## 6. Files/Directories That Should Be Kept",
        _markdown_list(recommendations["keep"]),
        "",
        "## 7. Files/Directories That Should Be Ignored",
        _markdown_list(recommendations["ignore"]),
        "",
        "## 8. Files/Directories That Should Be Archived",
        _markdown_list(recommendations["archive"]),
        "",
        "## 9. Recommended Commands",
        "```bash",
        "python tools/structure_audit.py",
        "docker compose build",
        "docker compose run --rm ocr python main.py evaluation/appointment/images/A01.jpg",
        "docker compose run --rm ocr python evaluation/run_detection_ocr_report.py",
        "python evaluation/validate_dataset.py",
        "python evaluation/evaluate.py",
        "```",
        "",
        "## 10. Safe Cleanup Plan",
        "1. Keep `evaluation/*/images/` and `evaluation/*/ground_truth/` as benchmark data.",
        "2. Keep `data/test_images/` only as legacy/sample input; do not use it as the primary quick-test path.",
        "3. Ignore generated debug/output/report files in Git.",
        "4. Archive legacy or accidental files instead of deleting them.",
        "5. Re-run the audit after any cleanup change.",
        "",
        "## Inventory Notes",
        f"- Sample input files: `{len(generated['sample_input_files'])}`",
        f"- Archive files: `{len(generated['archive_files'])}`",
        f"- Generated debug files: `{len(generated['generated_debug_files'])}`",
        f"- Generated output files: `{len(generated['generated_output_files'])}`",
    ]
    return "\n".join(lines)


def main() -> int:
    report = build_inventory()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    INVENTORY_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(build_report_markdown(report), encoding="utf-8")

    summary = report["summary"]
    required = report["required"]
    print(f"total files: {summary['total_files']}")
    print(f"missing required directories: {required['missing_directories']}")
    print(f"missing required files: {required['missing_files']}")
    print(f"outdated path references: {report['outdated_path_references']}")
    print(f"docker issues: {report['docker_issues']}")
    print("recommended next actions:")
    print("- keep data/test_images as legacy/sample only")
    print("- keep evaluation images and ground truth as benchmark data")
    print("- archive accidental or legacy files instead of deleting them")
    print("- keep generated outputs ignored by Git")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
