from __future__ import annotations

import ast
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
INVENTORY_PATH = DOCS_DIR / "project_file_inventory.json"
REPORT_PATH = DOCS_DIR / "project_cleanup_report.md"

SKIP_DIR_NAMES = {".git", ".venv", "__pycache__", ".pycache"}
SKIP_FILE_NAMES = {".DS_Store"}
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}
ALLOWED_PY_SUFFIX = ".py"
ENTRY_POINT_RELATIVE_PATHS = [
    "tools/project_audit.py",
    "main.py",
    "evaluation/evaluate.py",
    "evaluation/prepare_dataset.py",
    "evaluation/validate_dataset.py",
]


def _is_skipped(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIR_NAMES:
        return True
    return path.name in SKIP_FILE_NAMES


def _scan_files() -> list[Path]:
    files: list[Path] = []
    for path in PROJECT_ROOT.rglob("*"):
        if path.is_dir():
            continue
        if _is_skipped(path):
            continue
        files.append(path)
    return sorted(files)


def _relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _module_name_from_path(path: Path) -> str | None:
    if path.suffix != ALLOWED_PY_SUFFIX:
        return None
    rel = path.relative_to(PROJECT_ROOT)
    if rel.name == "__init__.py":
        return ".".join(rel.parent.parts) if rel.parent.parts else ""
    return ".".join(rel.with_suffix("").parts)


def _module_candidates_from_import(node: ast.AST, current_module: str) -> set[str]:
    candidates: set[str] = set()
    if isinstance(node, ast.Import):
        for alias in node.names:
            candidates.add(alias.name)
    elif isinstance(node, ast.ImportFrom):
        if node.level and current_module:
            package_parts = current_module.split(".")[:-node.level]
            if node.module:
                base = ".".join(package_parts + node.module.split("."))
            else:
                base = ".".join(package_parts)
        else:
            base = node.module or ""
        if base:
            candidates.add(base)
        for alias in node.names:
            if alias.name == "*":
                continue
            if base:
                candidates.add(f"{base}.{alias.name}")
    return candidates


def _parse_imports(path: Path, current_module: str) -> set[str]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except Exception:
        return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.update(_module_candidates_from_import(node, current_module))
    return imports


def _build_module_index(files: list[Path]) -> tuple[dict[str, Path], dict[Path, str]]:
    module_to_path: dict[str, Path] = {}
    path_to_module: dict[Path, str] = {}
    for path in files:
        module_name = _module_name_from_path(path)
        if module_name is None:
            continue
        path_to_module[path] = module_name
        module_to_path[module_name] = path
    return module_to_path, path_to_module


def _resolve_local_modules(
    imports: set[str],
    module_to_path: dict[str, Path],
) -> set[str]:
    resolved: set[str] = set()
    for name in imports:
        if name in module_to_path:
            resolved.add(name)
            continue
        parts = name.split(".")
        for end in range(len(parts) - 1, 0, -1):
            candidate = ".".join(parts[:end])
            if candidate in module_to_path:
                resolved.add(candidate)
                break
    return resolved


def _classify_file(path: Path) -> str:
    rel = _relative(path)
    suffix = path.suffix.lower()

    if rel.startswith("archive/legacy/"):
        return "archive"
    if path.name == ".gitkeep":
        return "config"
    if rel == "requirements.txt" or rel == ".gitignore" or rel == "pyvenv.cfg":
        return "config"
    if suffix == ".md":
        return "documentation"
    if suffix == ".pt":
        return "model_file"
    if rel.startswith("evaluation/appointment/images/") or rel.startswith("evaluation/medicine/images/"):
        return "evaluation_dataset"
    if rel.startswith("data/test_images/"):
        return "sample_input"
    if rel.startswith("evaluation/") and "/ground_truth/" in rel and suffix == ".json":
        return "ground_truth"
    if rel.startswith("evaluation/") and ("/predictions/" in rel or "/reports/" in rel):
        return "prediction_output"
    if rel.startswith("runtime/debug/"):
        return "debug_output"
    if rel.startswith("runtime/final_output/"):
        return "prediction_output"
    if rel.startswith("runtime/outputs/"):
        return "prediction_output"
    if rel.startswith("reports/"):
        return "documentation"
    if rel in {
        "evaluation/summary_report.json",
        "evaluation/dataset_validation_report.json",
        "evaluation/evaluation_report.json",
        "evaluation/report.json",
        "outputs/result.json",
    }:
        return "debug_output"
    if rel.startswith("debug/"):
        return "debug_output"
    if suffix == ".py":
        return "source_code"
    if suffix in {".pymv", ".pytouch"}:
        return "cache"
    if suffix == ".json":
        return "debug_output" if rel.startswith("evaluation/") else "unknown"
    return "unknown"


def _is_generated_file(path: Path) -> bool:
    rel = _relative(path)
    if path.name == ".gitkeep":
        return False
    return (
        rel.startswith("runtime/debug/")
        or rel.startswith("runtime/final_output/")
        or rel.startswith("runtime/outputs/")
        or rel.startswith("reports/")
        or rel.startswith("debug/")
        or rel.startswith("outputs/")
        or rel.startswith("evaluation/appointment/predictions/")
        or rel.startswith("evaluation/appointment/reports/")
        or rel.startswith("evaluation/medicine/predictions/")
        or rel.startswith("evaluation/medicine/reports/")
        or rel in {
            "evaluation/summary_report.json",
            "evaluation/dataset_validation_report.json",
            "evaluation/evaluation_report.json",
            "evaluation/report.json",
        }
    )


def _is_archive_file(path: Path) -> bool:
    return _relative(path).startswith("archive/legacy/")


def _is_gitignore_candidate(path: Path, category: str) -> bool:
    rel = _relative(path)
    if path.name == ".gitkeep":
        return False
    if category in {"debug_output", "cache", "prediction_output"}:
        return True
    if rel.startswith("evaluation/") and "/predictions/" in rel:
        return True
    if rel.startswith("evaluation/") and "/reports/" in rel:
        return True
    if rel.startswith("runtime/debug/") or rel.startswith("runtime/final_output/") or rel.startswith("runtime/outputs/"):
        return True
    if rel in {
        "evaluation/summary_report.json",
        "evaluation/dataset_validation_report.json",
        "evaluation/evaluation_report.json",
        "evaluation/report.json",
        "outputs/result.json",
        "runtime/final_output/",
    }:
        return True
    if rel in {"evaluation/field_accuracy.pymv", "extractors/medicine_extractor.pytouch"}:
        return True
    if rel.startswith("data/test_images/"):
        return False
    return False


def _recommendation_for_file(path: Path, category: str, status: str) -> str:
    if category == "archive":
        return "Do not delete"
    if category == "source_code" and status == "unused":
        return "Needs manual review"
    if category in {"debug_output", "prediction_output", "cache"}:
        return "Safe to ignore in Git"
    if category in {"evaluation_dataset", "ground_truth", "model_file", "documentation", "config"}:
        return "Do not delete"
    if status == "active":
        return "Do not delete"
    return "Needs manual review"


def _collect_inventory() -> dict[str, Any]:
    files = _scan_files()
    module_to_path, path_to_module = _build_module_index(files)

    entry_points = [PROJECT_ROOT / rel for rel in ENTRY_POINT_RELATIVE_PATHS if (PROJECT_ROOT / rel).exists()]
    entry_point_modules = {
        _module_name_from_path(path)
        for path in entry_points
        if _module_name_from_path(path)
    }

    imports_by_path: dict[Path, set[str]] = {}
    reverse_imports: dict[str, set[str]] = defaultdict(set)
    for path, module_name in path_to_module.items():
        imports = _parse_imports(path, module_name)
        local_imports = _resolve_local_modules(imports, module_to_path)
        imports_by_path[path] = local_imports
        for imported in local_imports:
            reverse_imports[imported].add(module_name)

    reachable_modules: set[str] = set(entry_point_modules)
    changed = True
    while changed:
        changed = False
        for module_name in list(reachable_modules):
            path = module_to_path.get(module_name)
            if not path:
                continue
            for imported in imports_by_path.get(path, set()):
                if imported not in reachable_modules:
                    reachable_modules.add(imported)
                    changed = True

    file_records: list[dict[str, Any]] = []
    category_counts: Counter[str] = Counter()
    active_source_files: list[str] = []
    possible_unused_files: list[str] = []
    generated_files: list[str] = []
    archive_files: list[str] = []
    files_to_ignore: list[str] = []

    for path in files:
        category = _classify_file(path)
        rel = _relative(path)
        size_bytes = path.stat().st_size
        is_entry_point = rel in ENTRY_POINT_RELATIVE_PATHS
        module_name = path_to_module.get(path)
        status = "active" if is_entry_point or (module_name in reachable_modules if module_name else False) else "inactive"
        if path.name == "__init__.py":
            status = "active"
        if category == "source_code" and status != "active":
            possible_unused_files.append(rel)
        if _is_generated_file(path):
            generated_files.append(rel)
        if _is_archive_file(path):
            archive_files.append(rel)
        if _is_gitignore_candidate(path, category):
            files_to_ignore.append(rel)

        file_record = {
            "path": rel,
            "category": category,
            "size_bytes": size_bytes,
            "empty": size_bytes == 0,
            "is_entry_point": is_entry_point,
            "status": status,
            "imports": sorted(imports_by_path.get(path, set())),
            "imported_by": sorted(reverse_imports.get(module_name, set())) if module_name else [],
            "generated": _is_generated_file(path),
            "recommended_action": _recommendation_for_file(path, category, status),
        }
        file_records.append(file_record)
        category_counts[category] += 1
        if category == "source_code" and status == "active":
            active_source_files.append(rel)

    files_to_ignore = sorted(set(files_to_ignore))
    generated_files = sorted(set(generated_files))
    archive_files = sorted(set(archive_files))
    possible_unused_files = sorted(set(possible_unused_files))

    inventory = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(PROJECT_ROOT),
        "entry_points": [rel for rel in ENTRY_POINT_RELATIVE_PATHS if (PROJECT_ROOT / rel).exists()],
        "summary": {
            "total_files": len(files),
            "counts_by_category": dict(sorted(category_counts.items())),
            "active_source_files": len(active_source_files),
            "possible_unused_files": len(possible_unused_files),
            "generated_files": len(generated_files),
            "files_to_ignore": len(files_to_ignore),
        },
        "files": sorted(file_records, key=lambda item: item["path"]),
        "active_source_files": sorted(active_source_files),
        "possible_unused_files": possible_unused_files,
        "generated_files": generated_files,
        "archive_files": archive_files,
        "files_to_ignore": files_to_ignore,
    }
    return inventory


