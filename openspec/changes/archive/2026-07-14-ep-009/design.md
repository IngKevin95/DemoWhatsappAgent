# Design: Clasificación de Flujo + Alta CRM (EP-009)

## Architectural Impact

1. **`agent/main.py`**
   - Importar `EspoCRM` en `main.py` (o usar la instancia existente) e invocar `crear_lead` silenciosamente en la rama donde `texto_upper == "SI"`.
   - Después de obtener el `conversacion_id`, buscar la instancia de `Conversacion` y si su `tipo_solicitud` es NULL, invocar `clasificar_intencion(mensaje.texto)` y actualizar el registro.

2. **`agent/brain.py`**
   - Actualizar `clasificar_intencion(texto: str)`:
     ```python
     async def clasificar_intencion(texto: str) -> str:
         # Usar el modelo de google-genai para devolver "comercial", "soporte", o "otro"
         # prompt: "Clasifica el siguiente mensaje en una sola palabra ('comercial', 'soporte' u 'otro'): {texto}"
     ```
   - Nota: como es asíncrono, hay que cambiarlo en donde se use.

3. **`agent/tools.py`**
   - En `escalar_a_humano`:
     ```python
     with SyncSession() as session:
         conv = session.query(Conversacion).filter(
             Conversacion.telefono == telefono, 
             Conversacion.estado == "abierta"
         ).order_by(Conversacion.id.desc()).first()
         
         if conv and conv.radicado_id:
             radicado = session.query(Radicado).get(conv.radicado_id)
             # Reusar radicado
             radicado_id = radicado.id
         else:
             # Crear radicado normal
             radicado = Radicado(...)
             session.add(radicado)
             session.commit()
             session.refresh(radicado)
             radicado_id = radicado.id
             
             if conv:
                 conv.radicado_id = radicado_id
                 session.commit()
     ```

## Testing Strategy
- Mocks para `EspoCRM.crear_lead`.
- Test unitario de `clasificar_intencion` usando mock de Gemini.
- Test E2E/Integration de `escalar_a_humano` asegurando que no se duplican radicados en la misma conversación activa.
