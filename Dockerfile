FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PADDLE_PDX_CACHE_HOME=/app/.paddlex \
    MPLCONFIGDIR=/app/.mplconfig

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt /app/requirements-docker.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch==2.3.1 torchvision==0.18.1 && \
    pip install --no-cache-dir -r requirements-docker.txt

COPY . /app

CMD ["python", "main.py", "evaluation/appointment/images/A01.jpg"]
