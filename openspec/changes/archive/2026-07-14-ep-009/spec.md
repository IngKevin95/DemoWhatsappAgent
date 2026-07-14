# Spec: Clasificación de Flujo + Alta CRM (EP-009)

## Feature Description
Persistir el tipo de flujo (comercial/soporte/otro) en la base de datos, crear leads en el CRM automáticamente al recibir el consentimiento, y reutilizar un único radicado por cada conversación si se realizan escalamientos a humanos.

## Requirements

1. **Alta CRM Automática:**
   - Una vez el contacto presione el botón "Sí, acepto" (texto "SI"), debe enviarse asíncronamente una llamada a EspoCRM para crear un Lead con el número de teléfono del contacto.
   - En caso de fallar, no debe interrumpir el flujo (manejo silencioso de errores o retry asíncrono).

2. **Radicado Único por Conversación:**
   - La tool `escalar_a_humano` en `agent/tools.py` debe buscar la `Conversacion` activa de ese `telefono`.
   - Si la conversación tiene `radicado_id == None`, se crea un Radicado, se inserta en BD, y se actualiza `Conversacion.radicado_id = nuevo_radicado_id`.
   - Si `radicado_id != None`, se obtiene el Radicado existente y no se crea uno nuevo, pero se puede actualizar el resumen.

3. **Clasificación Determinista:**
   - `brain.py::clasificar_intencion` debe utilizar Gemini (vía la misma librería actual o un prompt de sistema) para clasificar el primer mensaje en `comercial`, `soporte` u `otro`.
   - En `agent/main.py`, si la conversación está abierta pero `tipo_solicitud` es NULL, se debe clasificar el mensaje entrante y hacer update a `Conversacion.tipo_solicitud`.

## Deltas

### ADDED Requirements

#### Escalamiento con Radicado Único
- **Scenario: Escalamiento por primera vez en la conversación**
  - **Given** que un contacto tiene una conversación activa sin radicado.
  - **When** Gemini llama a la tool `escalar_a_humano`.
  - **Then** el sistema crea un nuevo Radicado en la BD.
  - **And** asigna el ID de este nuevo radicado a `Conversacion.radicado_id`.

- **Scenario: Escalamiento subsecuente en la misma conversación**
  - **Given** que un contacto tiene una conversación activa con un radicado previamente asignado.
  - **When** Gemini llama a la tool `escalar_a_humano` nuevamente.
  - **Then** el sistema reutiliza el Radicado existente.
  - **And** no crea un radicado nuevo en la BD.

#### Alta Automática CRM
- **Scenario: Usuario acepta Habeas Data**
  - **Given** que el usuario responde "SI" al Habeas Data.
  - **When** se procesa la aceptación en el webhook.
  - **Then** el sistema invoca al CRM para crear un Lead con el número de teléfono como identificador.

#### Clasificación de Conversación
- **Scenario: Primer mensaje útil tras consentimiento**
  - **Given** que un usuario tiene una conversación activa con `tipo_solicitud` nulo.
  - **When** el usuario envía un mensaje de texto.
  - **Then** el sistema clasifica la intención (comercial/soporte/otro).
  - **And** actualiza `Conversacion.tipo_solicitud` con el resultado en la BD.
