# Épicas: DemoWhatsappAgent

**Fuente:** DemoWhatsappAgent-PRD.md  
**Fecha:** 2026-07-14  
**FASE 1 DEMO (v1.0) — UPDATED:**  
- **Épicas v1.0:** EP-001 (14 HU, archivada), EP-002 (1 HU, archivada), EP-003-MINI (4 HU, nueva), EP-005-MINI (5 HU, nueva)
- **Total v1.0:** 24 HU (15 archivadas + 9 nuevas)
- **Eliminadas:** EP-004 (RAG, indefinidamente deferred)
- **Línea de base:** Grafo de dependencias (156 nodos, 5 comunidades, hub nodes identificados)

---

## EP-001: Test Suite Foundation

### Propósito Ejecutivo

Establecer cobertura de tests unitarios + integración en módulos críticos (brain.py, tools.py, memory.py) para que cambios futuros no rompan la arquitectura.

### Por Qué Existe

- **Chokepoint crítico:** `generar_respuesta()` (brain.py) es bridge node central (betweenness 0.000565) — si falla, conversación completa se interrumpe. **Hoy: 0 tests dedicados.**
- **Hub nodes sin cobertura:** `escalar_a_humano()` (degree 32), `agendar_cita()` (degree 23) — cambios aquí impactan 23-32 dependencias. **Hoy: tests E2E básicos, coverage desconocida.**
- **Deuda técnica bloqueadora:** No se puede refactorizar sin romper cosas (sin modo refactor seguro).
- **Blocker de Fase 2:** No se deploya a producción sin test coverage ≥60%.

### Objetivos PRD que Atiende

- ✅ Éxito / KPI: Test coverage ≥60%
- ✅ Confiabilidad general (todos los objetivos dependen de que el código funcione)

### Capabilities Incluidas

- **Nivel 4 (Backend):** Validación interna, testing framework, stubs para integraciones externas
- **Seguridad Mínima v1.0:**
  - `main.py::recibir_webhook()`: Rate limiting básico (10 req/min por IP)
  - `main.py` + `brain.py`: Input sanitization (remover scripts, SQL injections)
  - No exponemos secretos en logs (scrubbing de DATABASE_URL, GOOGLE_*, META_*)
- **Especialmente:**
  - `brain.py::generar_respuesta()` — tests unitarios (mock Gemini)
  - `tools.py::escalar_a_humano()` — tests de integración (mock EspoCRM + Gmail)
  - `tools.py::agendar_cita()` — tests de integración (mock Google Calendar)
  - `memory.py::obtener_historial()` — tests de persistencia (mock Postgres)
  - `main.py::recibir_webhook()` — tests de validación de firma Meta (HMAC) + rate limiting

### Cómo se Mide Éxito

| Métrica | Target | Método |
|---------|--------|--------|
| Test coverage (líneas) | ≥60% | `pytest --cov` |
| Tests ejecutados | ≥50 test cases | `pytest -v` |
| CI/CD verde | 100% | GitHub Actions |
| Hub nodes covered | ≥4 de 4 (escalar, agendar, etc.) | Test coverage report |
| Bridge nodes covered | 100% (generar_respuesta) | Test coverage report + E2E |

### Artefactos Esperados

- `tests/unit/test_brain.py` (mock Gemini, verificar telefono wrapping)
- `tests/integration/test_tools_*.py` (mocks de servicios externos)
- `tests/e2e/test_webhook_scenarios.py` (flujos end-to-end)
- `tests/conftest.py` (fixtures comunes)
- GitHub Actions workflow (`.github/workflows/test.yml`)
- Coverage report (CI badge)

### Layer

**foundational** — No se construye feature de negocio hasta que esto esté listo. EP-001 es blocker de Fase 2.

### Estimación (Rough)

- **Story Points:** 13 (2-3 semanas para 1 backend engineer)
- **Complejidad:** Alta (requiere entender 5+ módulos a fondo)

---

## EP-002: Error Handling & Resilience

### Propósito Ejecutivo

Reemplazar fallos silenciosos por recuperación graciosa, logging estructurado y retry logic automático. Garantizar que fallos en Google Calendar, EspoCRM o Firebird no causen experiencia nula.

### Por Qué Existe

