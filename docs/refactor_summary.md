# Refactor Summary

## What Changed

- Gemma is now treated as an approval layer with debug traces.
- Clean production output remains in `runtime/final_output/*.json`.
- Latest run output remains in `runtime/outputs/result.json`.
- Prompt templates were moved out of Python code into `prompts/`.
- Gemma debug artifacts are written to `runtime/debug/gemma/`.

## Architecture Before

- OCR pipeline and output formatting were more tightly coupled.
- Gemma prompt text lived inside Python code.
- Debug artifacts were less clearly separated from approval traces.

## Architecture After

- `main.py` acts as CLI entry point.
- `core/ocr_pipeline.py` orchestrates stages.
- `core/gemma_postprocessor.py` handles Gemma approval and debug trace writing.
- `core/final_output_formatter.py` creates the web-ready JSON schema.
- `core/production_output.py` owns production output helpers and summary helpers.

## Files Added

- `prompts/appointment_prompt.txt`
- `prompts/medicine_prompt.txt`
- `docs/refactor_summary.md`

## Files Updated

- `core/gemma_postprocessor.py`
- `core/ocr_pipeline.py`
- `core/production_output.py`
- `README.md`
- `docs/architecture.md`

## Files Retained

- `core/yolo_detector.py`
- `core/paddle_ocr.py`
- `core/document_classifier.py`
- `core/field_extractor.py`
- `core/validator.py`
- `core/final_output_formatter.py`
- `evaluation/*`
- `tools/*`

## Notes

- No OCR algorithm was changed.
- No YOLO model or PaddleOCR model was changed.
- Final web output schema remains the same.
- Debug traces now include Gemma prompt, response, approval, latency, and changed fields.
