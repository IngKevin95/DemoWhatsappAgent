## Why

DemoWhatsappAgent tiene código crítico sin cobertura de tests formal. El bridge node `generar_respuesta()` (betweenness 0.000565) y hub nodes `escalar_a_humano()` (degree 32), `agendar_cita()` (degree 23) son vulnerables a cambios regresivos. **Hoy: 0 tests dedicados en suite formal.** Esto bloquea refactorización segura y produce confianza baja en deploys a producción.

Target: test coverage ≥60% en módulos críticos (brain.py, tools.py, memory.py, main.py). Blocker de Fase 2 (toda release pasa por Release Gate que exige esta cobertura).

## What Changes

- **Agregar pytest + pytest-asyncio + pytest-cov** a requirements.txt
- **Configurar pytest.ini** con markers (unit, integration, e2e), asyncio mode, coverage thresholds
- **Crear GitHub Actions workflow** (`.github/workflows/test.yml`) para CI automático
- **Extender tests unitarios** para cubrir generar_respuesta, escalar_a_humano, agendar_cita, memory layer
- **Configurar badge de coverage** en README
- **Documentar cómo correr tests localmente**

No se elimina ni modifica lógica de negocio. Los cambios son puramente de infraestructura de testing y CI/CD.

## Capabilities

### New Capabilities
- `pytest-infrastructure`: Framework, config, markers, asyncio integration
- `unit-tests-brain`: Tests unitarios para generar_respuesta(), clasificar_intencion(), guardrails_check()
- `unit-tests-tools`: Tests de integración mock para escalar_a_humano(), agendar_cita(), tools de consulta
- `unit-tests-memory`: Tests de persistencia (mock Postgres, obtener_historial, guardar_contexto)
- `unit-tests-main`: Tests de validación de firma Meta, rate limiting, sanitización
- `ci-cd-workflow`: GitHub Actions para correr tests en cada push/PR, publicar coverage
- `coverage-enforcement`: pytest-cov con target ≥60%, fail si no se cumple

### Modified Capabilities
(Ninguna. No se modifica comportamiento existente.)

## Impact

- **Code:** Archivos `agent/*.py` no cambian (solo se agregan tests)
- **Config:** Se agrega `pytest.ini`, se modifica `requirements.txt` y `pyproject.toml`
- **CI/CD:** Se crea `.github/workflows/test.yml`
- **Dependencies:** pytest, pytest-asyncio, pytest-cov (dev/test only)
- **Breaking changes:** Ninguno (tests son aditivos)

## Trazabilidad

Épica: **EP-001 (Test Suite Foundation)**

Historias cubiertas:
- HU-001, HU-002, HU-004, HU-005, HU-006, HU-007, HU-011a, HU-011b, HU-012, HU-013, HU-014, HU-015, HU-024, HU-025 (todas dentro de EP-001)

Validación:
- Todas las HU tienen AC en Given/When/Then
- Todas pertenecen a EP-001 (verificado en docs/04-historias/)
- Priorización: Sprint 1 (Quick Wins + Strategic)
