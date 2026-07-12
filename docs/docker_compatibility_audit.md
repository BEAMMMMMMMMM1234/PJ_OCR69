# Docker Compatibility Audit

## Scope

Audit of the Docker runtime for PJ_OCR69 based on the real project files:

- `Dockerfile`
- `docker-compose.yml`
- `requirements-docker.txt`
- `requirements.txt`
- `.dockerignore`
- `core/paddle_ocr.py`
- `core/ocr_pipeline.py`

This is an audit report only. No OCR, YOLO, dataset, or model logic was changed for this review.

## Current Dockerfile Summary

- Base image: `python:3.10-slim`
- Package install flow:
  - `apt-get update`
  - installs `libglib2.0-0`, `libgl1`, `libgomp1`, `libsm6`, `libxext6`, `libxrender1`, `ffmpeg`, `git`
  - upgrades `pip`
  - installs CPU `torch` / `torchvision` from the PyTorch CPU index
  - installs `requirements-docker.txt`
- Working directory: `/app`
- Default command: `python main.py evaluation/appointment/images/A01.jpg`
- Cache cleanup:
  - `rm -rf /var/lib/apt/lists/*` is present
- Runtime env:
  - `PYTHONUNBUFFERED=1`
  - `PIP_NO_CACHE_DIR=1`

### Observations

- The Dockerfile is already biased toward CPU inference.
- The image is slim, which reduces size but increases the risk of missing shared libraries for Paddle/PaddleOCR C++ components.
- The Dockerfile does not set any OpenMP / MKL / Paddle runtime stabilization variables.

## Current docker-compose Summary

- Service name: `ocr`
- Build context: repository root
- Working directory: `/app`
- Volume mount: `.:/app`
- Interactive terminal enabled:
  - `stdin_open: true`
  - `tty: true`
- Environment:
  - `PYTHONUNBUFFERED=1`
  - `OLLAMA_HOST=http://host.docker.internal:11434`
- Command: `bash`

### Observations

- No explicit `platform:` is set.
- On Apple Silicon, Docker Desktop will generally follow the host architecture unless overridden.
- On Windows handoff, the lack of an explicit platform means behavior can vary depending on the host and Docker Desktop settings.

## Current requirements-docker Summary

- `ultralytics>=8.2.0`
- `paddleocr>=3.0.0`
- `paddlepaddle>=3.0.0`
- `opencv-python-headless>=4.10.0`
- `pillow>=10.0.0`
- `numpy>=1.26.0`
- `requests>=2.31.0`
- `PyYAML>=6.0.1`

### Observations

- This file is already CPU-oriented.
- It does not pin exact versions, so Docker builds may drift over time.
- `opencv-python-headless` is the right choice for container inference.
- `torch` is installed separately in the Dockerfile from the CPU wheel index, which reduces CUDA dependency risk.

## Current requirements.txt Summary

- `ultralytics>=8.2.0`
- `pillow>=10.0.0`
- `opencv-python>=4.10.0`
- `paddleocr>=3.0.0`

### Observations

- `requirements.txt` is for local/dev use and still uses GUI OpenCV.
- For Docker runtime, `requirements-docker.txt` is the more relevant file.

## Current .dockerignore Summary

Ignored:

- `.venv/`
- `debug/`
- `outputs/`
- `runtime/debug/`
- `runtime/outputs/`
- `runtime/reports/`
- `runtime/logs/`
- `archive/`
- generated evaluation outputs
- `reports/`

### Observations

- The ignore list is broad and suitable for keeping generated files out of the image build context.
- It does not ignore the benchmark image folders or ground-truth folders, which is correct.

## Detected Architecture

- Host architecture from `uname -m`: `arm64`
- This means the development machine is macOS Apple Silicon.

### Inference

- Because `docker-compose.yml` does not pin a platform, Docker is likely building/running an `arm64` Linux image on Apple Silicon unless Docker Desktop or an explicit `--platform` overrides it.

## PaddleOCR / PaddlePaddle Compatibility Risk

The failure reported by the user is:

- `FatalError: Segmentation fault`
- `SIGSEGV`
- during `evaluation/run_pipeline_diagnosis.py`

The relevant runtime call path is:

- `OCRPipeline.run()`
- `PaddleOCRReader.read_regions()`
- `TextRecognition.predict(roi)`

### Root Cause Hypothesis

