# Spec: Cierre Explícito de Conversación (EP-010)

## Feature Description
Cerrar explícitamente la conversación a través del LLM cuando el usuario lo solicite, o automáticamente tras 2 avisos de inactividad, registrando el estado final y el motivo del cierre en la BD.

## Requirements

1. **Columna motivo_cierre:** Agregar `motivo_cierre` a la tabla `Conversacion` en `agent/db.py`.
2. **Tool de Cierre para el LLM:** Exponer una herramienta `finalizar_conversacion()` a Gemini. Al invocarla, marcará la `Conversacion` activa de ese teléfono como `estado="cerrada"` y `motivo_cierre="usuario"`.
3. **Flujo de Inactividad (2 Check-ins):**
   - El daemon `_revisar_inactividad` debe enviar un primer check-in (ej. "Hola, sigues ahí?") tras `CHECKIN_INACTIVIDAD_SEGUNDOS`.
   - Tras otros `CHECKIN_INACTIVIDAD_SEGUNDOS` sin respuesta, debe enviar un segundo check-in.
   - Tras los `CIERRE_INACTIVIDAD_SEGUNDOS` finales, debe enviar el mensaje de cierre definitivo, limpiar el historial, y además marcar la `Conversacion` activa como `estado="cerrada"` y `motivo_cierre="inactividad"`.

## Deltas

### ADDED Requirements

#### Cierre manual por voluntad del usuario
- **Scenario: Usuario se despide**
  - **Given** que el usuario envía un mensaje como "Gracias, eso era todo".
  - **When** Gemini detecta la intención y llama a la tool `finalizar_conversacion`.
  - **Then** el sistema marca `estado="cerrada"` y `motivo_cierre="usuario"` en la base de datos.
  - **And** el bot puede enviar un mensaje de despedida.

#### Cierre por inactividad prolongada (2 check-ins)
- **Scenario: Usuario ignora dos check-ins consecutivos**
  - **Given** que el usuario deja de responder en medio de una charla.
  - **When** pasa el tiempo del primer check-in, el bot envía "Hola, sigues ahí?".
  - **And** al pasar el tiempo del segundo check-in, envía "Si no respondes, cerraremos el caso".
  - **And** al vencerse el timeout final se ejecuta el cierre por inactividad.
  - **Then** el sistema limpia el historial en RAM y en BD marca `estado="cerrada"` y `motivo_cierre="inactividad"`.