- **Riesgos identificados en PRD:** Gemini latency, Google unavailable, EspoCRM auth, Firebird down, rate attacks
- **Profundidad de flujos:** `reclasificar_caso_sin_licencia` tiene 7 nodos → cambio en un punto puede cascadear en 7
- **Impacto en KPI:** Error rate target es <1%, hoy = desconocido (sin monitoring)
- **Blocker de confianza:** Soporte no confía en el bot si escala falla silenciosamente

### Objetivos PRD que Atiende

- ✅ KPI: Error rate <1%
- ✅ Objetivo 2: Escalar casos con contexto (se pierde contexto si error)
- ✅ Objetivo 4: Funcionar 24/7 (no puede si servicios externos fallan)

### Capabilities Incluidas

- **Nivel 4 (Backend):** Retry logic, circuit breakers, graceful degradation
- **Especialmente:**
  - `tools.py` (todos los tools): retry con exponential backoff (Google, EspoCRM, Firebird)
  - `integrations/google.py` + `integrations/espocrm.py`: circuit breakers
  - `brain.py`: fallback response si Gemini times out (frase pre-grabada)
  - `main.py`: logging estructurado (JSON, levels)
  - `memory.py`: retry en Postgres connection

### Cómo se Mide Éxito

| Métrica | Target | Método |
|---------|--------|--------|
| Error rate en API | <1% | Prometheus metrics |
| P99 latency (Gemini call) | <3s | APM instrumentation |
| Retry success rate | ≥80% | Logs analysis |
| Circuit breaker trips | ≤5/día (bajo tráfico demo) | Logs + alertas |
| Logging coverage | 100% (critical paths) | Code review |

### Artefactos Esperados

- `agent/middleware/retry.py` (decorator retry + exponential backoff)
- `agent/middleware/circuit_breaker.py` (Pybreaker o similar)
- `agent/middleware/logging.py` (JSON logging, levels)
- Updated `integrations/*.py` (retry logic in Google, EspoCRM, Firebird)
- Alerting rules (Prometheus alerts para latency > 3s, error_rate > 1%)
- Runbook: "¿Qué hacer si Firebird está down?" (graceful degradation)

### Layer

**foundational** — Necesario antes de EP-003 (Security). EP-002 es blocker de Fase 2.

### Estimación (Rough)

- **Story Points:** 8 (1.5 semanas para 1 backend engineer)
- **Complejidad:** Media (patrones estándar, pero 5+ integraciones)

---

---

## EP-003: Security Hardening — MINI (v1.0)

### Propósito Ejecutivo

Proteger el demo de ataques obvios (rate limiting, input validation) y asegurar audit trail de decisiones críticas. **MINI scope:** Solo lo crítico para demo segura, sin encryption at rest ni compliance full.

### Por Qué Existe

- **Blocker de Demo:** Demo sin protección = vulnerable a DDoS obvios y log leaks
- **Audit Trail:** Decisiones críticas (escalar, agendar, licencia) deben loguear quién/qué/cuándo
- **Secretos en Logs:** CRITICAL — tokens no deben exponerse en exception logs
- **Timing:** v1.0 demo, no Fase 2 (decidido 2026-07-14)

### Objetivos PRD que Atiende

- ✅ Objetivo 3: Audit logging en `consultar_licencia()` para rastrabilidad
- ✅ Objetivo 4: Funcionar seguro 24/7 (protegido de ataques obvios)
- ✅ Restricción v1: Mínimo security para demo (no full compliance)

### Capabilities Incluidas (MINI)

- **Nivel 4 (Backend):** Rate limiting, input validation, audit logging, secrets scrubbing
- **Especialmente:**
  - `main.py::recibir_webhook()`: Rate limiting 10 req/min per IP (HU-030)
  - `main.py` + `brain.py`: Input sanitization (remove SQL, scripts) (HU-031)
  - `tools.py` (high-stakes): Audit logging (user, tool, timestamp, result) (HU-032)
    - `escalar_a_humano()`
    - `agendar_cita()`
    - `reclasificar_caso_sin_licencia()`
    - `consultar_licencia()`
  - Logging: Scrubbing de tokens en exception handlers (HU-033) — **CRITICAL fix**

### Excluido (Diferir Fase 2)

