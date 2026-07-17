# Notificaciones WhatsApp a líderes

## ADDED Requirements

### Requirement: WhatsApp al líder de infraestructura ante fallo técnico de Google
The system SHALL enviar un WhatsApp al número configurado en el parámetro `whatsapp_lider_infra`
cada vez que se maneja un fallo técnico de Google/Calendar, además del correo a infra ya existente.
Si el parámetro no existe o está vacío, no se intenta el envío pero el resto del manejo del fallo
continúa sin bloquearse.

#### Scenario: Fallo técnico con líder infra configurado
- **Given** que existe el parámetro `whatsapp_lider_infra` con un número válido
- **When** el bot maneja un fallo técnico de Google/Calendar
- **Then** se envía un WhatsApp a ese número con el detalle del error, el área afectada y el
  contacto involucrado
- **And** el envío se hace además del correo a infra que ya existe

#### Scenario: Parámetro no configurado
- **Given** que el parámetro `whatsapp_lider_infra` no existe o está vacío
- **When** el bot maneja un fallo técnico de Google/Calendar
- **Then** no se intenta enviar WhatsApp a infra
- **And** el resto del manejo (log, correo, escalamiento) se ejecuta normalmente
- **And** se registra en log que no había número de infra configurado

#### Scenario: Fallo en el envío del WhatsApp de alerta a infra
- **Given** que el parámetro `whatsapp_lider_infra` está configurado
- **When** el envío del WhatsApp a infra falla (error de red o de la API de Meta)
- **Then** el error se captura y se registra con `logger.error`
- **And** no interrumpe el flujo de escalamiento ni el manejo del fallo original

### Requirement: WhatsApp al líder comercial cuando un caso entra en cola
The system SHALL enviar un WhatsApp al número configurado en el parámetro `whatsapp_lider_<area>`
únicamente cuando `escalar_a_humano` deja un caso en cola (todos los agentes del área ocupados),
con el código de caso, nombre del cliente y posición en cola. No se notifica cuando el caso se
asigna directamente a un agente libre.

#### Scenario: Caso encolado con líder comercial configurado
- **Given** que existe el parámetro `whatsapp_lider_<area>` (ej. `whatsapp_lider_comercial`) con un
  número válido
- **And** que todos los agentes del área están ocupados
- **When** el bot escala un caso y lo deja en cola
- **Then** se envía un WhatsApp al líder comercial del área con el código de caso, el nombre del
  cliente y la posición en cola

#### Scenario: Caso escalado pero atendido de inmediato
- **Given** que hay al menos un agente libre en el área
- **When** el bot escala un caso y lo asigna directamente a un agente
- **Then** NO se notifica al líder comercial

#### Scenario: Parámetro de líder de área no configurado
- **Given** que no existe `whatsapp_lider_<area>` para el área del caso
- **When** un caso entra en cola
- **Then** no se intenta enviar WhatsApp al líder
- **And** el resto del flujo de encolamiento (posición, mensaje al cliente) se ejecuta normalmente

#### Scenario: Fallo en el envío al líder comercial
- **Given** que el parámetro está configurado
- **When** el envío del WhatsApp al líder falla
- **Then** el error se captura y se registra con `logger.error`
- **And** el cliente igual recibe su mensaje de "en cola, posición N"
