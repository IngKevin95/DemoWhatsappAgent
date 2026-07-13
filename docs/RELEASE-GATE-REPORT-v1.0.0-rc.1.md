# Release Gate Report: v1.0.0-rc.1

**Release ID:** R1-mvp  
**Épicas:** EP-001 (Test Suite), EP-002 (Error Handling), EP-005 (Production Deployment)  
**Fecha:** 2026-07-13  
**Status:** ❌ FAILED (Backup Point Only — No Production Ready)

---

## Executive Summary

R1-mvp completó integration testing (✅ PASS) pero falló en 4 de 5 gates de revisión crítica:
- Security: 3 CRITICAL, 3 HIGH, 2 MEDIUM
- Code Smell: Deuda técnica (funciones oversized 80-110L)
- Coherence: 28-32% AC coverage (68-72% AC huérfanos)
- Stack/Architecture: Credenciales hardcodeadas, config no editable

**Este branch es un punto de control únicamente. No está listo para producción.**

---

## Gate Results

### 🔴 SECURITY — FAILED

**Hallazgos Críticos (3):**
1. Credenciales hardcodeadas en docker-compose.yml + .env (Postgres, NocoDB, Meta, Gemini)
2. Sin rate limiting en webhook `/recibir_webhook` → DoS risk
3. OAuth tokens Google (token.json) expuestos en volumen Docker sin encriptación

**Hallazgos High (3):**
4. Logging inseguro — imprime respuestas Meta sin filtrado (information disclosure)
5. Chat history en texto plano en Postgres (privacy breach, PII)
6. Endpoint `/agentes/{telefono}/liberar` sin autenticación

**Hallazgos Medium (2):**
7. Firebird default password débil (`sysbot`)
8. Inyección indirecta vía LLM (bajo si mantiene SQLAlchemy, riesgo de regression)

**Impacto:** Cualquiera con acceso al repo accede a todas las APIs externas. Tokens vivos (Meta, Gemini).

---

### 🟡 CODE SMELL — FAILED

**Violaciones Beck (Regla 4: métodos < 30L):**

1. **`agent/tools.py:263-342` — `agendar_cita()` — 80 líneas**
   - Responsabilidades mixtas: concurrencia + búsqueda horarios + Google Calendar + email + EspoCRM
   - Anidación 4+ niveles
   - Fix: extraer `_buscar_horario()`, `_crear_evento_integrado()`

2. **`agent/tools.py:418-528` — `escalar_a_humano()` — 110 líneas**
   - Ciclomática ~8, múltiples paths (directo, agente, queue)
   - Fix: extraer `_buscar_agente()`, `_conectar_agente()`, `_encolar()`

3. **`agent/brain.py:144-174` — `generar_respuesta()` — 30 líneas**
   - Comprime 3-4 responsabilidades (retry + historial + Gemini + fallback)
   - Fix: decorator `@retry_on_rate_limit()`, extraer `_convertir_historial()`

**Duplicación (Regla 2):**
- Meta wrapper en tools.py vs integrations/meta.py
- Try-except email en agendar_cita vs escalar_a_humano

**Impacto:** Difícil de testear, mantener y refactorizar sin romper cosas.

---

### ✅ UX — N/A

(No aplica — bot de WhatsApp sin UI web. Design source = N/A.)

---

### 🔴 COHERENCE — FAILED

**Cobertura AC:** 28-32% (18-20 de 63 AC)  
**AC Huérfanos:** 43-45 (68-72%)

**Bloqueadores Críticos:**
- AC-4 (error handling) sin test en 10+ HU: HU-001, HU-004, HU-006, HU-011a, HU-012, HU-013, HU-015
- Confirmación explícita (HU-011a agendar, HU-015 escalar) no validada en tests
- HU-003 (disponibilidad 24/7), HU-005 (detalles), HU-007 (comparativa), HU-014 (licencia) sin cobertura

**Falta OpenSpec:**
- No existen `proposal.md` formales en `.claude/changes/`
- Trazabilidad AC → spec tasks → código no explícita

**Tests sin justificación (33%):**
- 8 casos de prueba (02_info_empresa, 06_horario, 09_estado_no_registrado, 13-15_ticket, 19_prompt_injection, 20_dato_sensible) sin AC claro

**Infraestructura sin tests:**
- HU-021 (leads digest): solo draft
- HU-025 (inactividad): implementada pero sin tests

**Impacto:** No hay garantía de que AC se implementen correctamente. Regresiones silenciosas en producción.

---

### 🔴 STACK/ARCHITECTURE — FAILED

**Violaciones Críticas:**

1. **Credenciales en Texto Plano** (agent/integrations/google.py:11, docker-compose.yml:60)
   - Tokens Google/Meta/Gemini en .env sin secrets manager
   - Firebird password débil por defecto
   - Violación: ARCHITECTURE.md§Stack promete "credenciales gestionadas"

