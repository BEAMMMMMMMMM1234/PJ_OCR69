# File Responsibility

This document summarizes each Python file based on the current codebase and the actual call sites found in the project.

## Core Runtime

| File | Purpose | Called By | Output | Critical | Type | Used in Evaluation |
|---|---|---|---|---|---|---|
| `main.py` | CLI entry point for single image or folder runs; supports production output | User CLI | Full debug JSON or clean production JSON | YES | Production | Yes |
| `core/ocr_pipeline.py` | Orchestrates YOLO, OCR, classification, extraction, validation, Gemma post-processing, and file artifacts | `main.py`, evaluation scripts, dashboard scripts | Full pipeline result, clean final output, debug trace files | YES | Production + Debug | Yes |
| `core/yolo_detector.py` | Detects text regions with YOLO and writes annotated images | `core/ocr_pipeline.py`, evaluation report scripts | Detection boxes + annotated image | YES | Production | Yes |
| `core/paddle_ocr.py` | Reads OCR text from detected ROIs in memory | `core/ocr_pipeline.py`, `evaluation/run_detection_ocr_report.py` | OCR regions, raw text, confidences | YES | Production | Yes |
| `core/document_classifier.py` | Weighted keyword classification for Appointment / MedicineLabel / Unknown | `core/ocr_pipeline.py` | Classification scores and matched keywords | YES | Production | Yes |
| `core/field_extractor.py` | Dispatches to document-specific extractors | `core/ocr_pipeline.py` | Structured field dict | YES | Production | Yes |
| `core/validator.py` | Normalizes and validates extracted fields | `core/ocr_pipeline.py` | Validated field dict | YES | Production | Yes |
| `core/gemma_postprocessor.py` | Optional Gemma/Ollama post-processing with fallback to validated data | `core/ocr_pipeline.py` | Gemma-cleaned data + usage/error flag | NO | Production helper | Yes |
| `core/final_output_formatter.py` | Builds the clean web/API JSON contract | `core/ocr_pipeline.py`, `core/production_output.py` | Clean final output JSON | YES | Production | Yes |
| `core/gemma_formatter.py` | Legacy compatibility formatter; no longer the primary final stage | Legacy / compatibility only | Final schema from validated data | NO | Legacy | No |
| `core/production_output.py` | Builds web/API-safe production JSON and runtime directories | `main.py`, `evaluation/export_web_results.py`, `core/ocr_pipeline.py` | Clean output JSON | YES | Production | Yes |
| `core/json_builder.py` | Legacy empty helper; no active logic | No current import found | None | NO | Legacy | No |

## Extractors

| File | Purpose | Called By | Output | Critical | Type | Used in Evaluation |
|---|---|---|---|---|---|---|
| `extractors/appointment_extractor.py` | Rule-based extraction for appointment documents | `core/field_extractor.py` | Appointment fields | YES | Production | Yes |
| `extractors/medicine_extractor.py` | Rule-based extraction for medicine labels | `core/field_extractor.py` | Medicine fields | YES | Production | Yes |
| `extractors/__init__.py` | Package marker | Python import system | None | NO | Package | No |

## Evaluation

| File | Purpose | Called By | Output | Critical | Type | Used in Evaluation |
|---|---|---|---|---|---|---|
| `evaluation/evaluate.py` | Full benchmark evaluation using ground truth | CLI | Evaluation report JSON and summary | YES | Evaluation | Yes |
| `evaluation/prepare_dataset.py` | Copies/creates benchmark dataset structure | CLI | Dataset folders and GT templates | YES | Evaluation setup | Yes |
| `evaluation/validate_dataset.py` | Validates benchmark dataset completeness and schema | CLI, `evaluation/evaluate.py` | Dataset validation report JSON | YES | Evaluation | Yes |
| `evaluation/run_detection_ocr_report.py` | Runs YOLO + OCR only | CLI | Detection/OCR report JSON and MD in `reports/`; visual artifacts in archive | NO | Evaluation utility | Yes |
| `evaluation/run_pipeline_diagnosis.py` | Diagnoses failures by stage across evaluation images | CLI | Diagnosis report JSON and MD in `reports/` | NO | Evaluation utility | Yes |
| `evaluation/run_visual_dashboard.py` | Builds HTML dashboard for human review | CLI | Dashboard HTML, JSON, annotated images in archive | NO | Evaluation utility | Yes |
| `evaluation/export_web_results.py` | Converts clean final output to web-ready JSON | CLI | `runtime/outputs/web_ready_results.json` | NO | Export utility | Yes |
| `evaluation/cer.py` | CER calculation via Levenshtein distance | `evaluation/evaluate.py` | CER value | NO | Evaluation utility | Yes |
| `evaluation/field_accuracy.py` | Field-level accuracy calculation | `evaluation/evaluate.py` | Field accuracy metrics | NO | Evaluation utility | Yes |
| `evaluation/__init__.py` | Package marker | Python import system | None | NO | Package | No |

## Tools

| File | Purpose | Called By | Output | Critical | Type | Used in Evaluation |
|---|---|---|---|---|---|---|
| `tools/project_audit.py` | Repository inventory and cleanup audit | CLI | Inventory report JSON/MD | NO | Tooling | No |
| `tools/structure_audit.py` | Path consistency and structure audit | CLI | Structure report JSON/MD | NO | Tooling | No |
| `tools/final_project_check.py` | Final smoke checks and project readiness | CLI | Readiness report | NO | Tooling | No |
| `tools/validate_input_images.py` | Input image quality validation before evaluation import | CLI | Input validation report JSON/MD | NO | Tooling | Yes |
| `tools/dataset_readiness.py` | Quick dataset availability checker | CLI | Dataset readiness report | NO | Tooling | Yes |

## Runtime Artifact Ownership

- `runtime/debug/annotated/` is written by `core/yolo_detector.py`.
- `runtime/debug/classification/` is written by `core/document_classifier.py`.
- `runtime/debug/ocr_evidence/` is written by `core/ocr_pipeline.py`.
- `runtime/final_output/` is written by `core/ocr_pipeline.py` and contains clean final output for the web/API handoff.
- `runtime/debug/pipeline_trace/` is written by `core/ocr_pipeline.py` and contains the full developer trace.
- `runtime/debug/final_output/` is legacy and archived; it should not be used by the runtime anymore.
- `runtime/outputs/` is written by `main.py` and `evaluation/export_web_results.py`.
- `reports/` is written by evaluation and diagnostic scripts.
