# Unit Tests: memory.py

## Descripción

Tests de persistencia para la capa de memoria: obtener_historial, guardar_contexto, limpiar_sesion.

## Requisitos

### R1: obtener_historial retorna mensajes previos
**Given** mock Postgres contiene 3 mensajes de usuario 123 en historial  
**When** se llama `obtener_historial(telefono="123")`  
**Then** retorna lista de 3 dicts con {timestamp, rol, texto}

### R2: guardar_contexto persiste en BD
**Given** mock Postgres mock pool  
**When** se llama `guardar_contexto(telefono="456", intent="PRECIO", payload={...})`  
**Then** INSERT ejecutado, retorna context_id generado

### R3: limpiar_sesion archiva en lugar de borrar
**Given** sesión activa con 10 mensajes  
**When** se llama `limpiar_sesion(telefono="789")`  
**Then** status cambia a "archived", mensajes no se borran (GDPR compliance)

### R4: Connection pool resilience
**Given** mock Postgres.get_connection() falla 1 vez  
**When** se llama obtener_historial (con retry)  
**Then** reintenta y éxito en segundo intento

## Artefactos

- `tests/unit/test_memory.py` (nuevo)
- Mock Postgres extendido en conftest.py

## Criterios de Aceptación

- ≥10 test cases en test_memory.py
- Todos pasan: `pytest tests/unit/test_memory.py -v`
- Coverage de obtener_historial, guardar_contexto ≥85%
- GDPR compliance verificado: DELETE nunca se llama directo
