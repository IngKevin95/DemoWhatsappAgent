# Visión y Roadmap — Plataforma Inteligente de Atención Omnicanal

**Versión:** 1.0
**Estado:** Vigente — única fuente de fases del proyecto

---

# 1. Qué es esta plataforma

Centro inteligente de atención empresarial basado en agentes de IA, no un chatbot. Múltiples agentes especializados colaboran para atender clientes, ejecutar procesos, consultar sistemas corporativos y asistir a agentes humanos.

Principio central: **el agente nunca es el centro del sistema**. El centro es el **Caso de Atención (Radicado)**. Todo canal (WhatsApp, correo, Teams, chat web) debe poder continuar un mismo radicado sin perder contexto.

---

# 2. Problema que resuelve

Hoy los canales de atención (WhatsApp, correo, chat web, Teams, redes, soporte telefónico) operan de forma aislada: información dispersa, conversaciones duplicadas, pérdida de contexto, SLA no medibles, conocimiento interno (manuales, wikis, CRM, ERP) desconectado del punto de atención.

---

# 3. Roadmap — 4 fases (fuente única, no se redefine en otro documento)

| Fase | Nombre | Alcance | Estado |
|---|---|---|---|
| **Fase 1** | Demo | Un agente Gemini con tools síncronas, WhatsApp Cloud API, Postgres simple, sin RAG, sin multiagente | Construido |
| **Fase 2** | MVP sin RAG | Modelo de datos orientado a Radicados (doc 02), Agent Core más robusto, integraciones reales (CRM, agenda), observabilidad básica, seguridad "lo mejor posible" para MVP, despliegue docker-compose. Deja las bases para RAG, no lo implementa. | Próximo (código, sesión futura) |
| **Fase 3** | RAG | Pipeline de vectorización sobre pgvector, memoria de contexto en niveles (corto/mediano/largo plazo) | Futuro |
| **Fase 4** | Multiagente | Orquestación Supervisor + agentes especialistas, arquitectura enterprise (multi-tenant, RBAC/ABAC, Kubernetes, Tool Broker con adapters) | Futuro |

Cada fase construye sobre la anterior: el modelo de datos de Fase 2 es prerrequisito de Fase 3 (RAG necesita `knowledge_sources`/`embeddings` sobre el mismo esquema de radicados); Fase 4 reutiliza el mismo Agent Core de Fase 2/3 y le agrega un Supervisor + router.

La documentación de cada fase vive en su propia carpeta: `fase-1-demo/`, `fase-2-mvp/`, `fase-3-rag/`, `fase-4-multiagente/`. Cada archivo abre con "**Construye sobre:** fase N-1 / doc X" y describe solo el incremento.

---

# 4. Concepto de dominio transversal a todas las fases

```
Cliente
  └─ Radicado          (agregado raíz — el "caso")
       ├─ Conversación
       │    └─ Mensaje
       ├─ Evento         (auditoría de cambios de estado)
       ├─ Tool Call       (registro de herramientas ejecutadas)
       └─ Agent Execution (registro de llamadas al modelo: tokens/costo)
```

Ya vigente en Fase 1 (parcialmente) y objetivo pleno de Fase 2.

---

# 5. Principios de diseño (válidos en todas las fases)

- Omnicanalidad: el agente nunca sabe desde qué canal llegó la solicitud.
- Independencia del modelo de IA (hoy Gemini, mañana cualquiera).
- Independencia de integraciones: el agente solo conoce Tools, nunca URLs/SQL/credenciales.
- Arquitectura basada en casos, no en mensajes ni teléfonos.

---

# 6. Fuera de alcance de este documento

Contenido histórico/aspiracional de más largo plazo (SaaS multi-tenant, marketplace de agentes, voz, multimodal) vive en `fase-4-multiagente/12-Arquitectura-Enterprise.md` como visión a futuro — no es una quinta fase formal.
