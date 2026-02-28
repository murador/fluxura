FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY celeryconfig.py /app/celeryconfig.py

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

CMD ["celery", "-A", "fluxura.celery_app:celery_app", "worker", "-l", "info"]