- ❌ Chat history encryption at rest (DB ya local)
- ❌ mTLS entre servicios (no aplica demo monolítica)
- ❌ Full compliance audit (SOC2, GDPR, etc.)
- ❌ Rate limiting multi-tier (solo per-IP por ahora)

### Cómo se Mide Éxito

| Métrica | Target | Método |
|---------|--------|--------|
| Rate limiting enforced | 10 req/min/IP blocked | Load test + logs |
| Input validation coverage | 100% (webhook + tools) | Security test |
| Secrets in logs | 0 occurrences | Log scanning + CI gate |
| Audit trail completeness | 100% (4 high-stakes tools) | DB audit table queries |
| Tests passing | ≥90% | CI/CD |
| SAST | 0 new CRITICAL | GitHub scanning |

### Artefactos Esperados

- `agent/middleware/rate_limiter.py` (10 req/min per IP)
- Updated `main.py` (apply rate limiter + input validation)
- Updated `tools.py` (audit log calls en 4 tools)
- Updated `agent/middleware/logging.py` (fix exception logging secrets leak)
- Security tests: `tests/security/test_rate_limiting.py`, `test_input_validation.py`, `test_secrets.py`
- Runbook: "If rate limit fails: enable fallback in NocoDB"

### Historias

- HU-030: Rate limiting webhook (4h)
- HU-031: Input validation (3h)
- HU-032: Audit logging (6h)
- HU-033: Secrets scrubbing (2h) ← **CRITICAL GAP-EP002-3 fix**

### Layer

**business** — Feature de negocio: seguridad específica para demo robusta. Construible tras EP-001/EP-002 (cimientos).

### Estimación

- **Story Points:** 5 (mini scope)
- **Esfuerzo:** ~15 horas (~2 días backend + QA)
- **Complejidad:** Media (patrones estándar, solo 4 HU)

---

## EP-005-MINI: Production Deployment Stack

### Propósito Ejecutivo

Empaquetar, asegurar y deployar el sistema a infraestructura productiva. Pase de dev (docker-compose local) a staging (Docker en cloud) a production (Gunicorn + Nginx + monitoring).

### Por Qué Existe

- **Prerequisito de v1.0:** No hay v1.0 sin esto. Hoy: local dev only.
- **Objetivo 4:** Funcionar 24/7 requiere infraestructura confiable (no laptop developer)
- **SLA del PRD:** Uptime 99% no se puede medir/cumplir en dev

### Objetivos PRD que Atiende

- ✅ Objetivo 4: Funcionar 24/7 en producción
- ✅ Objetivo 5: Recolectar leads cualificados (HU-021/023: notificación + follow-up)
- ✅ KPI: Uptime 99%
- ✅ KPI: Response time <500ms (requiere Gunicorn + Nginx)

### Capabilities Incluidas

- **Todas (Nivel 1-4):** Infraestructura para que todo funcione en producción

### Cómo se Mide Éxito

| Métrica | Target | Método |
|---------|--------|--------|
| Deployment time (from git push) | <10 min | CI/CD metrics |
| Rollback time | <5 min | CD manual runbook |
| Uptime | 99% | Monitoring (Prometheus) |
| P99 response time | <500ms | APM instrumentation |
| Error tracking | All errors logged + alertado | Sentry o similar |
| Security scan (SAST) | 0 critical findings | GitHub security scanning |

### Artefactos Esperados

- Dockerfile (multi-stage: build + runtime)
- docker-compose.prod.yml (Gunicorn, Nginx, Postgres, monitoring)
- Kubernetes manifests (si escalamos) o simple Docker en cloud (AWS ECS, DigitalOcean, etc.)
- `.github/workflows/deploy.yml` (CI/CD pipeline: test → build → push → deploy)
- Nginx config: rate limiting, reverse proxy, compression
- Monitoring stack: Prometheus + Grafana (o cloud monitoring)
- Runbook: "How to deploy", "How to rollback", "How to scale"
- Health checks: `/health`, `/ready` endpoints
- Logs: Centralized logging (ELK stack o cloud logs)

### Layer

**business** — Infraestructura de despliegue: necesario para v1.0 release, pero construible tras EP-001/EP-002 (cimientos).

### Estimación (Rough)

