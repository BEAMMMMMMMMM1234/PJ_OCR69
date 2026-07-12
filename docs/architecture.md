# PJ_OCR69 Architecture

## Overview

PJ_OCR69 is a Thai OCR document processing pipeline.

## Flow

1. Input image
2. YOLO text-region detection
3. PaddleOCR recognition on each ROI in memory
4. Weighted document classification
5. Rule-based field extraction
6. Validation and normalization
7. Gemma approval layer
8. Final output formatting
9. Structured JSON output generation

## Runtime Layers

- `runtime/final_output/` is the single source of truth for clean per-image JSON for web/API handoff
- `runtime/debug/` stores debug artifacts such as annotated images, OCR evidence, classification JSON, and pipeline traces
- `runtime/debug/gemma/` stores Gemma prompt/response/latency/approval traces
- `runtime/outputs/result.json` stores only the latest clean output
- `reports/` stores processing reports and evaluation summaries
- `runtime/logs/` stores runtime logs

## Source Layers

- `core/` contains pipeline logic
- `extractors/` contains rule-based field extraction
- `prompts/` contains Gemma prompt templates
- `evaluation/` contains benchmark scripts and dataset tools
- `tools/` contains audit and validation utilities
- Legacy dead code has been archived under `archive/legacy/dead_core/`
- `production_output.py` is a writer/helper layer only; schema selection must come from `FinalOutputFormatter`

## Stability Rules

- Do not change YOLO, PaddleOCR, classification, extraction, validation, or Gemma logic unless a bug is confirmed
- Keep benchmark images and ground truth separate from generated outputs
- Prefer runtime folders for generated artifacts
- Archive legacy dead code instead of reintroducing it into `core/`
