# Pytest Infrastructure

## Descripción

Infraestructura de testing: configuración de pytest, fixtures compartidas, markers para categorización de tests.

## Requisitos

### R1: pytest.ini con configuración de async y markers
**Given** se crea pytest.ini en raíz del proyecto  
**When** se ejecuta `pytest --version`  
**Then** pytest detecta asyncio_mode=auto, markers personalizados (unit, integration, e2e), testpaths=tests

### R2: conftest.py con fixtures globales
**Given** conftest.py existe en tests/  
**When** se ejecuta `pytest --fixtures`  
**Then** muestra mock_gemini, mock_google_calendar, mock_espocrm, mock_postgres, mock_meta_webhook

### R3: pytest en requirements.txt
**Given** se actualiza requirements.txt  
**When** se ejecuta `pip install -r requirements.txt`  
**Then** pytest, pytest-asyncio, pytest-cov quedan instalados

### R4: Async test execution
**Given** se corre un test con `@pytest.mark.asyncio`  
**When** test usa `async def test_...` y llama `await`  
**Then** pytest ejecuta el test en event loop sin timeout (conftest controla loop)

## Artefactos

- `pytest.ini` (config)
- `tests/conftest.py` (fixtures)
- `requirements.txt` actualizado
- Documentación: "How to run tests locally" en README.md

## Criterios de Aceptación

- pytest.ini existe, todas las secciones presentes
- conftest.py compila sin error
- `pytest --collect-only` lista ≥30 tests
- `pytest -m unit` ejecuta solo tests unitarios
- AsyncIO tests se ejecutan <100ms cada uno
