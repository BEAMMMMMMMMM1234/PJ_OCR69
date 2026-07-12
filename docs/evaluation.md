# Evaluation Guide

## Purpose

Evaluation in PJ_OCR69 measures how well the OCR pipeline performs on the benchmark dataset.

## Dataset Layout

- Appointment images: `evaluation/appointment/images/`
- Appointment ground truth: `evaluation/appointment/ground_truth/`
- Medicine images: `evaluation/medicine/images/`
- Medicine ground truth: `evaluation/medicine/ground_truth/`

## Reports

- `reports/pipeline_diagnosis_report.json`
- `reports/pipeline_diagnosis_report.md`
- `reports/summary_report.json`
- `reports/dataset_validation_report.json`
- `reports/evaluation_report.json`

## What the Evaluation Checks

- YOLO detection success
- PaddleOCR recognition success
- Document classification accuracy
- Appointment field completion
- Medicine field completion

## Notes

- Evaluation is read-only for pipeline results
- Generated prediction and report files should be ignored by Git
- Ground truth should not be changed by evaluation scripts
