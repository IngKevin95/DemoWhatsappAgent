# Unit Tests: tools.py

## Descripción

Tests de integración mock para los tools críticos: escalar_a_humano, agendar_cita, consultar_precio_modulo.

## Requisitos

### R1: escalar_a_humano crea case en EspoCRM
**Given** mock EspoCRM está configurado, usuario con sin_licencia=true  
**When** se llama `await escalar_a_humano(usuario, razon="Soporte técnico")`  
**Then** mock_espocrm.create_case fue llamado con descripción que incluye razon, retorna ticket_id

### R2: agendar_cita crea evento en Google Calendar
**Given** mock Google Calendar, slot disponible "martes 14:00"  
**When** se llama `await agendar_cita(usuario, slot, producto)`  
**Then** mock_google_calendar.events.insert fue llamado, retorna event_id y confirmación email

### R3: consultar_precio_modulo devuelve precio actualizado
**Given** BD mock tiene módulo Pro: $99/mes  
**When** se llama `consultar_precio_modulo("Pro")`  
**Then** retorna {"nombre": "Pro", "precio": 99, "moneda": "USD"}

### R4: retry logic en tools con exponential backoff
**Given** mock_espocrm falla 2 veces, éxito al reintento 3  
**When** se llama escalar_a_humano (retry decorator activo)  
**Then** reintenta con backoff 1s→2s→4s, finalmente éxito

## Artefactos

- `tests/unit/test_tools.py` (nuevo)
- Mocks extendidos en conftest.py: mock_espocrm, mock_google_calendar con retry simulation

## Criterios de Aceptación

- ≥12 test cases en test_tools.py
- Todos pasan: `pytest tests/unit/test_tools.py -v`
- Coverage de escalar_a_humano, agendar_cita ≥90%
- Retry logic verificado (3 intentos = 1 éxito)