- **Story Points:** 8 (1.5-2 semanas para 1 DevOps/Backend)
- **Complejidad:** Media (patrones estándar, pero múltiples moving parts)

### Nota

Puede separarse en:
- EP-005a: Dockerization + basic CI/CD
- EP-005b: Monitoring + alerting
- EP-005c: Scaling + HA (futuro)

---

## FASE 2 — Ruta conversacional completa (Fase 2)

**Contexto:** la ruta actual del webhook va directo al LLM sin gate previo. Estas 5 épicas
implementan la ruta exigida por el negocio (saludo → consentimiento habeas data → alta CRM →
selección de flujo → cierre) y cierran la brecha del modelo de dominio
(`docs/07-arquitectura/fase-2-mvp/02-Modelo_Dominio.md`: `Radicado → Conversación → Mensaje`).
Orden de construcción: EP-006 → EP-007 → EP-008 → EP-009 → EP-010 (foundational antes que business).

---

## EP-006: Modelo Conversación + Consentimiento

### Propósito Ejecutivo

Materializar la entidad `Conversación` (hoy inexistente) y el consentimiento de tratamiento de datos,
ligando `Radicado → Conversación → Mensaje` como manda el modelo de dominio. Cimiento de datos sobre
el que se apoyan EP-008/009/010.

### Por Qué Existe

- **Brecha del modelo de dominio:** el doc declara `Conversación` como entidad entre `Radicado` y
  `Mensaje`, pero no existe en `agent/db.py`. `Mensaje` (en `agent/memory.py`) se liga solo por
  `telefono`, sin conversación ni radicado.
- **Habeas data:** no hay persistencia de consentimiento; legalmente obligatorio antes de capturar PII.
- **Blocker de EP-008/009/010:** el gate de consentimiento, la clasificación de flujo y el cierre
  necesitan una conversación persistida con estado.

### Objetivos PRD que Atiende

- ✅ Trazabilidad de cada interacción (Radicado como agregado raíz)
- ✅ Cumplimiento habeas data (base para EP-008)

### Capabilities Incluidas

- **Nivel 4 (Backend/Datos):** tabla `conversaciones`, columnas de consentimiento en `contactos`,
  FK `mensajes.conversacion_id`, FK `conversaciones.radicado_id`, helpers de apertura/cierre.

### Historias

- HU-034: Entidad Conversación (abrir/cerrar) (complejidad 2)
- HU-035: Cada mensaje ligado a su conversación (1)
- HU-036: Consentimiento persistido en el contacto (1)
- HU-037: Conversación ligada a su radicado (1)

### Layer

**foundational** — cimiento de datos; ninguna épica de negocio (EP-008/009/010) se construye antes.

### Estimación (Rough)

- **Story Points:** 5 · **Complejidad:** Media (modelo + migración)

---

## EP-007: Botones Interactivos WhatsApp

### Propósito Ejecutivo

Habilitar el envío y parseo de botones interactivos de WhatsApp (Meta Cloud API), requisito técnico
del gate de consentimiento (Sí/No). Hoy el provider solo maneja texto.

### Por Qué Existe

- **Restricción actual:** `agent/providers/meta.py` solo envía `type:text` y descarta mensajes
  entrantes que no sean `type:text` — las respuestas de botón se pierden.
- **Blocker de EP-008:** sin botones no hay Sí/No predeterminado para el consentimiento.

### Objetivos PRD que Atiende

- ✅ Base técnica para habeas data (EP-008)

### Capabilities Incluidas

- **Nivel 4 (Backend/Integración):** `enviar_botones()` (payload `interactive`); parseo de
  `type:interactive` (`button_reply.id`) en `parsear_webhook`; `MensajeEntrante` con `tipo`/`payload`.

### Historias

- HU-038: Enviar botones Sí/No al usuario (complejidad 2)
- HU-039: Parsear la respuesta de botón interactivo (1)

### Layer

**foundational** — capacidad de integración; blocker de EP-008.

### Estimación (Rough)

- **Story Points:** 3 · **Complejidad:** Baja-Media

---

## EP-008: Gate de Consentimiento Habeas Data

### Propósito Ejecutivo

Insertar en la ruta del webhook, antes del LLM, el saludo + solicitud de aceptación de tratamiento de
datos con botones Sí/No. Sin consentimiento no se atiende.

