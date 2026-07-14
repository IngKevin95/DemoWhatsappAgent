# Design: Cierre Explícito de Conversación (EP-010)

## Architectural Impact

1. **`agent/db.py`:**
   - Modificar `Conversacion` añadiendo: `motivo_cierre = Column(String, nullable=True)`

2. **`agent/tools.py`:**
   - Añadir una nueva tool `finalizar_conversacion(telefono: str, motivo_cierre: str = "usuario") -> dict:` (marcada con el flag para el LLM o manejada como tal) que ejecute:
     ```python
     with SyncSession() as session:
         conv = session.query(Conversacion).filter_by(telefono=telefono, estado="abierta").order_by(Conversacion.id.desc()).first()
         if conv:
             conv.estado = "cerrada"
             conv.motivo_cierre = motivo_cierre
             session.commit()
     # También invocar async limpiar_historial(telefono) si corresponde.
     ```
   - Registrar la tool en Gemini.

3. **`agent/main.py`:**
   - En `_revisar_inactividad()`, implementar los 2 check-ins. Se usarán mensajes fijos (ej. `MENSAJE_CHECKIN_1` y `MENSAJE_CHECKIN_2`) y se comparará el contenido del último mensaje del assistant.
   - Cuando finalmente toque cerrar por inactividad, en lugar de solo llamar a `limpiar_historial`, se invoca una función helper (o un bloque BD) que marque `estado="cerrada"` y `motivo_cierre="inactividad"`.

## Testing Strategy
- **DB Test:** Validar inserción de `motivo_cierre`.
- **Tool Test:** Validar que `finalizar_conversacion` cierre la conversación activa.
- **Async Daemon Test:** (Opcional si es complejo mockear `asyncio.sleep`) Extraer la lógica de inactividad a una función puramente lógica testeable (ej. `_evaluar_inactividad`) para asegurar los estados intermedios.
