# DemoWhatsappAgent

Bot conversacional de WhatsApp para asesoría comercial, soporte técnico y gestión de licencias.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

## Running Tests

### All tests
```bash
pytest -v
```

### Unit tests only
```bash
pytest tests/unit/ -m unit -v
```

### With coverage report
```bash
pytest --cov=agent --cov-report=html
open htmlcov/index.html
```

### Watch mode (re-run on changes)
```bash
pip install pytest-watch
ptw
```

## Test Structure

- `tests/unit/` — Unit tests (mocked dependencies)
  - `test_brain.py` — Conversation logic, intent classification
  - `test_main.py` — Webhook validation, rate limiting
  - `test_tools.py` — Tool execution (escalar, agendar, consultar)
  - `test_memory.py` — Persistence layer
  
- `tests/e2e/` — End-to-end tests (full webhook flow)

- `tests/conftest.py` — Shared fixtures (mocks for Gemini, Google Calendar, EspoCRM, Postgres)

## Coverage

Target: ≥60% (enforced in CI with `--cov-fail-under=60`)

## CI/CD

Tests run automatically on:
- Push to `main`, `develop`, or `feature/*`
- Pull requests to `main` or `develop`

See `.github/workflows/test.yml` for details.

## Architecture

- `agent/main.py` — FastAPI webhook receiver
- `agent/brain.py` — LLM orchestration (Gemini)
- `agent/tools.py` — Tool implementations (escalar, agendar, etc.)
- `agent/memory.py` — Chat history persistence (Postgres)
- `agent/integrations/` — External service wrappers (Google, EspoCRM, Firebird)

## Development

```bash
# Run server locally
python -m uvicorn agent.main:app --reload

# Access: http://localhost:8000/docs (OpenAPI Swagger UI)
```
