# Coverage Enforcement

## Descripción

Configuración de pytest-cov para medir y garantizar cobertura ≥60% en agent/.

## Requisitos

### R1: pytest-cov instalado y configurado
**Given** pytest-cov está en requirements.txt  
**When** se ejecuta `pip install -r requirements.txt`  
**Then** pytest-cov disponible, `pytest --cov` funciona

### R2: Coverage report generado en HTML
**Given** pytest corre con --cov-report=html  
**When** completado  
**Then** se genera htmlcov/index.html con coverage detallado por archivo

### R3: Threshold ≥60% en pytest.ini
**Given** pytest.ini contiene `addopts = --cov-fail-under=60`  
**When** coverage < 60%  
**Then** pytest falla, muestra resumen de líneas no cubiertas

### R4: Coverage badge en README
**Given** codecov/codecov-action subió reporte  
**When** se visualiza README.md  
**Then** badge muestra coverage % actual (ej. ![Coverage 65%](codecov.io/...))

## Artefactos

- pytest.ini actualizado con --cov-fail-under=60
- `.codecov.yml` (opcional, para configuración avanzada)
- README.md badge

## Criterios de Aceptación

- `pytest --cov=agent` muestra coverage por módulo
- Coverage agent/ ≥60%
- `pytest --cov-fail-under=60` falla si coverage < umbral
- CI workflow publica coverage report
- Badge actualizado en README
