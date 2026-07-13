## Arquitectura del Test Suite

### Visión General

Tests organizados en 3 niveles (pirámide):
```
         E2E (webhook scenarios)
       /                       \
    Integration            Integration
   (mock services)        (mock services)
    /            \        /              \
  Unit          Unit    Unit             Unit
 (brain)       (main)  (tools)        (memory)
```

- **Unit (80% del esfuerzo):** Funciones individuales con mocks de dependencias externas
- **Integration (15%):** Flujos entre módulos (brain → tools → integrations) con mocks de Google/EspoCRM/Firebird
- **E2E (5%):** Webhook end-to-end (simula request Meta → respuesta bot) sin mocks

### Decisiones Clave

**D1: Mock vs. Real Servicios**
- Google Calendar, EspoCRM, Firebird: siempre mocks en tests (no llamadas reales)
- Razón: No queremos degradación de tests si servicios externos están down; tests deben ser <30s cada uno
- Excepción: Smoke phase (después de esta épica) hará verificación con servicios reales

**D2: Async/Await en Tests**
- Todos los tests de main.py y brain.py usan `@pytest.mark.asyncio`
- Razón: main.py es FastAPI (async), brain.py usa genai.Client (async)
- conftest.py carga `pytest-asyncio` con mode="auto"

**D3: Coverage Target ≥60%**
- 60% es el mínimo legal para producción (15 de 25 LP de Fase 1 release)
- Se mide con `pytest --cov=agent --cov-report=html`
- Falla el CI si coverage < 60%

**D4: Fixtures Compartidas**
- `conftest.py` centraliza mocks de Gemini, EspoCRM, Google, Postgres
- Evita duplicación de setup en cada test
- Razón: mantenimiento centralizado, cambios a un mock = reflejan en todos los tests

### Estructura de Directorios

```
tests/
├── conftest.py                    # Fixtures globales
├── unit/
│   ├── test_brain.py             # generar_respuesta, clasificar_intencion, etc.
│   ├── test_main.py              # recibir_webhook, validación firma Meta
│   ├── test_tools.py             # escalar_a_humano, agendar_cita (nuevos)
│   ├── test_memory.py            # obtener_historial, guardar_contexto (nuevos)
│   └── test_retry_logic.py       # Decorator retry + exponential backoff
└── e2e/
    └── test_webhook_scenarios.py # Flujos end-to-end (webhook → respuesta)
```

### Fixtures (conftest.py)

```python
@pytest.fixture
def mock_gemini():
    # Mock genai.Client.models.generate_content
    # Retorna respuesta sintética en <100ms
    
@pytest.fixture
def mock_google_calendar():
    # Mock Google Calendar API (crear evento)
    
@pytest.fixture
def mock_espocrm():
    # Mock EspoCRM REST API (crear case, enviar email)
    
@pytest.fixture
def mock_postgres():
    # Mock SQLAlchemy connection pool
    
@pytest.fixture
def mock_meta_webhook():
    # Meta webhook payload válido (HMAC firma incluida)
```

### Pytest Configuration (pytest.ini)

```ini
[pytest]
asyncio_mode = auto
markers =
    unit: tests unitarios (sin red)
    integration: tests con mocks de servicios
    e2e: webhook end-to-end
testpaths = tests
addopts = --cov=agent --cov-fail-under=60 --cov-report=html
```

### CI/CD Workflow (.github/workflows/test.yml)

```yaml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=agent --cov-report=xml
      - uses: codecov/codecov-action@v3  # Upload coverage report
```

### Criterios de Éxito (DoD)

- [ ] pytest.ini creado y configurado (async, markers, coverage)
- [ ] requirements.txt incluye pytest, pytest-asyncio, pytest-cov
- [ ] Todos los tests pasan en main.py, brain.py, tools.py, memory.py
- [ ] Coverage ≥60% en agent/
- [ ] CI workflow activo (GitHub Actions test.yml)
- [ ] Badge de coverage en README

### Riesgos y Mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| Tests lentos (latencia acumulada) | Todos los mocks: <100ms cada uno; target suite <30s |
| Mocks desalineados con realidad | Design spec detalla contrato de cada mock |
| Async tests fallan aleatoriamente | pytest-asyncio mode="auto" evita race conditions |

### Próxima Fase (No en esta épica)

- EP-002: Error Handling (retry logic, circuit breakers)
- EP-005: Deployment (monitoring, alertas, production smoke tests)
- Release Gate: Security review, UX audit, Arquitectura review