### Por Qué Existe

- **Cumplimiento legal:** capturar/registrar PII sin autorización previa es ilegal.
- **Gap de ruta:** `recibir_webhook` va directo a `generar_respuesta` sin gate.

### Objetivos PRD que Atiende

- ✅ Cumplimiento habeas data · ✅ Confianza del usuario

### Capabilities Incluidas

- **Nivel 4 (Backend):** gate en `recibir_webhook`; texto de política editable vía parámetro
  `texto_habeas_data`; ramas aceptar/rechazar.

### Historias

- HU-040: Saludo + solicitud de consentimiento a contacto nuevo (complejidad 2)
- HU-041: Aceptar (Sí) desbloquea el flujo (1)
- HU-042: Rechazar (No) despide y no atiende (1)

### Layer

**business** — construible tras EP-006 (datos) + EP-007 (botones).

### Estimación (Rough)

- **Story Points:** 5 · **Complejidad:** Media

---

## EP-009: Clasificación de Flujo + Alta CRM

### Propósito Ejecutivo

Tras aceptar el consentimiento, clasificar de forma determinista la conversación en
comercial/soporte/otro, persistir el tipo, dar de alta el contacto en el CRM (con teléfono origen) y
ligar la conversación a un radicado.

### Por Qué Existe

- **Routing implícito:** hoy el flujo lo decide el LLM vía tools; `clasificar_intencion` en `brain.py`
  es código muerto. Sin persistir el tipo de solicitud no hay trazabilidad ni reportes por flujo.
- **Alta CRM tardía:** hoy solo se registra lead si el LLM detecta interés comercial.
- **Radicado por escalamiento:** hoy se crea un radicado por cada escalamiento en vez de reutilizar
  el de la conversación.

### Objetivos PRD que Atiende

- ✅ Responder consultas comerciales (lead) · ✅ Escalar soporte con contexto · ✅ Recolectar leads

### Capabilities Incluidas

- **Nivel 4 (Backend):** `clasificar_intencion` real; `Conversacion.tipo_solicitud`; alta CRM al
  aceptar; `escalar_a_humano` reutiliza el radicado de la conversación.

### Historias

- HU-043: Clasificar el flujo y persistirlo en la conversación (complejidad 2)
- HU-044: Alta del contacto en el CRM al aceptar (2)
- HU-045: Un radicado por conversación, reusado al escalar (2)

### Layer

**business** — construible tras EP-006/EP-008.

### Estimación (Rough)

- **Story Points:** 8 · **Complejidad:** Media-Alta (refactor de `escalar_a_humano`)

---

## EP-010: Cierre Explícito de Conversación

### Propósito Ejecutivo

Cerrar la conversación de forma explícita: por indicación del usuario (con despedida) o por
inactividad tras 2 preguntas sin respuesta. Extiende HU-024/HU-025 (archivadas) con la entidad
`Conversación` y la regla de 2 check-ins.

### Por Qué Existe

- **Cierre por usuario ausente:** hoy el LLM puede despedirse pero no cierra formalmente la
  conversación.
- **Inactividad con 1 sola pregunta:** `_revisar_inactividad` hace 1 check-in; el negocio pide 2.

### Objetivos PRD que Atiende

- ✅ Cierre limpio de conversación (journey fase 7)

### Capabilities Incluidas

- **Nivel 4 (Backend):** detección de intención de cierre; `_revisar_inactividad` con 2 check-ins;
  `cerrar_conversacion(motivo)` con `motivo_cierre` (usuario|inactividad).

### Historias

- HU-046: Cierre por indicación del usuario + despedida (complejidad 1)
- HU-047: Cierre por inactividad con 2 preguntas (2)

### Layer

**business** — construible tras EP-006.

### Estimación (Rough)

- **Story Points:** 3 · **Complejidad:** Baja-Media

---

## Matriz de Cobertura: Épicas × Objetivos PRD (v1.0)

