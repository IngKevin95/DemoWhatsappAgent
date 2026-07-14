# Spec: Gate de Consentimiento Habeas Data (EP-008)

## Feature Description
Insertar en la ruta del webhook, antes del LLM, el saludo + solicitud de aceptación de tratamiento de datos con botones Sí/No. Sin consentimiento no se atiende.

## Requirements

1. **Gate de Consentimiento:**
   - Cuando un mensaje entra a `recibir_webhook` (`agent/main.py`), se verifica si el contacto tiene `consentimiento_datos = True`.
   - Si no lo tiene:
     - Si el mensaje entrante es `"SI"`, se marca el consentimiento como verdadero, se le saluda y se abre la conversación.
     - Si el mensaje entrante es `"NO"`, se le despide indicando que no se pueden procesar sus datos y NO se abre la conversación.
     - Si es cualquier otra cosa (su primer mensaje natural), se le retiene enviando un mensaje de Habeas Data junto con dos botones: `"Sí, acepto"` (id: `SI`) y `"No, gracias"` (id: `NO`).
   - Una vez otorgado el consentimiento, los siguientes mensajes pasarán al LLM para su procesamiento normal.

## Deltas

### MODIFIED Requirements

#### Modificar Flujo de Habeas Data en Webhook
- **Scenario: Contacto no ha dado su consentimiento**
  - **Given** que un contacto nuevo envía su primer mensaje (ej: "Hola").
  - **When** se procesa en `recibir_webhook` y no hay consentimiento registrado.
  - **Then** el bot debe detener la ejecución normal hacia el LLM.
  - **And** debe enviarle el mensaje de políticas con los botones interactivos (Sí/No).
- **Scenario: Contacto acepta el consentimiento**
  - **Given** que un contacto sin consentimiento previo presiona el botón "Sí, acepto" (texto entrante "SI").
  - **When** se procesa en `recibir_webhook`.
  - **Then** la BD actualiza `consentimiento_datos = True`.
  - **And** el bot responde "Gracias. Hemos registrado tu consentimiento. ¿En qué te puedo ayudar?".
  - **And** se inicia una conversación nueva.
- **Scenario: Contacto rechaza el consentimiento**
  - **Given** que un contacto sin consentimiento previo presiona el botón "No, gracias" (texto entrante "NO").
  - **When** se procesa en `recibir_webhook`.
  - **Then** la BD mantiene `consentimiento_datos = False`.
  - **And** el bot responde "Entendemos. No podemos procesar tus datos sin tu consentimiento. Hasta pronto.".
