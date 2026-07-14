---
id: EP-010-flow
epica: EP-010
historias_cubiertas: [HU-046, HU-047]
---

# Flow EP-010 — Cierre explícito de conversación

```mermaid
flowchart TD
    A[Conversacion abierta] --> B{Evento}
    %% HU-046 AC-1
    B -- Usuario: no necesito nada mas --> C[Enviar MENSAJE_CIERRE]
    C --> D[cerrar_conversacion motivo=usuario + limpiar historial]
    %% HU-046 AC-2
    B -- Mensaje es consulta --> E[Atencion normal]
    %% HU-046 AC-3
    B -- Despedida ambigua --> F[Preguntar si desea algo mas]
    %% HU-047 AC-1
    B -- Inactividad: ultimo=usuario --> G[Enviar MENSAJE_CHECKIN_1]
    %% HU-047 AC-2
    G -- sigue en silencio --> H[Enviar MENSAJE_CHECKIN_2]
    %% HU-047 AC-3
    H -- sigue en silencio --> I[MENSAJE_CIERRE + cerrar motivo=inactividad]
    %% HU-047 AC-4
    G -- usuario responde --> E
    H -- usuario responde --> E
```

## Cobertura

- **Camino feliz:** cierre por indicación del usuario con despedida (HU-046 AC-1).
- **Ramal de error/alternativo:** no cerrar en medio de una consulta (HU-046 AC-2); despedida ambigua
  pregunta antes de cerrar (HU-046 AC-3).
- **Edge:** usuario responde entre check-ins → reinicia ciclo (HU-047 AC-4).
