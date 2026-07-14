---
id: EP-006-flow
epica: EP-006
historias_cubiertas: [HU-034, HU-035, HU-036, HU-037]
---

# Flow EP-006 — Modelo Conversación + Consentimiento

Flujo de datos al llegar un mensaje entrante y persistir conversación, mensaje, consentimiento y
enlace a radicado.

```mermaid
flowchart TD
    A[Mensaje entrante del contacto] --> B{Conversacion abierta?}
    %% HU-034 AC-2
    B -- Si --> C[Reutilizar conversacion existente]
    %% HU-034 AC-1
    B -- No --> D[abrir_conversacion: estado=abierta, tipo_solicitud=NULL]
    C --> E[guardar_mensaje con conversacion_id]
    D --> E
    %% HU-035 AC-1
    E --> F[Mensaje persistido ligado a la conversacion]
    %% HU-036 AC-1
    F --> G{Consentimiento del contacto?}
    %% HU-036 AC-2
    G -- Registrar aceptacion --> H[consentimiento=True, consentimiento_en=now]
    %% HU-036 AC-3
    G -- Registrar rechazo --> I[consentimiento=False, consentimiento_en=now]
    %% HU-037 AC-2
    H --> J[ligar_radicado cuando exista caso]
    %% HU-037 AC-1
    J --> K[radicado_id NULL hasta clasificar/escalar]
    %% HU-034 AC-3
    C --> L[cerrar_conversacion motivo=usuario/inactividad]
    %% HU-034 AC-4
    L -- motivo invalido --> M[ValueError, conversacion sigue abierta]
    %% HU-035 AC-3
    F -- mensaje antiguo --> N[conversacion_id NULL, no falla]
    %% HU-037 AC-3
    J -- radicado inexistente --> O[rechazo por integridad referencial]
```

## Cobertura

- **Camino feliz:** apertura de conversación → mensaje ligado → consentimiento → enlace a radicado.
- **Ramal de error:** motivo de cierre inválido (HU-034 AC-4); radicado inexistente (HU-037 AC-3).
- **Edge:** mensaje antiguo sin `conversacion_id` (HU-035 AC-3).
