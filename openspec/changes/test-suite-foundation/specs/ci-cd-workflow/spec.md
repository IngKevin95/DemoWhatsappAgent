# CI/CD Workflow

## Descripción

GitHub Actions workflow para ejecutar tests automáticamente en cada push y PR.

## Requisitos

### R1: Workflow dispara en push y pull_request
**Given** cambios pusheados a cualquier rama  
**When** se ejecuta `.github/workflows/test.yml`  
**Then** se inicia job "test" en ubuntu-latest

### R2: Instala dependencias y ejecuta pytest
**Given** workflow corriendo  
**When** se ejecutan steps: setup-python, pip install, pytest  
**Then** instala Python 3.11, requirements.txt, corre `pytest --cov=agent --cov-report=xml`

### R3: Publica coverage a codecov
**Given** pytest completó con cobertura ≥60%  
**When** se ejecuta codecov/codecov-action  
**Then** coverage report subido a codecov.io, badge actualizado

### R4: Falla si coverage <60%
**Given** cambios reducen coverage a 58%  
**When** se ejecuta pytest --cov-fail-under=60  
**Then** workflow falla, PR no se puede mergear sin remediación

## Artefactos

- `.github/workflows/test.yml` (nuevo)
- `.codecov.yml` (configuración codecov, opcional)
- README.md badge de coverage

## Criterios de Aceptación

- Workflow existe en `.github/workflows/test.yml`
- Triggers en push + pull_request
- Todos los pasos ejecutan sin error
- Coverage report publicado a codecov
- Build status visible en PR (✓ o ✗)
