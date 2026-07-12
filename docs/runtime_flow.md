# Runtime Flow

This document explains where runtime artifacts come from and how the project separates developer debug output from production output.

## Production Flow

```text
main.py
  └── OCRPipeline
        ├── YoloDetector
        ├── PaddleOCRReader
        ├── DocumentClassifier
        ├── FieldExtractor
        │     ├── AppointmentExtractor
        │     └── MedicineExtractor
        ├── DataValidator
        ├── GemmaPostProcessor
        ├── FinalOutputFormatter
        └── build_production_output
              ├── runtime/final_output/{stem}.json
              ├── runtime/debug/pipeline_trace/{stem}_trace.json
              └── runtime/outputs/result.json (via main.py --production)
```

## Artifact Ownership

### `runtime/debug/annotated/`

- Created by `core/yolo_detector.py`
- Stores annotated images with bounding boxes

### `runtime/debug/classification/`

- Created by `core/document_classifier.py`
- Stores per-image classification evidence

### `runtime/debug/ocr_evidence/`

- Created by `core/ocr_pipeline.py`
- Stores OCR raw text, regions, and OCR-level notes

### `runtime/final_output/`

- Created by `core/ocr_pipeline.py`
- Stores clean final output for the web/API handoff
- Current schema:
  - `status`
  - `document_type`
  - `data`
  - `error`

### `runtime/debug/pipeline_trace/`

- Created by `core/ocr_pipeline.py`
- Stores the full pipeline trace for developers
- Includes:
  - `structured_data`
  - `validated_data`
  - `final_data`
  - `ocr_evidence`
  - `classification`
  - trace metadata

### `runtime/outputs/`

- Created by `main.py`
- Created by `evaluation/export_web_results.py`
- Stores production-safe JSON for web/API/mobile consumers

### `reports/`

- Created by evaluation and diagnostic scripts
- Stores project-level reports and markdown summaries

### `runtime/logs/`

- Created by `main.py`
- Stores the runtime log file

## Why This Split Matters

- Developers need full traceability during OCR debugging.
- Web/API/mobile consumers need a compact schema with no debug internals.
- The project now keeps both contracts:
  - `runtime/debug/pipeline_trace/` for developer diagnosis
  - `runtime/final_output/` for clean per-image handoff
  - `runtime/outputs/` for production integration
  - `reports/` for project-level reports
