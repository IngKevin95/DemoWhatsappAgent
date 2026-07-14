# Tasks: Cierre Explícito de Conversación (EP-010)

- [ ] Añadir `motivo_cierre` a `Conversacion` en `agent/db.py` (migración autogenerada por SQLAlchemy si se recrea en tests o manual, asumiendo base de datos destruible o `alembic` no necesario para este demo).
- [ ] Modificar `_revisar_inactividad` en `agent/main.py` para soportar `MENSAJE_CHECKIN_1`, `MENSAJE_CHECKIN_2` y `MENSAJE_CIERRE`.
- [ ] Añadir la función (tool) `finalizar_conversacion` en `agent/tools.py` y exponerla en Gemini.
- [ ] Asegurarse de que el cierre por inactividad marque `estado="cerrada"` y `motivo_cierre="inactividad"` en la BD.
- [ ] Tests de la tool y el manejador de inactividad.
