---
id: EP-007-flow
epica: EP-007
historias_cubiertas: [HU-038, HU-039]
---

# Flow EP-007 — Botones interactivos WhatsApp

```mermaid
flowchart TD
    A[Bot necesita decision binaria] --> B[enviar_botones telefono, texto, botones]
    %% HU-038 AC-1
    B --> C{Cantidad de botones <= 3?}
    %% HU-038 AC-3
    C -- No --> D[ValueError: max 3 reply buttons]
    %% HU-038 AC-1
    C -- Si --> E[POST Meta type=interactive, action.buttons]
    %% HU-038 AC-4
    E -- Error HTTP --> F[log/propaga error, caller no rompe]
    %% HU-038 AC-2
    E -- OK --> G[Usuario ve botones Si acepto / No]
    G --> H[Usuario toca un boton]
    %% HU-039 AC-1
    H --> I[parsear_webhook detecta type=interactive]
    I --> J[MensajeEntrante tipo=boton, payload=button_reply.id]
    %% HU-039 AC-2
    G2[Usuario escribe texto libre] --> K[parsear_webhook type=text]
    K --> L[MensajeEntrante tipo=text]
    %% HU-039 AC-3
    H -- tipo no soportado --> M[parsear_webhook devuelve None]
```

## Cobertura

- **Camino feliz:** enviar botones válidos → usuario toca → parseo devuelve `payload`.
- **Ramal de error:** >3 botones (HU-038 AC-3); error HTTP del provider (HU-038 AC-4).
- **Edge:** tipo de mensaje no soportado devuelve None (HU-039 AC-3).
