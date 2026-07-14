# Design: Gate de Consentimiento Habeas Data (EP-008)

## Architectural Impact

1. **`agent/main.py`**
   ```python
    if not consentimiento_dado:
        texto_upper = mensaje.texto.strip().upper()
        if texto_upper == "SI":
            with SyncSession() as session:
                contacto = session.query(Contacto).filter(Contacto.telefono == mensaje.telefono).first()
                contacto.consentimiento_datos = True
                session.commit()
            await enviar_mensaje_seguro(mensaje.telefono, "Gracias. Hemos registrado tu consentimiento. ¿En qué te puedo ayudar?")
            await abrir_conversacion(mensaje.telefono)
            return {"status": "ok"}
        elif texto_upper == "NO":
            await enviar_mensaje_seguro(mensaje.telefono, "Entendemos. No podemos procesar tus datos sin tu consentimiento. Hasta pronto.")
            return {"status": "ok"}
        else:
            botones = [
                {"id": "SI", "title": "Sí, acepto"},
                {"id": "NO", "title": "No, gracias"}
            ]
            await enviar_mensaje_seguro(
                mensaje.telefono, 
                "Por políticas de privacidad (Habeas Data), necesitamos tu consentimiento para procesar tus datos. Por favor elige una opción.", 
                botones=botones
            )
            return {"status": "ok"}
   ```

2. Todo lo demás se apoya en los cimientos de la EP-006 (persistencia) y EP-007 (botones subyacentes).

## Testing Strategy
- Utilizar `pytest tests/unit/test_main.py` (o donde se esté probando el webhook) para asegurarse de que si el usuario es nuevo, el bot le mande la respuesta con los botones.
- **Mock de envío:** Asegurar que `proveedor.enviar_mensaje` se llame con el argumento `botones`.
