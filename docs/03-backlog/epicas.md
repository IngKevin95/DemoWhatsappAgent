# Épicas: DemoWhatsappAgent

**Fuente:** DemoWhatsappAgent-PRD.md  
**Fecha:** 2026-07-12  
**FASE 1 DEMO (v1.0) — FINAL:**  
- **Épicas Activas:** EP-001 (14 HU), EP-002 (1 HU), EP-005 (2 HU)
- **Total v1.0:** 17 HU
- **Deferred v1.1+:** EP-003 (Security), EP-004 (RAG)
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

**Foundational** — No se construye feature de negocio hasta que esto esté listo.

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

**Foundational** — Necesario antes de EP-003 (Security).

### Estimación (Rough)

- **Story Points:** 8 (1.5 semanas para 1 backend engineer)
- **Complejidad:** Media (patrones estándar, pero 5+ integraciones)

---

---

## 🔄 DEFERRED A v1.1 (Fase 2+)

---

## EP-003: Security Hardening (v1.1)

### Propósito Ejecutivo

Proteger el sistema de ataques (rate limiting, input validation, audit logging) y asegurar que datos sensibles (tokens, credenciales) no se loguean ni se exponen.

### Por Qué Existe

- **Hub node sin audit:** `escalar_a_humano()` (degree 32) crea case + email sin trail de quién/qué/cuándo
- **Entry point sin defensa:** `recibir_webhook()` (degree 28) valida firma Meta pero no rate limits
- **Datos sensibles sin protección:** Chat history en Postgres sin encriptación, tokens en filesystem
- **Blocker de Producción:** No se deploya sin al menos:
  - Rate limiting en webhook
  - Input validation en webhook
  - Audit logging en high-stakes tools
  - No exponemos secretos en logs/errors

### Objetivos PRD que Atiende

- ✅ Objetivo 3: Validar elegibilidad de licencias (audit logging en `consultar_licencia()`)
- ✅ Objetivo 4: Funcionar seguro 24/7 (protegido de ataques)
- ✅ Restricción v1: Mínimo security (no es full compliance, pero lo básico)

### Capabilities Incluidas

- **Nivel 4 (Backend):** Validación, rate limiting, audit logging
- **Especialmente:**
  - `main.py::recibir_webhook()`: Rate limiting por IP + por user
  - `main.py` + `brain.py`: Input sanitization (remove SQL, scripts, etc.)
  - `tools.py` (high-stakes): Audit logging (user, tool, timestamp, result)
    - `escalar_a_humano()` ← especialmente
    - `agendar_cita()`
    - `reclasificar_caso_sin_licencia()`
    - `consultar_licencia()`
  - `memory.py`: Chat history encryption at rest (simple: AES-256 + master key)
  - Logging: Scrubbing de tokens (DATABASE_URL, GOOGLE_*, META_*)

### Cómo se Mide Éxito

| Métrica | Target | Método |
|---------|--------|--------|
| Rate limiting enforced | ≥3 tiers (global, per-IP, per-user) | Load test + logs |
| Input validation coverage | 100% (webhook + tools) | Code review + security test |
| Secrets in logs | 0 occurrences | Log scanning (grep -i password, token, key) |
| Audit trail completeness | 100% (high-stakes tools) | DB audit table + logs |
| Test: SQL injection attempt | Blocked | Security test |
| Test: XSS attempt | Blocked | Security test |
| Test: Rate limit bypass | Failed | Load test |

### Artefactos Esperados

- `agent/middleware/rate_limiter.py` (token bucket o sliding window)
- `agent/middleware/input_validator.py` (sanitization rules)
- `agent/middleware/audit_logger.py` (structured logging to DB)
- Updated `tools.py` (audit log calls en escalar, agendar, reclasificar, consultar_licencia)
- `agent/middleware/secrets_scrubber.py` (logging filter)
- `agent/security/encryption.py` (AES-256 para chat history)
- Security tests: `tests/security/test_rate_limiting.py`, `test_input_validation.py`, `test_secrets.py`
- Runbook: "Incident response si rate limiting falla"

### Layer

**Foundational** — Necesario para v1.0 release.

### Estimación (Rough)

- **Story Points:** 13 (2.5 semanas para 1 backend engineer)
- **Complejidad:** Alta (múltiples capas de seguridad)

---

## EP-004: RAG Backend (v1.1) (Knowledge Base)

### Propósito Ejecutivo

Implementar backend de búsqueda semántica para que la herramienta `buscar_en_conocimiento()` funcione. Hoy es un stub desconectado. Con RAG, bot puede responder preguntas complejas sobre productos/servicios sin tener que hard-code.

### Por Qué Existe

- **Capability desconectada:** `consultar_precio_modulo()` funciona, pero `buscar_en_conocimiento()` es un stub (no tiene backend)
- **Blocker de Valor:** Usuarios B2B harán preguntas tipo "¿Qué incluye el módulo X?" o "¿Cuál es la diferencia entre plan A y B?" — hoy no hay forma de responder
- **Mejora de Conversión:** RAG permite respuestas más ricas → mejor lead nurturing
- **Mejora de Soporte:** Usuarios pueden auto-resolver con FAQ embeddeadas

### Objetivos PRD que Atiende

- ✅ Objetivo 1: Responder consultas comerciales al instante (con contexto, no solo tablas)
- ✅ KPI: Conversión 25% (mejor si respondemos preguntas profundas)

### Capabilities Incluidas

