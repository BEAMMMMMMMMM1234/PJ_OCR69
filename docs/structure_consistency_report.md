# Structure Consistency Report

## 1. Current Project Structure
- Total files scanned: `4132`
- Runtime debug files: `2202`
- Runtime output files: `286`

## 2. Expected Project Structure
```text
PJ_OCR69/
├── core/
├── extractors/
├── evaluation/
│   ├── appointment/
│   │   ├── images/
│   │   ├── ground_truth/
│   │   ├── predictions/
│   │   └── reports/
│   ├── medicine/
│   │   ├── images/
│   │   ├── ground_truth/
│   │   ├── predictions/
│   │   └── reports/
│   ├── prepare_dataset.py
│   ├── validate_dataset.py
│   ├── evaluate.py
│   └── run_detection_ocr_report.py
├── models/
│   ├── yolo/best.pt
│   └── paddle/
├── runtime/
│   ├── debug/
│   ├── outputs/
│   └── logs/
├── reports/
├── tools/
├── docs/
├── archive/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-docker.txt
├── README.md
└── main.py
```

## 3. Dataset Location
- Appointment images missing: 0
- Appointment ground truth missing: 0
- Medicine images missing: 0
- Medicine ground truth missing: 0

## 4. Docker Path Consistency
- Docker issues: 0
- none

## 5. Broken or Outdated Path References
- Broken references: 38
- `file`: `main.py`, `reference`: `outputs/`
- `file`: `Dockerfile`, `reference`: `app/requirements-docker.txt`
- `file`: `Dockerfile`, `reference`: `download.pytorch.org/whl/cpu`
- `file`: `Dockerfile`, `reference`: `var/lib/apt/lists`
- `file`: `README.md`, `reference`: `27/10/2568`
- `file`: `README.md`, `reference`: `Ollama/Gemma`
- `file`: `README.md`, `reference`: `docs/web_handoff.md`
- `file`: `README.md`, `reference`: `outputs/`
- `file`: `README.md`, `reference`: `reports/evaluation_report.json`
- `file`: `README.md`, `reference`: `reports/report.json`
- `file`: `README.md`, `reference`: `reports/summary_report.json`
- `file`: `README.md`, `reference`: `runtime/outputs/web_ready_results.json`
- `file`: `README.md`, `reference`: `yolo/best.pt`
- `file`: `tools/project_audit.py`, `reference`: `Debug/Cache`
- `file`: `tools/project_audit.py`, `reference`: `docs/project_cleanup_report.md`
- `file`: `tools/project_audit.py`, `reference`: `docs/project_file_inventory.json`
- `file`: `tools/project_audit.py`, `reference`: `evaluation/dataset_validation_report.json`
- `file`: `tools/project_audit.py`, `reference`: `evaluation/evaluation_report.json`
- `file`: `tools/project_audit.py`, `reference`: `evaluation/field_accuracy.pymv`
- `file`: `tools/project_audit.py`, `reference`: `evaluation/report.json`
- `file`: `tools/project_audit.py`, `reference`: `evaluation/summary_report.json`
- `file`: `tools/project_audit.py`, `reference`: `extractors/medicine_extractor.pytouch`
- `file`: `tools/project_audit.py`, `reference`: `legacy/sample`
- `file`: `tools/project_audit.py`, `reference`: `outputs/`
- `file`: `tools/project_audit.py`, `reference`: `outputs/result.json`
- `file`: `tools/structure_audit.py`, `reference`: `Files/Directories`
- `file`: `tools/structure_audit.py`, `reference`: `debug/output/report`
- `file`: `tools/structure_audit.py`, `reference`: `evaluation/batch_report.json`
- `file`: `tools/structure_audit.py`, `reference`: `evaluation/dataset_validation_report.json`
- `file`: `tools/structure_audit.py`, `reference`: `evaluation/detection_ocr_report.json`
- `file`: `tools/structure_audit.py`, `reference`: `evaluation/detection_ocr_report.md`
- `file`: `tools/structure_audit.py`, `reference`: `evaluation/evaluation_report.json`
- `file`: `tools/structure_audit.py`, `reference`: `evaluation/report.json`
- `file`: `tools/structure_audit.py`, `reference`: `evaluation/summary_report.json`
- `file`: `tools/structure_audit.py`, `reference`: `legacy/sample`
- `file`: `tools/structure_audit.py`, `reference`: `outputs/`
- `file`: `tools/structure_audit.py`, `reference`: `something/file.ext`
- `file`: `tools/structure_audit.py`, `reference`: `yolo/best.pt`

### Outdated References
- none

## 6. Files/Directories That Should Be Kept
- `core/`
- `extractors/`
- `evaluation/*/images/`
- `evaluation/*/ground_truth/`
- `models/yolo/best.pt`
- `models/paddle/`
- `main.py`
- `requirements.txt`
- `requirements-docker.txt`

## 7. Files/Directories That Should Be Ignored
- `debug/`
- `outputs/`
- `runtime/debug/`
- `runtime/final_output/`
- `runtime/outputs/`
- `runtime/logs/`
- `evaluation/*/predictions/`
- `evaluation/*/reports/`
- `evaluation/summary_report.json`
- `evaluation/evaluation_report.json`
- `evaluation/dataset_validation_report.json`
- `evaluation/report.json`
- `evaluation/batch_report.json`
- `evaluation/detection_ocr_report.json`
- `evaluation/detection_ocr_report.md`
- `archive/legacy/visual_tools/`

## 8. Files/Directories That Should Be Archived
- `archive/legacy/`
- `legacy sample reference paths in docs and Docker`
- `old accidental files if any appear again, e.g. *.pymv / *.pytouch`

## 9. Recommended Commands
```bash
python tools/structure_audit.py
docker compose build
docker compose run --rm ocr python main.py evaluation/appointment/images/A01.jpg
docker compose run --rm ocr python evaluation/run_detection_ocr_report.py
python evaluation/validate_dataset.py
python evaluation/evaluate.py
```

## 10. Safe Cleanup Plan
1. Keep `evaluation/*/images/` and `evaluation/*/ground_truth/` as benchmark data.
2. Keep `data/test_images/` only as legacy/sample input; do not use it as the primary quick-test path.
3. Ignore generated debug/output/report files in Git.
4. Archive legacy or accidental files instead of deleting them.
5. Re-run the audit after any cleanup change.

## Inventory Notes
- Sample input files: `0`
- Archive files: `1265`
- Generated debug files: `2202`
- Generated output files: `286`