2. **Config Hardcodeada**
   - `HORARIOS_DISPONIBLES` en código (línea 13 google.py)
   - `TZ_OFFSET = "-05:00"` hardcodeado
   - Violación: PRD requiere "parámetros editables desde NocoDB sin deploy"

**Violaciones Media:**

3. **Retry/Circuit Breaker Inconsistente**
   - Gemini: 2 intentos solo para 429
   - EspoCRM: sin reintentos (falla instantánea en timeout)
   - Meta: sin reintentos en envío mensajes

4. **Logging Inseguro** (agent/providers/meta.py:63)
   - `print("META ERROR BODY:", resp.text)` sin filtrado
   - Puede exponer tokens/credenciales

---

### ✅ INTEGRATION — PASSED

**Status:** Funcional end-to-end  
**Journeys Validados:**
- ✅ Saludo → Gemini → WhatsApp
- ✅ Consulta precio → PostgreSQL
- ✅ Agendar → Google Calendar + Email
- ✅ Escalamiento → radicado + audit log
- ✅ Licencia → Firebird deterministic

**Infraestructura:**
- ✅ PostgreSQL 16, Firebird 3.0, NocoDB, Gemini, Google OAuth, Meta Webhook
- ⚠️ EspoCRM DNS falla (fallback graceful)

**Seguridad & Audit:**
- ✅ Sin credenciales en logs
- ✅ 416 mensajes auditados
- ✅ Error handling graceful

**Gaps:**
- EspoCRM hostname resolve issue (dev: usar localhost:8081)
- Sin circuit breaker explícito

---

## Blockers Antes de Próximo Release Gate

| ID | Blocker | Prioridad | Componente |
|----|---------|-----------|-----------|
| SEC-001 | Rotar credentials Meta + Gemini | 🔴 CRITICAL | Infra |
| SEC-002 | Implementar secrets manager | 🔴 CRITICAL | Infra |
| SEC-003 | Rate limiting en webhook | 🔴 CRITICAL | agent/main.py |
| SEC-004 | Auth en `/agentes/liberar` | 🔴 CRITICAL | agent/main.py |
| SMELL-001 | Refactor agendar_cita (80L → <30L) | 🟡 HIGH | agent/tools.py |
| SMELL-002 | Refactor escalar_a_humano (110L → <40L) | 🟡 HIGH | agent/tools.py |
| SMELL-003 | Eliminar duplicación Meta | 🟡 HIGH | agent/tools.py |
| COHESION-001 | OpenSpec proposal.md (EP-001, EP-002) | 🟡 HIGH | .claude/changes/ |
| COHESION-002 | AC-4 (error handling) en 10+ HU | 🟡 HIGH | tests/ |
| ARCH-001 | Config horarios → DB (no código) | 🟡 MEDIUM | agent/integrations/ |
| ARCH-002 | Config TZ → env var (no código) | 🟡 MEDIUM | agent/integrations/ |
| ARCH-003 | Retry/circuit breaker en EspoCRM | 🟡 MEDIUM | agent/integrations/ |

---

## Próximos Pasos

### Fase A: Security Fixes (Semana 1-2)
1. Rotar credentials (Meta, Gemini, Google)
2. Implementar secrets manager (AWS Secrets / Vault)
3. Rate limiting en webhook (SlowAPI)
4. Auth en endpoints críticos
5. Re-run security gate

### Fase B: Code Cleanup (Semana 2-3)
1. Refactor funciones oversized
2. Eliminar duplicación
3. Re-run smell gate

### Fase C: Coherence + Architecture (Semana 3-4)
1. Crear OpenSpec proposal.md por épica
2. AC-4 tests (error handling)
3. Config editable (horarios, TZ → DB)
4. Retry/circuit breaker
5. Re-run coherence + stack gates

### Release Gate v1.0.0-rc.2
Todos los gates: ✅ PASS (security, smell, coherence, stack, integration)

---

## Cambios en Este Branch

```
92 files changed, 12,092 insertions(+)
```

Cubre todas las épicas v1.0:
- EP-001: Test Suite Foundation (14 HU)
- EP-002: Error Handling & Resilience (1 HU)
- EP-005: Production Deployment (2 HU)

**Total v1.0:** 17 HU implementadas, 63 AC formalizados.

---

## Notas

- **Branch creada:** 2026-07-13 (release/v1.0.0-rc.1)
- **Punto de control:** Sí, para tracking de versiones
- **Listo para producción:** No. Múltiples hallazgos de seguridad bloqueantes
- **Próxima acción:** Volver a `develop`, crear tickets de fix, re-correr Release Gate en v1.0.0-rc.2

---

**Generado por:** releasing-a-version skill  
**Revisor:** Release Gate (5 subagentes)
