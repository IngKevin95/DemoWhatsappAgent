# Capítulo 1 — Estado Actual (Fase 1 Demo)

**Construye sobre:** N/A (fase base — punto de partida del roadmap)

**Estado:** Construido

Detalle técnico completo (stack, docker-compose, seguridad, túnel) vive en
[`ARCHITECTURE.md`](../../../ARCHITECTURE.md) en la raíz del repo — este
documento resume qué hay y qué falta, sin duplicar ese contenido.

---

## 1. Qué está construido

- **Un solo agente Gemini** con function-calling síncrono (`agent/brain.py`,
  `agent/tools.py`) — sin RAG, sin orquestación multiagente.
- **Canal:** WhatsApp Cloud API (Meta) vía `ProveedorWhatsApp` (abstracción
  en `agent/providers/`), expuesto a internet con Cloudflare Quick Tunnel.
- **Modelo de datos orientado a Radicados ya construido** (`agent/db.py`):
  `Area`, `Agente`, `Contacto`, `Cliente` (con tipo lead/cliente y perfil de
  empresa), `Radicado` (agregado raíz — caso de atención, con `estado`,
  `modo`, `crm_case_id`), `ColaEspera`, además de `Modulo`/`Oferta`/
  `Parametro`/`Mensaje`. `escalar_a_humano()` (`agent/tools.py`) ya persiste
  un `Radicado` real en vez de un ID en memoria. Cubre el diagrama de
  dominio transversal del [`00-Vision-Roadmap.md`](../00-Vision-Roadmap.md#4-concepto-de-dominio-transversal-a-todas-las-fases)
  a nivel de esquema — falta madurar Conversación/Evento/Tool Call/Agent
  Execution como entidades propias (hoy `mensajes` es la única tabla de
  ese lado).
- **Persistencia real en Postgres 16.** NocoDB como panel admin sobre la
  misma BD.
- **Integraciones reales:** Google Calendar + Gmail (citas y correos),
  EspoCRM (leads/casos) y Firebird (licencias) en infra de demo separada
  (`docker-compose.demo.yml`).
- **Seguridad mínima ya resuelta:** validación de firma de webhook
  (`X-Hub-Signature-256`).

## 2. Qué es simulado o no persistente

- Citas internas (`_CITAS_DB`) viven en memoria del proceso — se pierden en
  cada restart del contenedor.
- Cuota gratuita de Gemini (20 req/día) — sin billing habilitado.

## 3. Qué falta (gaps conocidos, no bloqueantes para demo)

- Sin rate limiting ni CORS/security headers en el webhook público.
- Postgres con credenciales débiles y puerto expuesto al host.
- Secretos en `.env` plano (no cifrados).
- NocoDB comparte credenciales de Postgres con el bot (no hay usuario
  acotado).
- Token OAuth de Google (`token.json`) persistido en texto plano.
- Túnel Cloudflare Quick Tunnel: sin SLA, URL efímera por arranque —
  migrar a Named Tunnel requiere cuenta Cloudflare (pendiente, decisión del
  usuario).
- Un solo proceso Uvicorn sin supervisión de crashes ni autoscaling.

Estos gaps son exactamente lo que Fase 2 (MVP sin RAG) debe cerrar antes de
producción real — ver
[`00-Vision-Roadmap.md`](../00-Vision-Roadmap.md) y
[`fase-2-mvp/01-Analisis_Modelo.md`](../fase-2-mvp/01-Analisis_Modelo.md).
