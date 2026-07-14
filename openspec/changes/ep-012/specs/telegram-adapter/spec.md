# Adaptador Telegram

## ADDED Requirements

### Requirement: Adaptador de Telegram en providers
The system SHALL proveer un módulo `agent/providers/telegram.py` que implemente la interfaz para enviar y recibir mensajes usando la API del Bot de Telegram.

#### Scenario: Parseo y envío en Telegram
- **Given** un webhook entrante desde Telegram
- **When** el proveedor lo parsea
- **Then** retorna un objeto `MensajeEntrante`
- **And** al llamar a `enviar_mensaje`, the system SHALL comunicarse con `api.telegram.org`.