This is most likely a runtime/native dependency issue, not a Python syntax or business-logic issue.

Most probable causes, from lower to higher confidence:

1. Missing or incompatible shared libraries in the slim image
   - especially `libgomp1`, `libstdc++6`, OpenMP-related runtime pieces, or OpenCV/Paddle shared objects
2. PaddleOCR / PaddlePaddle wheel mismatch with the running architecture
   - `arm64` vs `amd64`
3. OpenMP / thread-related instability in the container
4. Incompatible combination of `paddlepaddle` and `paddleocr` versions
5. Less likely: OpenCV image/GUI dependency issue

### Why this is probably runtime, not pipeline logic

- The crash is a segmentation fault inside the C++ runtime, not a Python exception.
- The OCR pipeline itself already runs outside Docker.
- The failure appears only in Docker execution.

## Architecture Compatibility Analysis

### Mac Apple Silicon

- Best native fit: `linux/arm64`
- Advantage:
  - no x86 emulation penalty
  - faster startup and runtime
- Risk:
  - PaddleOCR / PaddlePaddle arm64 wheel stability can vary

### Windows Handoff

- Most predictable cross-team handoff:
  - `linux/amd64`
- Advantage:
  - closer to common Docker/CI assumptions
  - easier to align with x86 CI and many prebuilt wheels
- Risk:
  - slower on Apple Silicon because of emulation

### Estimated Performance Tradeoff

- `linux/amd64` on Apple Silicon usually runs noticeably slower than native arm64 because of emulation.
- For OCR inference, the slowdown is typically acceptable for development/demo, but exact slowdown depends on image size, PaddleOCR model, and host CPU.

## Recommended Option

### Recommended: Option C, Hybrid

- Use local Python environment for day-to-day Mac development.
- Use Docker as the stable handoff/runtime contract for Windows and team sharing.
- Prefer Docker `linux/amd64` if the priority is consistent handoff and reproducible runtime behavior.

### Why

- The current failure is likely in the native runtime layer.
- `linux/amd64` tends to be the safer compatibility target for PaddleOCR/PaddlePaddle packaging in team handoff scenarios.
- If the team needs native Apple Silicon speed later, that can be revisited after the Docker runtime is stable.

## Exact File Changes Recommended

### Dockerfile

- Add runtime stabilization env vars:
  - `OMP_NUM_THREADS=1`
  - `MKL_NUM_THREADS=1`
  - `FLAGS_use_mkldnn=false`
  - `FLAGS_allocator_strategy=auto_growth`
- Consider a less aggressive slim baseline if segmentation continues:
  - `python:3.10-bullseye` or similar
- Keep CPU torch install from the PyTorch CPU index
- Keep `opencv-python-headless`

### docker-compose.yml

- Add an explicit platform if the team chooses a fixed target:
  - `platform: linux/amd64` for Windows-first stability
  - `platform: linux/arm64` for Apple Silicon-native development
- Keep `OLLAMA_HOST=http://host.docker.internal:11434`

### requirements-docker.txt

- Pin exact versions for:
  - `paddlepaddle`
  - `paddleocr`
  - `ultralytics`
  - `opencv-python-headless`
  - `numpy`
- Keep `torch` and `torchvision` CPU-only installation in Dockerfile

### tools/docker_runtime_check.py

- Add a minimal runtime sanity script for Docker validation only.

## Exact Commands to Test After Changes

### Build

```bash
docker compose build
```

### Runtime smoke check

```bash
docker run --rm pj_ocr69-ocr:latest python tools/docker_runtime_check.py
```

### Single-image OCR

```bash
docker run --rm -v "$PWD":/app -w /app -e USE_GEMMA=false pj_ocr69-ocr:latest python main.py evaluation/appointment/images/A01.jpg --production
```

### Pipeline diagnosis

```bash
docker run --rm -v "$PWD":/app -w /app -e USE_GEMMA=false pj_ocr69-ocr:latest python evaluation/run_pipeline_diagnosis.py
```

## Conclusion

- The failure is most likely a Docker runtime / native dependency issue, not a Python logic issue.
- The highest-risk area is PaddleOCR / PaddlePaddle C++ runtime compatibility inside a slim container.
- For team handoff, `linux/amd64` is the safer default recommendation.
- For local Mac speed, `linux/arm64` is attractive but carries more Paddle runtime risk.

