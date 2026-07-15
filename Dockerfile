# ponytail: single-stage debian-slim. Tests run in CI (.github/) + local pytest,
# not baked into the image build — coupling artifact build to the suite was broken
# (pytest not on PATH, alpine musl vs glibc wheels) and only blocked `compose up`.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libfbclient2 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + runtime data (config for prompts.yaml, scripts for the seed service)
COPY agent/ ./agent/
COPY config/ ./config/
COPY knowledge/ ./knowledge/
COPY scripts/ ./scripts/
COPY static/ ./static/
COPY gunicorn_conf.py .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check (urllib is stdlib — requests isn't installed)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready', timeout=5)" || exit 1

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn_conf.py", "agent.main:app"]
