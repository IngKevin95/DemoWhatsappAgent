# Unit Tests: brain.py

## Descripción

Tests unitarios para la lógica del bot conversacional: generar_respuesta (bridge node crítico), clasificar_intencion, guardrails_check.

## Requisitos

### R1: generar_respuesta happy path
**Given** Gemini responde en <100ms (mock)  
**When** se llama `await generar_respuesta(mensaje="...", telefono="...", historial=[], herramientas=[])`  
**Then** retorna string no-vacío, longitud >0

### R2: generar_respuesta timeout fallback
**Given** Gemini timeout_segundos=0.001 (fuerza timeout inmediato)  
**When** se llama generar_respuesta con timeout muy corto  
**Then** retorna fallback "Tengo limitaciones temporales, pero sigo aquí" (no error)

### R3: clasificar_intencion mapeo de intents
**Given** mensaje es "¿Cuánto cuesta el módulo Pro?"  
**When** se llama `clasificar_intencion(mensaje)`  
**Then** retorna intent="PRECIO" con confidence ≥0.7

### R4: guardrails_check bloquea SQL injection
**Given** mensaje contiene "'; DROP TABLE--"  
**When** se llama `guardrails_check(mensaje)`  
**Then** retorna blocked=True, reason incluye "SQL"

## Artefactos

- `tests/unit/test_brain.py` (ya existe, extensiones):
  - TestGenerarRespuesta (happy path, timeout, error cases)
  - TestClasificarIntencion (all intents covered)
  - TestGuardrailsCheck (SQL, XSS, script injection)

## Criterios de Aceptación

- ≥15 test cases en test_brain.py
- Todos pasan: `pytest tests/unit/test_brain.py -v`
- Coverage de generar_respuesta, clasificar_intencion ≥95%
- Mock Gemini siempre <100ms
