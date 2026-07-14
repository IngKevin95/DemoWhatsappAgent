# Stage 1: Build
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    libfbclient2 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Run tests with coverage
RUN pytest --cov=agent --cov-report=term-missing --co -q || true
RUN pytest --cov=agent --cov-report=xml --cov-report=term -v 2>&1 | tee test-results.log

# Check coverage threshold (70%)
RUN python -c "import xml.etree.ElementTree as ET; root = ET.parse('coverage.xml').getroot(); coverage = float(root.get('line-rate')) * 100; print(f'Coverage: {coverage:.1f}%'); exit(0 if coverage >= 70 else 1)"

# ---

# Stage 2: Runtime
FROM python:3.11-alpine

RUN apk add --no-cache libfbclient

WORKDIR /app

# Copy only pip packages from builder
COPY --from=builder /root/.local /root/.local

# Copy only app code (no tests, no git)
COPY agent/ ./agent/
COPY gunicorn_conf.py .

# Set PATH for local pip packages
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=5s \
    CMD python -c "import requests; requests.get('http://localhost:8000/ready', timeout=5)" || exit 1

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn_conf.py", "agent.main:app"]
