# Pipeline Call Graph

## Entry Points

The active runtime entry points are:

- `main.py`
- `evaluation/evaluate.py`
- `evaluation/prepare_dataset.py`
- `evaluation/validate_dataset.py`
- `evaluation/run_detection_ocr_report.py`
- `evaluation/run_pipeline_diagnosis.py`
- `evaluation/run_visual_dashboard.py`
- `evaluation/export_web_results.py`
- `tools/project_audit.py`
- `tools/structure_audit.py`
- `tools/final_project_check.py`
- `tools/validate_input_images.py`
- `tools/dataset_readiness.py`

## Main Runtime Flow

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
        ├── runtime/final_output/{stem}.json
        ├── runtime/debug/pipeline_trace/{stem}_trace.json
        └── build_production_output()
              └── runtime/outputs/result.json (via main.py --production)
```

## Detailed Flow

1. `main.py` parses the image path and optional `--production` flag.
2. `main.py` creates an `OCRPipeline` instance.
3. `OCRPipeline.run()` calls `YoloDetector.detect()` to get text-region boxes.
4. `OCRPipeline.run()` calls `PaddleOCRReader.read_regions()` to read OCR per ROI.
5. `OCRPipeline.run()` calls `DocumentClassifier.classify()` to decide `Appointment`, `MedicineLabel`, or `Unknown`.
6. `OCRPipeline.run()` calls `FieldExtractor.extract()` which dispatches to:
   - `AppointmentExtractor.extract()`
   - `MedicineExtractor.extract()`
7. `OCRPipeline.run()` calls `DataValidator.validate()` for normalization and cleanup.
8. `OCRPipeline.run()` calls `GemmaPostProcessor.postprocess()` to optionally clean OCR noise with Gemma/Ollama.
9. `OCRPipeline.run()` calls `FinalOutputFormatter.format()` to create the clean JSON contract.
10. `OCRPipeline.run()` writes `runtime/final_output/{stem}.json` and the debug trace.
11. `main.py` writes production output to `runtime/outputs/result.json` when `--production` is set.

## Evaluation Call Paths

### `evaluation/evaluate.py`

```text
evaluation/evaluate.py
  ├── validate_dataset()
  ├── OCRPipeline
  ├── calculate_cer()
  └── calculate_field_accuracy()
```

Purpose:

- Runs benchmark evaluation against ground truth.
- Uses full OCR pipeline output.
- Produces summary reports and per-sample predictions.

### `evaluation/run_pipeline_diagnosis.py`

```text
evaluation/run_pipeline_diagnosis.py
  └── OCRPipeline
```

Purpose:

- Diagnoses which stage failed per image.
- Summarizes YOLO, OCR, classification, and field completion rates.

### `evaluation/run_detection_ocr_report.py`

```text
evaluation/run_detection_ocr_report.py
  ├── YoloDetector
  └── PaddleOCRReader
```

Purpose:

- Measures detection + OCR only.
- Writes summary reports to `reports/`.
- Stores visual artifacts under `archive/legacy/visual_tools/`.

### `evaluation/run_visual_dashboard.py`

```text
evaluation/run_visual_dashboard.py
  ├── OCRPipeline
  └── YoloDetector
```

Purpose:

- Builds an HTML dashboard for human inspection.
- Shows original image, annotated YOLO output, OCR regions, and final JSON.
- Stores the dashboard under `archive/legacy/visual_tools/`.

### `evaluation/export_web_results.py`

```text
evaluation/export_web_results.py
  └── build_production_output()
```

Purpose:

- Converts debug final outputs into clean web-ready JSON.
- Writes `runtime/outputs/web_ready_results.json`.

## Support Utilities

- `tools/validate_input_images.py` validates image quality before dataset import.
- `tools/final_project_check.py` performs final smoke checks and runtime path checks.
- `tools/project_audit.py` and `tools/structure_audit.py` generate repository audits.
- `tools/dataset_readiness.py` checks whether the benchmark dataset folders exist.