| Objetivo PRD | EP-001 | EP-002 | EP-003-MINI | EP-005-MINI | Cobertura |
|--------------|--------|--------|---------|--------|-----------|
| 1. Responder consultas comerciales | ✓ | ✓ | | ✓ | 100% |
| 2. Escalar casos soporte | ✓ | **✓** | **✓** | ✓ | 100% |
| 3. Validar licencias | ✓ | ✓ | **✓** | ✓ | 100% |
| 4. Funcionar 24/7 seguro | ✓ | **✓** | **✓** | **✓** | 100% |
| 5. Recolectar leads | | | | ✓ | 100% |

**Leyenda:** `✓` = atendido incidentalmente, `**✓**` = atendido directamente  
**Nota:** EP-004 (RAG) eliminada completamente del alcance de v1.0.

---

## Matriz de Cobertura: Épicas × KPIs (v1.0)

| KPI | EP-001 | EP-002 | EP-003-MINI | EP-005-MINI | Status |
|-----|--------|--------|---------|--------|--------|
| Test coverage ≥60% | ✓ | | | | 🟡 In progress (60.39%) |
| Error rate <1% | | ✓ | **✓** | ✓ | 🚀 New (EP-003-MINI) |
| Velocidad <30s | ✓ | ✓ | | ✓ | ✓ Archivada |
| Uptime 99% | | ✓ | | **✓** | 🚀 New (EP-005) |
| Conversión 25% | | | | ✓ | 🟡 Deferred (leads capture) |

---

## Huérfanos Detectados

### Objetivos sin épica clara

**Ninguno.** Todas las visiones del PRD están cubiertas.

### Épicas sin objetivo claro

**Ninguna.** Cada épica atiende al menos 1 objetivo PRD.

### Capabilities sin épica

| Capability | Por qué falta | Acción |
|-----------|---------------|--------|
| Dashboard de analytics | No aparece en v1 (out-of-scope) | Diferir a v2 |
| Bi-directional Salesforce sync | EspoCRM is primero (out-of-scope v1) | Diferir a Fase 2 |
| Rich media (carousels, buttons) | Constrains v1: solo texto | Diferir a Fase 2 |

---

## Orden de Ejecución (v1.0 DEMO)

### Fase 1: Cimientos + Demo v1.0 (~1-2 semanas)

1. ✅ **EP-001** (Test Suite Foundation) — Archivada. Gaps documentados en GAPS_EP001_EP002_AUDIT.md
2. ✅ **EP-002** (Error Handling & Resilience) — Archivada. Gaps + 3 CRITICAL fixes documentados
3. 🚀 **EP-003-MINI** (Security Hardening Demo) — 4 HU nuevas, 2 días. Reemplaza Fase 2, entra en v1.0
4. 🚀 **EP-005-MINI** (Deployment Stack) — Docker + CI/CD + health checks, 3-4 días

### Parallelization Options

- **Option A (Fastest):** EP-001/002 fixes + EP-003-MINI → Laptop demo (Hoy → Mañana)
- **Option B (Staging):** Anterior + EP-005-MINI deployment → Cloud demo (Next 3-4 days)
- **Option C (Production):** Anterior + lead capture + config UI → Full KPIs demo (2 weeks)

---

## Notas de Planificación (v1.0 DEMO)

- **Dependency:** EP-001/002 ya archivadas. Gaps documentados, requieren fixes (~2-3 días).
- **EP-003-MINI:** 4 HU nuevas, 2 días. Reemplaza Fase 2 full scope.
- **EP-005-MINI:** 3-4 días (Docker + CI/CD + health checks).
- **Timing:** Laptop demo hoy → Mañana PM (con fixes rápidos EP-002). Staging demo 3-4 días. Full demo 2 semanas.
- **Team:** 2 backend engineers (fixes + EP-003/005), 1 QA (security tests).
- **Scope:** EP-001 + EP-002 + EP-003-MINI + EP-005-MINI = v1.0 demo. EP-004 (RAG) eliminada, puede re-introducirse.

---

## Próximos Pasos (v1.0 DEMO Execution)

### Paso 1: Planificar Correcciones (Today)
- Documentar gaps EP-001/002 → **DONE:** GAPS_EP001_EP002_AUDIT.md
- Planificar fixes por severidad (GAP-EP002-3 first, CRITICAL)
- Crear plan de desarrollo EP-003-MINI + EP-005-MINI

