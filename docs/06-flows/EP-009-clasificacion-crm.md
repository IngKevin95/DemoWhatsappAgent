---
id: EP-009-flow
epica: EP-009
historias_cubiertas: [HU-043, HU-044, HU-045]
---

# Flow EP-009 — Clasificación de flujo + alta CRM

```mermaid
flowchart TD
    A[Consentimiento aceptado] --> B[Alta contacto en CRM con telefono origen]
    %% HU-044 AC-2
    B -- ya existe --> C[No duplicar en CRM]
    %% HU-044 AC-3
    B -- CRM caido --> D[log + continuar, reintentar luego]
    B --> E{Clasificar tipo_solicitud}
    %% HU-043 AC-1
    E -- senales comerciales --> F[tipo_solicitud=comercial]
    %% HU-043 AC-2
    E -- senales soporte --> G[tipo_solicitud=soporte]
    %% HU-043 AC-3
    E -- ninguna --> H[tipo_solicitud=otro]
    %% HU-045 AC-1
    G --> I[Crear radicado y ligar a la conversacion]
    F --> I
    %% HU-045 AC-2
    I --> J{Escalar en el mismo hilo?}
    J -- Si, ya hay radicado --> K[Reutilizar radicado existente]
    %% HU-043 AC-4
    F -- usuario pide soporte luego --> G
    %% HU-045 AC-3
    G -- sin_licencia --> L[Reclasificar sobre el mismo radicado]
```

## Cobertura

- **Camino feliz:** aceptar → alta CRM → clasificar → radicado ligado.
- **Ramal de error:** CRM caído → continuar con degradación (HU-044 AC-3).
- **Edge:** reclasificación de tema (HU-043 AC-4); reclasificar sin licencia sobre el mismo radicado
  (HU-045 AC-3).