- **Nivel 1 (Comercial):** `buscar_en_conocimiento()` con backend real
- **Infraestructura:**
  - Vector store: Pinecone, Weaviate o pgvector (Postgres local)
  - Embeddings: OpenAI, Gemini o local (all-MiniLM)
  - Chunking strategy: Recursive text splitter (1000 tokens, 200 overlap)
  - Retrieval: Top-K (k=3-5), similarity threshold > 0.7

### Cómo se Mide Éxito

| Métrica | Target | Método |
|---------|--------|--------|
| Recall (relevant docs found) | ≥80% | Manual evaluation set |
| Precision (top-3 are relevant) | ≥70% | Manual evaluation set |
| Query latency | <500ms | APM instrumentation |
| Embedding quality | Cosine similarity > 0.8 for duplicate questions | Semantic similarity tests |
| End-to-end test | "¿Qué incluye módulo X?" → correcta respuesta | Integration test |

### Artefactos Esperados

- `agent/rag/embeddings.py` (wrapper para embeddings)
- `agent/rag/vector_store.py` (interface para Pinecone/Weaviate/pgvector)
- `agent/rag/retriever.py` (search + ranking)
- `agent/rag/chunker.py` (recursive text splitter)
- Knowledge base seed data: `data/knowledge_base/*.md` (FAQ, product specs, etc.)
- Ingestion script: `scripts/ingest_knowledge.py` (populate vector store)
- Tests: `tests/integration/test_rag_retrieval.py`, `test_embedding_quality.py`
- Evaluation set: `data/rag_eval_set.jsonl` (Q&A pairs para testing)

### Layer

**Business** — Mejora UX pero no es blocker crítico de v1.0. Puede diferirse a v1.1.

### Estimación (Rough)

- **Story Points:** 13 (2.5-3 semanas para 1 backend engineer)
- **Complejidad:** Media-Alta (requiere experiencia con RAG)

### Nota

Si no entra en Fase 1, pasa a EP-001-v1.1.

---

## EP-005: Production Deployment

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

**Foundational** — Necesario para v1.0 release. Pero puede ser minimal (no full Kubernetes) para fase 1.

### Estimación (Rough)

- **Story Points:** 8 (1.5-2 semanas para 1 DevOps/Backend)
- **Complejidad:** Media (patrones estándar, pero múltiples moving parts)

### Nota

Puede separarse en:
- EP-005a: Dockerization + basic CI/CD
- EP-005b: Monitoring + alerting
- EP-005c: Scaling + HA (futuro)

---

## Matriz de Cobertura: Épicas × Objetivos PRD

| Objetivo PRD | EP-001 | EP-002 | EP-003 | EP-004 | EP-005 | Cobertura |
|--------------|--------|--------|--------|--------|--------|-----------|
| 1. Responder consultas comerciales | ✓ | ✓ | ✓ | **✓** | ✓ | 100% |
| 2. Escalar casos soporte | ✓ | **✓** | **✓** | | ✓ | 100% |
| 3. Validar licencias | ✓ | ✓ | ✓ | | ✓ | 100% |
| 4. Funcionar 24/7 | ✓ | **✓** | **✓** | | **✓** | 100% |
| 5. Recolectar leads | | | | **✓** | ✓ | 100% |

**Leyenda:** `✓` = atendido incidentalmente, `**✓**` = atendido directamente

---

## Matriz de Cobertura: Épicas × KPIs

| KPI | EP-001 | EP-002 | EP-003 | EP-004 | EP-005 |
|-----|--------|--------|--------|--------|--------|
| Cobertura 40% | ✓ | | | ✓ | |
| Velocidad <30s | ✓ | ✓ | | ✓ | |
| Conversión 25% | | | | ✓ | |
| Uptime 99% | | ✓ | | | ✓ |
| Test coverage 60% | ✓ | | | | |
| Error rate <1% | | ✓ | | | |

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
| Bi-directional Salesforce sync | EspoCRM is primero (out-of-scope v1) | Diferir a v1.1 |
| Rich media (carousels, buttons) | Constrains v1: solo texto | Diferir a v1.1 |

---

## Orden de Ejecución (Recomendado)

### Fase 1A: Cimientos (4 semanas)

1. **EP-001** (Test Suite) — Blocker de todo lo demás
2. **EP-002** (Error Handling) — Depende de tests para validar
3. **EP-003** (Security) — Depende de tests + error handling

### Fase 1B: Valor (2-3 semanas, paralelo a 1A si recursos)

4. **EP-004** (RAG Backend) — Independiente de EP-001-003

### Fase 2: Release (1-2 semanas)

5. **EP-005** (Production Deployment) — Depende de EP-001-003 completadas

---

## Notas de Planificación

- **Dependency:** EP-001 es blocker hard de todo. No avanzar sin test coverage ≥60%.
- **Parallelism:** EP-004 (RAG) puede correr en paralelo con EP-001-003 si hay recursos.
- **Timing:** Fase 1 (5 épicas) = ~6 semanas, 5 FTE (Tech Lead + Backend x2 + QA + DevOps part-time).
- **Scope:** Estas 5 épicas cubren v1.0 completa. Todo lo demás (multi-channel, Salesforce, etc.) es v1.1+.

---

## Próximo Paso

**Opción A:** `/factory:historia` — Empezar a escribir historias de usuario de EP-001  
**Opción B:** `/factory:mapa` — Primero visualizar journey end-to-end (Jeff Patton)  
**Opción C:** `/factory:revisar` — Auditar cobertura de épicas vs. PRD  

**Recomendación:** Opción B → A (User Story Map → Historias).

---

**Documento generado:** 2026-07-12  
**Revisor asignado:** (pendiente)  
**Estado:** Draft (listo para `/factory:revisar`)
