# Enrutamiento Multi-canal

## MODIFIED Requirements

### Requirement: Soportar múltiples webhooks y proveedores en main.py
The system SHALL poseer endpoints separados en `main.py` para `/webhook/meta` y `/webhook/telegram`, y orquestar el flujo inyectando la instancia correspondiente del proveedor.

#### Scenario: Enrutamiento al proveedor correcto
- **Given** un mensaje de Telegram y uno de WhatsApp
- **When** llegan a sus respectivos webhooks
- **Then** the system SHALL utilizar `ProveedorTelegram` para el primero y `ProveedorMeta` para el segundo.
