# Web Handoff

## What The Web Team Should Use

- `runtime/final_output/*.json`
- `runtime/outputs/result.json`

## What The Web Team Should Not Use

- `runtime/debug/*`
- `runtime/debug/pipeline_trace/*`
- `runtime/debug/ocr_evidence/*`
- `runtime/debug/classification/*`
- `runtime/debug/gemma/*`
- `runtime/debug/final_output/*` if it still exists in an old archive

## Final Output Schema

### MedicineLabel

```json
{
  "status": "success",
  "document_type": "MedicineLabel",
  "data": {
    "medicine_name": "...",
    "usage_instruction": "..."
  },
  "error": null
}
```

### Appointment

```json
{
  "status": "success",
  "document_type": "Appointment",
  "data": {
    "appointment_date": "...",
    "appointment_time": "...",
    "preparation_instruction": "..."
  },
  "error": null
}
```

## Contract Rules

- `FinalOutputFormatter` defines the schema.
- `production_output.py` only writes or wraps already-clean output.
- Gemma prompt files live in `prompts/`.
- Legacy helpers `core/gemma_formatter.py` and `core/json_builder.py` were archived because they are dead code.

## Run Commands

```bash
python main.py evaluation/medicine/images/M01.jpg --production
python main.py evaluation/appointment/images/A01.jpg --production
```

## Notes

- The web team should treat `runtime/final_output/*.json` as the source of truth for per-image output.
- `runtime/outputs/result.json` is only the latest result from the most recent run.
- Debug folders are for developers only and may change without notice.