def _format_list(items: list[str], limit: int | None = None) -> str:
    if not items:
        return "- none"
    subset = items if limit is None else items[:limit]
    return "\n".join(f"- `{item}`" for item in subset)


def _build_report(inventory: dict[str, Any]) -> str:
    summary = inventory["summary"]
    counts = summary["counts_by_category"]
    active = inventory["active_source_files"]
    possible_unused = inventory["possible_unused_files"]
    generated = inventory["generated_files"]
    archive_files = inventory["archive_files"]
    files_to_ignore = inventory["files_to_ignore"]

    must_not_delete = [
        "main.py",
        "core/*.py",
        "extractors/*.py",
        "models/yolo/best.pt",
        "evaluation/appointment/images/*",
        "evaluation/appointment/ground_truth/*.json",
        "evaluation/medicine/images/*",
        "evaluation/medicine/ground_truth/*.json",
        "evaluation/prepare_dataset.py",
        "evaluation/validate_dataset.py",
        "evaluation/evaluate.py",
        "requirements.txt",
        "README.md",
    ]

    safe_ignore = [
        p
        for p in generated
        if p.startswith("debug/")
        or p.startswith("outputs/")
        or p.startswith("runtime/debug/")
        or p.startswith("runtime/final_output/")
        or p.startswith("runtime/outputs/")
        or p.startswith("reports/")
    ]
    safe_archive = archive_files + [
        "evaluation/report.json",
        "evaluation/evaluation_report.json",
        "evaluation/summary_report.json",
        "evaluation/dataset_validation_report.json",
        "evaluation/field_accuracy.pymv",
        "extractors/medicine_extractor.pytouch",
        "docs/project_cleanup_report.md",
        "docs/project_file_inventory.json",
    ]
    needs_manual_review = list(dict.fromkeys(possible_unused))

    report = f"""# Project Cleanup Audit

## 1. Project Overview

- Project root: `{inventory["project_root"]}`
- Total files scanned: `{summary["total_files"]}`
- Active source files: `{summary["active_source_files"]}`
- Possible unused files: `{summary["possible_unused_files"]}`

## 2. Entry Points

{_format_list(inventory["entry_points"])}

## 3. Active Source Files

{_format_list(active)}

## 4. Evaluation Dataset Files

- `data/test_images/` (legacy/sample only)
- `evaluation/appointment/images/`
- `evaluation/appointment/ground_truth/`
- `evaluation/medicine/images/`
- `evaluation/medicine/ground_truth/`

## 5. Generated Files

{_format_list(generated)}

## 6. Archive Files

{_format_list(archive_files)}

## 7. Debug/Cache Files

- `debug/`
- `outputs/`
- `runtime/debug/`
- `runtime/final_output/`
- `runtime/outputs/`
- `reports/`
- `archive/legacy/`
- `evaluation/summary_report.json`
- `evaluation/dataset_validation_report.json`
- `evaluation/evaluation_report.json`
- `evaluation/report.json`
- `evaluation/field_accuracy.pymv`
- `extractors/medicine_extractor.pytouch`

## 8. Possible Unused Files

{_format_list(needs_manual_review)}

## 9. Safe Cleanup Recommendations

### Safe to ignore in Git

{_format_list(safe_ignore)}

### Safe to archive

{_format_list(safe_archive)}

### Needs manual review

{_format_list(needs_manual_review)}

### Do not delete

{_format_list(must_not_delete)}

## 10. Files That Must NOT Be Deleted

{_format_list(must_not_delete)}

## 11. Suggested .gitignore Updates

{_format_list(files_to_ignore)}

## 12. Next Actions

1. Review the manual-review files before changing anything.
2. Keep all active source files, models, and evaluation ground truth.
3. Add the generated report and inventory to version control if you want the audit to be reproducible.
4. Add the suggested `.gitignore` entries if you want to keep generated evaluation outputs out of Git.

## Category Summary

{chr(10).join(f"- `{key}`: `{value}`" for key, value in counts.items())}
"""
    return report


def main() -> int:
    inventory = _collect_inventory()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    INVENTORY_PATH.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(_build_report(inventory), encoding="utf-8")

    summary = inventory["summary"]
    print(f"Total files scanned: {summary['total_files']}")
    print("Files by category:")
    for category, count in summary["counts_by_category"].items():
        print(f"- {category}: {count}")
    print("Paths to inspect:")
    for path in inventory["possible_unused_files"][:50]:
        print(f"- {path}")
    if len(inventory["possible_unused_files"]) > 50:
        print(f"- ... and {len(inventory['possible_unused_files']) - 50} more")
    print("Paths to add to .gitignore:")
    for path in inventory["files_to_ignore"]:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
