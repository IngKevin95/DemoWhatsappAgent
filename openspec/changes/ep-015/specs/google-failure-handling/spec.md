# Manejo generalizado de fallos de Google

## ADDED Requirements

### Requirement: Todo fallo de Google en tools de Calendar queda logueado y escala
The system SHALL capturar cualquier `Exception` lanzada por las APIs de Google dentro de
`consultar_disponibilidad_agenda` y `agendar_cita`, registrarla con `logger.exception` y ejecutar
el flujo de manejo de fallo (log + escalamiento a humano + alerta a infra), sin importar si el
error corresponde a cuota excedida u otro motivo (token expirado/revocado, permiso denegado, etc.).

#### Scenario: RefreshError al consultar disponibilidad
- **Given** que el token de Google está expirado o revocado (`RefreshError: invalid_grant`)
- **When** el bot ejecuta `consultar_disponibilidad_agenda` durante un intento de agendamiento
- **Then** el error se registra con `logger.exception` incluyendo tipo de error y área afectada
- **And** se dispara el escalamiento a humano para el contacto de la conversación activa
- **And** el resultado devuelto indica estado de error de servicio, no una lista vacía de horarios

#### Scenario: Fallo genérico de Google al crear evento
- **Given** que la API de Calendar devuelve un error que NO es de cuota (permiso denegado o token
  inválido)
- **When** el bot ejecuta `agendar_cita`
- **Then** el error se registra con `logger.exception`
- **And** el flujo de manejo de fallo (log + escalamiento + alerta a infra) se ejecuta igual que
  para un error de cuota

#### Scenario: Error de cuota mantiene el comportamiento actual sin duplicar
- **Given** que la API de Google devuelve un error de cuota excedida
- **When** el bot ejecuta cualquier tool que use Calendar
- **Then** se mantiene el comportamiento actual (alerta a infra por correo y escalamiento)
- **And** no se duplica la notificación por haber generalizado el manejo

#### Scenario: Operación normal sin fallos
- **Given** que las credenciales de Google son válidas
- **When** el bot consulta disponibilidad o agenda una cita
- **Then** no se registra ningún error
- **And** no se dispara escalamiento por fallo técnico
