# Design: Botones Interactivos WhatsApp (EP-007)

## Architectural Impact

1. **`agent/providers/base.py`**
   ```python
   class ProveedorMensajeria(ABC):
       @abstractmethod
       async def enviar_mensaje(self, telefono: str, mensaje: str, botones: list[dict] = None) -> bool:
           pass
   ```
   Agregamos `botones: list[dict] = None` al método abstracto `enviar_mensaje`. Cada botón tendrá la forma `{"id": "...", "title": "..."}`.

2. **`agent/providers/meta.py`**
   ```python
   async def enviar_mensaje(self, telefono: str, mensaje: str, botones: list[dict] = None) -> bool:
       # ...
       if botones:
           if len(botones) > 3:
               raise ValueError("Meta API only supports up to 3 buttons")
           
           meta_buttons = [
               {
                   "type": "reply",
                   "reply": {
                       "id": b["id"],
                       "title": b["title"]
                   }
               } for b in botones
           ]
           
           payload = {
               "messaging_product": "whatsapp",
               "to": telefono,
               "type": "interactive",
               "interactive": {
                   "type": "button",
                   "body": {
                       "text": mensaje
                   },
                   "action": {
                       "buttons": meta_buttons
                   }
               }
           }
       else:
           # texto normal
   ```

   Para recibir (`parsear_webhook`):
   ```python
   # ...
   msg_obj = value["messages"][0]
   if msg_obj["type"] == "text":
       texto = msg_obj["text"]["body"]
   elif msg_obj["type"] == "interactive" and msg_obj["interactive"]["type"] == "button_reply":
       texto = msg_obj["interactive"]["button_reply"]["id"]  # O title, dependiendo de la logica
   else:
       return None # tipo no soportado
   ```

3. **`agent/main.py`**
   Implementar `enviar_botones_seguro(telefono: str, mensaje: str, botones: list[dict]) -> bool`.

## Testing Strategy
- Unit tests en `test_meta.py` para asegurar que `enviar_mensaje` construye correctamente el JSON para texto y para botones.
- Unit tests en `test_meta.py` para asegurar que `parsear_webhook` parsea exitosamente un webhook payload con `interactive` `button_reply`.
