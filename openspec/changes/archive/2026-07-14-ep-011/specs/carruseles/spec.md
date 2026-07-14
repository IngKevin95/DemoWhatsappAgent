# Carruseles de Ofertas

## MODIFIED Requirements

### Requirement: Soporte para templates interactivos tipo carrusel en Meta API
The system SHALL extender `enviar_mensaje` o crear una variante en `providers/meta.py` que permita enviar `template` con tipo `carousel`.

#### Scenario: Enviar un carrusel
- **Given** una solicitud para enviar ofertas
- **When** se llama al proveedor con formato de carrusel
- **Then** el proveedor hace un POST a la API de WhatsApp Graph con `type: template` y los componentes de las ofertas.
