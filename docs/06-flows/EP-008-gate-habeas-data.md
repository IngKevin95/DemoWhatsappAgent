---
id: EP-008-flow
epica: EP-008
historias_cubiertas: [HU-040, HU-041, HU-042]
---

# Flow EP-008 — Gate de consentimiento habeas data

```mermaid
flowchart TD
    A[Mensaje entrante] --> B{Estado consentimiento?}
    %% HU-041 AC-2
    B -- True --> C[Flujo normal: generar_respuesta]
    %% HU-040 AC-1
    B -- NULL, primer contacto --> D[Abrir conversacion + guardar mensaje]
    %% HU-040 AC-2
    D --> E[Enviar botones con texto_habeas_data]
    %% HU-040 AC-4
    E -- parametro ausente --> F[Texto por defecto + log]
    %% HU-040 AC-3
    B -- NULL, ya preguntado sin responder --> G[Reofrecer gate una vez]
    %% HU-042 AC-2
    B -- False --> H[Reofrecer gate]
    E --> I{Respuesta del usuario}
    %% HU-041 AC-1
    I -- habeas_si --> J[registrar_consentimiento True + agradecer]
    J --> C
    %% HU-042 AC-1
    I -- habeas_no --> K[registrar_consentimiento False + despedir]
    K --> L[cerrar_conversacion motivo=usuario]
    %% HU-041 AC-3
    I -- texto 'si acepto' --> J
    %% HU-042 AC-3
    I -- texto 'no acepto' --> K
```

## Cobertura

- **Camino feliz:** contacto nuevo → gate → acepta → flujo normal.
- **Ramal de error:** parámetro `texto_habeas_data` ausente → texto por defecto (HU-040 AC-4).
- **Edge:** aceptación/rechazo por texto libre (HU-041 AC-3, HU-042 AC-3); re-solicitud si pendiente.