### Paso 2: Ejecutar Fixes + EP-003-MINI (Next 2-4 days)
- Fix EP-001 GAP-001-3 (timeout Gemini) — 4h
- Fix EP-002 GAP-{1,2,3} (retry, circuit, secrets) — 8h
- Build EP-003-MINI HU-030/031/032/033 — 15h
- QA security tests — 4h

### Paso 3: Deploy + Demo (Next week or 2 weeks)
- Optional: EP-005-MINI deployment stack (3-4 days)
- Staging demo + KPIs measurement
- Customer-facing demo (full production-grade)

---

**Documento actualizado:** 2026-07-14  
**Estado:** Active — Lista para ejecución  
**Owner:** IngKevin95  
**Auditoría Factory:** Completa (3 agentes, hallazgos documentados)

---
---
## EP-REPAIRS: Deuda Técnica y Correcciones
**Prioridad:** Alta | **Complejidad:** Baja
**Descripción:** Correcciones de bugs detectados y estabilización del código existente.
**Historias:**
- [FIX-REPAIR-001](docs/04-historias/FIX-REPAIR-001.md) (Eliminado, ver HU-033)
- [FIX-REPAIR-002](docs/04-historias/FIX-REPAIR-002.md)
- [FIX-REPAIR-003](docs/04-historias/FIX-REPAIR-003.md)
- [FIX-REPAIR-004](docs/04-historias/FIX-REPAIR-004.md)

---

## FASE 3 — Scale-Out & Integraciones Avanzadas (Post-v1.0)

**Contexto:** Tras estabilizar el core del bot en la Fase 1 y Fase 2, la Fase 3 se enfoca en expandir las capacidades del producto hacia nuevos canales, formatos interactivos, visibilidad de datos e integraciones empresariales avanzadas (como se define en el PRD).

---

## EP-011: Rich Media & Componentes Interactivos

### Propósito Ejecutivo

Permitir que el bot envíe y procese contenido enriquecido (carruseles de productos, archivos PDF como cotizaciones, imágenes y notas de voz) para mejorar la experiencia del usuario y hacerla más atractiva.

### Por Qué Existe

- **Limitación actual:** El bot (v1) solo admite texto plano y botones simples (Sí/No).
- **Expectativa del usuario:** En flujos comerciales, los clientes esperan catálogos visuales o poder enviar notas de voz cuando están ocupados.

### Objetivos PRD que Atiende

- ✅ Mejorar la conversión comercial (mostrar vs. contar).
- ✅ Incrementar el NPS y satisfacción del usuario (UX más rica).

### Capabilities Incluidas

- **Nivel 4:** Soporte para recepción/envío de Media en `providers/meta.py`. Parsing de notas de voz usando Whisper/Google STT. Generación de plantillas (templates) de WhatsApp con carruseles para "Consultar Ofertas".

### Historias (Tentativas)

- HU-048: Enviar catálogos y ofertas usando WhatsApp Carousel Templates.
- HU-049: Enviar y recibir archivos adjuntos (PDFs de cotizaciones).
- HU-050: Transcribir notas de voz del usuario a texto (Voice-to-Text).

### Layer

**business** — Mejora de producto y experiencia de usuario.

---

## EP-012: Soporte Multi-canal (Telegram & SMS)

### Propósito Ejecutivo

Desacoplar la lógica conversacional (Brain) del proveedor Meta, permitiendo que el bot responda desde Telegram o Webchat/SMS, ampliando la cobertura de usuarios.

### Por Qué Existe

- **Riesgo:** Dependencia exclusiva de Meta Cloud API (single point of failure y lock-in).
- **Adopción:** Ciertos perfiles B2B prefieren canales alternativos.

### Objetivos PRD que Atiende

- ✅ Extender la disponibilidad a otras plataformas (Multi-canal).

### Capabilities Incluidas

- **Nivel 4:** Implementar nuevos adaptadores en `providers/` (ej. `telegram.py`, `twilio.py`). Refactor de `main.py` para exponer webhooks por canal.

### Historias (Tentativas)

- HU-051: Adaptador y Webhook para Telegram.
- HU-052: Enrutamiento de mensajes Multi-canal en `agent/main.py`.

### Layer

**foundational/business** — Arquitectura de adaptadores y feature de negocio.

---

## EP-013: Dashboard de Analytics y Reportes

### Propósito Ejecutivo

