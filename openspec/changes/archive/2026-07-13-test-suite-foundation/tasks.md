# Tasks: Test Suite Foundation (EP-001)

## Objetivo
Implementar infraestructura de testing, escribir tests unitarios para módulos críticos (brain.py, tools.py, memory.py, main.py), configurar CI/CD y garantizar coverage ≥60%.

---

## Bloque 1: Infraestructura (Blocker para todos los tests)

- [ ] **T1.1** Actualizar `requirements.txt`: agregar pytest, pytest-asyncio, pytest-cov
  - Verificar: `pip install -r requirements.txt` sin error
  
- [ ] **T1.2** Crear `pytest.ini` en raíz del proyecto
  - Secciones: asyncio_mode=auto, markers (unit, integration, e2e), testpaths=tests
  - Verificar: `pytest --collect-only` lista ≥30 tests

- [ ] **T1.3** Extender `tests/conftest.py` con fixtures
  - mock_gemini, mock_google_calendar, mock_espocrm, mock_postgres, mock_meta_webhook
  - Verificar: `pytest --fixtures | grep mock_` muestra todas

---

## Bloque 2: Unit Tests — brain.py

- [ ] **T2.1** Escribir tests para `generar_respuesta()`
  - AC: happy path, timeout fallback, mock Gemini <100ms
  - Target: ≥5 test cases, coverage ≥95%

- [ ] **T2.2** Escribir tests para `clasificar_intencion()`
  - AC: todos los intents (PRECIO, DISPONIBILIDAD, SOPORTE, etc.), confidence ≥0.7
  - Target: ≥5 test cases, coverage ≥95%

- [ ] **T2.3** Escribir tests para `guardrails_check()`
  - AC: SQL injection, XSS, script injection bloqueados
  - Target: ≥5 test cases, coverage ≥90%

- [ ] **T2.4** Correr `pytest tests/unit/test_brain.py -v`
  - Todos los tests deben pasar
  - Verificar: 0 failures, coverage ≥95%

---

## Bloque 3: Unit Tests — tools.py (Nueva)

- [ ] **T3.1** Crear `tests/unit/test_tools.py`
  - Tests para escalar_a_humano(), agendar_cita(), consultar_precio_modulo()
  - Incluir retry logic: 3 intentos con backoff exponencial
  - Target: ≥12 test cases, coverage ≥90%

- [ ] **T3.2** Extender mock_espocrm, mock_google_calendar en conftest.py
  - Simular creación de case, envío de email, creación de evento
  - Simular fallos intermitentes (para probar retry)

- [ ] **T3.3** Correr `pytest tests/unit/test_tools.py -v`
  - Todos los tests deben pasar
  - Verificar: 0 failures, coverage ≥90%

---

## Bloque 4: Unit Tests — memory.py (Nueva)

- [ ] **T4.1** Crear `tests/unit/test_memory.py`
  - Tests para obtener_historial(), guardar_contexto(), limpiar_sesion()
  - Verificar GDPR compliance (no DELETE directo, solo archivado)
  - Target: ≥10 test cases, coverage ≥85%

- [ ] **T4.2** Mock Postgres connection pool en conftest.py
  - Simular conexión exitosa y con retry

- [ ] **T4.3** Correr `pytest tests/unit/test_memory.py -v`
  - Todos los tests deben pasar

---

## Bloque 5: Unit Tests — main.py

- [ ] **T5.1** Extender `tests/unit/test_main.py`
  - Firma HMAC Meta: válida y inválida
  - Rate limiting: 10 req/min por IP, request 11+ → 429
  - Input sanitization: XSS/SQL injection removidos
  - Target: ≥8 test cases, coverage ≥90%

- [ ] **T5.2** Mock Meta webhook en conftest.py
  - Payload válido, firma correcta/incorrecta
  - IP spoofing detection

- [ ] **T5.3** Correr `pytest tests/unit/test_main.py -v`
  - Todos los tests deben pasar

---

## Bloque 6: Coverage Enforcement

- [ ] **T6.1** Agregar a `pytest.ini`: `--cov-fail-under=60`
  - Verificar: `pytest --cov=agent` retorna coverage ≥60% o falla

- [ ] **T6.2** Generar coverage report HTML
  - `pytest --cov=agent --cov-report=html`
  - Verificar: `htmlcov/index.html` generado

- [ ] **T6.3** Verificar coverage por módulo (agent/*.py)
  - brain.py ≥95%, tools.py ≥90%, memory.py ≥85%, main.py ≥90%

---

## Bloque 7: CI/CD Workflow

- [ ] **T7.1** Crear `.github/workflows/test.yml`
  - on: push, pull_request
  - Setup Python 3.11, pip install, pytest --cov
  - addopts: --cov-fail-under=60 (falla si coverage <60%)

- [ ] **T7.2** Agregar codecov/codecov-action step
  - Publica coverage report a codecov.io

- [ ] **T7.3** Verificar workflow en GitHub
  - Corre automáticamente en cada push
  - Build status visible en PRs
  - Coverage badge actualizado

---

## Bloque 8: Documentación

- [ ] **T8.1** Actualizar README.md
  - Sección "Running Tests": `pytest`, `pytest -m unit`, `pytest --cov`
  - Coverage badge (codecov)
  - Link a htmlcov/index.html

- [ ] **T8.2** Documento: "How to add a new test"
  - Estructura de fixtures
  - Markers (unit, integration, e2e)
  - Mock patterns

---

## Verificación Final (DoD)

- [ ] Todos los tests pasan: `pytest -v` = 0 failures
- [ ] Coverage ≥60%: `pytest --cov=agent` ≥60%
- [ ] CI workflow activo: `.github/workflows/test.yml` existe y pasa
- [ ] Coverage badge en README
- [ ] PR se puede mergear sin warnings

---

## Estimación

| Bloque | Tareas | Story Points | Tiempo |
|--------|--------|--------------|--------|
| 1. Infraestructura | T1.1-T1.3 | 3 | 1d |
| 2. brain.py tests | T2.1-T2.4 | 3 | 1.5d |
| 3. tools.py tests | T3.1-T3.3 | 3 | 1.5d |
| 4. memory.py tests | T4.1-T4.3 | 2 | 1d |
| 5. main.py tests | T5.1-T5.3 | 2 | 1d |
| 6. Coverage | T6.1-T6.3 | 1 | 0.5d |
| 7. CI/CD | T7.1-T7.3 | 2 | 1d |
| 8. Docs | T8.1-T8.2 | 1 | 0.5d |
| **TOTAL** | **23 tasks** | **17 points** | **~2-3 sem** |

---

## Definición de Listo (DoR)

- ✓ Todas las HU de EP-001 tienen AC en Given/When/Then
- ✓ proposal.md + design.md + specs creados (este change)
- ✓ No hay dependencias bloqueantes (scaffold confirmado)