Construir una interfaz visual (UI) de analíticas para que el equipo comercial y los líderes de soporte puedan medir el impacto del bot, ver el volumen de leads y el turnaround.

### Por Qué Existe

- **Problema:** Actualmente las métricas están enterradas en PostgreSQL, Prometheus o EspoCRM. No hay una vista unificada de "Cuántos leads generó el bot hoy".
- **Objetivo de Negocio:** Visibilidad clara del ROI del bot.

### Objetivos PRD que Atiende

- ✅ Monitoreo de KPIs de Negocio (Conversión, Resueltas automáticamente, Leads capturados).

### Capabilities Incluidas

- **Nivel 4:** Endpoints de analíticas en FastAPI o integración de Metabase/Grafana Business Dashboard conectada a PostgreSQL.

### Historias (Tentativas)

- HU-053: Endpoint agregador de métricas comerciales y de soporte.
- HU-054: Integración/Dashboard visual (Metabase o frontend simple) para KPIs del bot.

### Layer

**business** — Feature de inteligencia de negocios.

---

## EP-014: Sincronización Bidireccional Avanzada (CRM & ERP)

### Propósito Ejecutivo

Sincronizar de forma profunda el bot con herramientas empresariales más robustas (como Salesforce) y permitir actualización bidireccional (si el ticket se cierra en CRM, notificar al usuario en WhatsApp).

### Por Qué Existe

- **Limitación actual:** La integración con EspoCRM es básica (crear caso/lead). El bot no sabe cuándo un agente humano resolvió el caso si el usuario no pregunta.
- **Escalabilidad:** Empresas más grandes requerirán Salesforce.

### Objetivos PRD que Atiende

- ✅ Automatizar triaje de soporte con loop cerrado (notificación proactiva).

### Capabilities Incluidas

- **Nivel 4:** Background tasks (Celery/Cron) o Webhooks inversos desde el CRM al bot para emitir notificaciones activas (`template messages` en WhatsApp).

### Historias (Tentativas)

- HU-055: Webhook inverso desde EspoCRM para notificar al usuario el cierre de ticket.
- HU-056: Adaptador para integración con Salesforce.

### Layer

**business** — Operaciones empresariales.

---

## EP-015: Resiliencia de Escalamiento y Notificaciones a Líderes

### Propósito Ejecutivo

Garantizar que ningún fallo de servicios externos (Google/Calendar) se pierda silenciosamente y que los escalamientos lleguen a la persona correcta: al líder de infraestructura ante fallos técnicos, y al líder comercial del área cuando la cola se satura.

### Por Qué Existe

- **Bug detectado en producción:** un `RefreshError` de Google Calendar (token revocado) no era error de cuota, así que el `except` de las tools de Calendar lo dejaba escapar sin loggear ni escalar. El cliente recibía un mensaje de "inconveniente técnico" improvisado por el LLM y no había rastro en logs.
- **Punto ciego operativo:** solo los fallos de cuota alertaban a infra; cualquier otro fallo de Google era invisible.
- **Escalamiento sin dueño:** cuando todos los agentes de un área están ocupados, el caso queda en cola sin que ningún líder se entere para intervenir.

### Objetivos PRD que Atiende

- ✅ Escalamiento confiable a humano (loop cerrado, sin casos perdidos).
- ✅ Observabilidad operativa de fallos de integración.

### Capabilities Incluidas

- Manejo genérico de fallos de Google/Calendar (no solo cuota): log estructurado + escalamiento + alerta a infra.
- Parámetro configurable `whatsapp_lider_infra` para notificación por WhatsApp ante fallo técnico.
- Parámetro configurable `whatsapp_lider_<area>` para notificación por WhatsApp al líder comercial cuando un caso entra en cola.

### Historias

- HU-057: Manejo robusto y observable de fallos de Google/Calendar (no solo cuota); degradación a franja de BD.
- HU-058: Notificación WhatsApp al líder de infraestructura ante fallo técnico.
- HU-059: Notificación WhatsApp al líder comercial del área cuando un caso entra en cola.
- HU-060: Validación de correo del cliente e inclusión como invitado en la cita.

### Layer

**foundational** — Resiliencia y observabilidad del núcleo de escalamiento; habilita confiabilidad para las épicas de negocio.
