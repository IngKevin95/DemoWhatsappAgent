# Backlog Consolidado: DemoWhatsappAgent v1.0 FINAL

**Fuente:** 24 Historias de Usuario — Fase 1 Demo + Security + Deployment  
**Épicas v1.0:** 4 (EP-001, EP-002, EP-003-MINI, EP-005-MINI)  
**Eliminadas:** EP-004 (RAG, indefinidamente deferred)  
**Framework:** Valor / Esfuerzo (priorización ejecutada)  
**Fecha:** 2026-07-14  
**Alcance v1.0:** Bot conversa, consultas, agendar, escalación, cierre, security (rate limit, input validation, audit, secrets), deployment (Docker, CI/CD, monitoring)

---

## Tabla Consolidada: Todas las Historias v1.0 (24 HU) — ORDENADAS POR RATIO V/E

| Prioridad | HU | Título | Épica | Complejidad | Estado | V/E Ratio |
|-----------|----|----|-------|-------------|--------|-----------|
| **MUST** | HU-004 | Consultar precio de módulo | EP-001 | 1 | archivada | 5.0 |
| **MUST** | HU-005 | Saber qué incluye cada módulo | EP-001 | 1 | archivada | 5.0 |
| **MUST** | HU-012 | Consultar si soporte vigente | EP-001 | 1 | archivada | 5.0 |
| **MUST** | HU-030 | Rate limiting en webhook | EP-003-MINI | 1 | lista | 5.0 |
| **MUST** | HU-031 | Input validation & sanitization | EP-003-MINI | 1 | lista | 5.0 |
| **MUST** | HU-033 | Secrets scrubbing en logs | EP-003-MINI | 1 | lista | 5.0 |
| **MUST** | HU-001 | Primer contacto — bienvenida | EP-001 | 1 | archivada | 5.0 |
| **MUST** | HU-024 | Usuario cierra conversación | EP-001 | 1 | archivada | 4.0 |
| **SHOULD** | HU-014 | Ver estado de licencia | EP-001 | 1 | archivada | 4.0 |
| **SHOULD** | HU-025 | Sistema detecta inactividad | EP-001 | 1 | archivada | 4.0 |
| **SHOULD** | HU-006 | Ver ofertas y promociones | EP-001 | 1 | archivada | 4.0 |
| **SHOULD** | HU-011b | Notificaciones post-agenda | EP-001 | 1 | archivada | 4.0 |
| **SHOULD** | HU-003 | Disponibilidad 24/7 en producción | EP-005-MINI | 1 | lista | 4.0 |
| **MUST** | HU-032 | Audit logging en high-stakes tools | EP-003-MINI | 2 | lista | 2.5 |
| **MUST** | HU-002 | Reconocimiento de intención (NLU) | EP-001 | 2 | archivada | 2.5 |
| **MUST** | HU-015 | Contactar directo con equipo (escalación) | EP-001 | 2 | archivada | 2.5 |
| **MUST** | HU-011a | Agendar demo/consultoría | EP-001 | 2 | archivada | 2.5 |
| **MUST** | HU-028 | Health checks & monitoring | EP-005-MINI | 2 | lista | 1.5 |
| **SHOULD** | HU-013 | Registrarse como cliente nuevo | EP-001 | 2 | archivada | 1.5 |
| **SHOULD** | HU-019 | Soporte triaja (comercial vs técnico) | EP-002 | 2 | archivada | 1.5 |
| **SHOULD** | HU-021 | Comercial notificado de nuevos leads | EP-005-MINI | 2 | lista | 1.5 |
| **COULD** | HU-007 | Comparar dos módulos | EP-001 | 2 | archivada | 1.5 |
| **MUST** | HU-026 | Dockerization (multi-stage) | EP-005-MINI | 2 | lista | 1.5 |
| **MUST** | HU-027 | CI/CD pipeline GitHub Actions | EP-005-MINI | 2 | lista | 1.0 |

---

## FASE 2 — Ruta conversacional (Fase 2): 14 HU nuevas

Orden de construcción foundational → business (EP-006 → EP-010). V/E indicativo.

| Prioridad | HU | Título | Épica | Complejidad | Estado |
|-----------|----|----|-------|-------------|--------|
| **MUST** | HU-034 | Entidad Conversación (abrir/cerrar) | EP-006 | 2 | draft |
| **MUST** | HU-035 | Mensaje ligado a su conversación | EP-006 | 1 | draft |
| **MUST** | HU-036 | Consentimiento persistido en el contacto | EP-006 | 1 | draft |
| **SHOULD** | HU-037 | Conversación ligada a su radicado | EP-006 | 1 | draft |
| **MUST** | HU-038 | Enviar botones Sí/No | EP-007 | 2 | draft |
| **MUST** | HU-039 | Parsear respuesta de botón interactivo | EP-007 | 1 | draft |
| **MUST** | HU-040 | Saludo + solicitud de consentimiento | EP-008 | 2 | draft |
| **MUST** | HU-041 | Aceptar (Sí) desbloquea el flujo | EP-008 | 1 | draft |
| **MUST** | HU-042 | Rechazar (No) despide y no atiende | EP-008 | 1 | draft |
| **MUST** | HU-043 | Clasificar el flujo y persistirlo | EP-009 | 2 | draft |
| **MUST** | HU-044 | Alta del contacto en CRM al aceptar | EP-009 | 2 | draft |
| **SHOULD** | HU-045 | Un radicado por conversación, reusado al escalar | EP-009 | 2 | draft |
| **MUST** | HU-046 | Cierre por indicación del usuario + despedida | EP-010 | 1 | draft |
| **SHOULD** | HU-047 | Cierre por inactividad con 2 preguntas | EP-010 | 2 | draft |

---

## Resumen por Épica (v1.0)

| Épica | Historias | Cantidad | Estado | Esfuerzo |
|-------|-----------|----------|--------|----------|
| **EP-001** (Test Suite + Features) | HU-001 a 007, 011a/b, 012 a 015, 024 a 025 | 14 HU | ✅ ARCHIVADA | Completada |
| **EP-002** (Error Handling & Resilience) | HU-019 | 1 HU | ✅ ARCHIVADA | Completada |
| **EP-003-MINI** (Security Hardening) | HU-030, 031, 032, 033 | 4 HU | 🚀 NUEVA | 2 días |
| **EP-005-MINI** (Deployment Stack) | HU-003, 021, 026, 027, 028 | 5 HU | 🚀 NUEVA | 3-4 días |

**Total v1.0:** 24 HU

---

## Resumen por Journey (Core Bot Flow)

| Fase | Historias | Estado |
|------|-----------|--------|
| **0. Security** | HU-030, 031, 032, 033 | 🚀 Nueva (EP-003-MINI) |
| **1. Inicio** | HU-001, 002, 003 | ✅ Archivada + Nueva (HU-003) |
| **2. Consulta Comercial** | HU-004, 005, 006, 007 | ✅ Archivada |
| **4. Decisión** | HU-011a/b, 012, 013, 014 | ✅ Archivada |
| **5. Escalación** | HU-015, 019 | ✅ Archivada |
| **6. Seguimiento** | HU-021 | 🚀 Nueva (EP-005-MINI) |
| **7. Cierre** | HU-024, 025 | ✅ Archivada |
| **9. Deployment** | HU-026, 027, 028 | 🚀 Nueva (EP-005-MINI) |

---

## Distribución de Complejidad (24 HU v1.0)

| Complejidad | Cantidad | Ejemplos |
|------------|----------|----------|
| **1 (Trivial)** | 11 | HU-001, 003, 004, 005, 006, 011b, 014, 024, 030, 031, 033 |
| **2 (Media)** | 12 | HU-002, 007, 011a, 013, 015, 019, 021, 025, 026, 027, 028, 032 |
| **3 (Alta)** | 1 | HU-012 (consultar licencia) |

---

## Estado por Épica

| Épica | Status | Gaps Documentados | Fixes Necesarios | Timeline |
|-------|--------|------------------|------------------|----------|
| EP-001 | ✅ Archivada | 7 gaps (GAPS_EP001_EP002_AUDIT.md) | 4 críticos | Día 1-2 |
| EP-002 | ✅ Archivada | 7 gaps (GAPS_EP001_EP002_AUDIT.md) | 3 críticos | Día 1-2 |
| EP-003-MINI | 🚀 Nueva | Ninguno (scope definido) | Construcción nueva | Día 3-4 |
| EP-005-MINI | 🚀 Nueva | Ninguno (scope definido) | Construcción nueva | Día 5-7 |

---

## Próximos Pasos

1. ✅ **Documentación Cerrada:** epicas.md + backlog.md + 7 HUs nuevas + 3 documentos de plan
2. → **Ejecutar Fixes EP-001/002:** PLAN_CORRECCIONES_EP001_EP002.md (prioridad: FIX-EP002-3 FIRST)
3. → **Construir EP-003-MINI:** HU-030/031/032/033
4. → **Construir EP-005-MINI:** HU-026/027/028 (opcional si demo staging/prod)

---

**Generado:** 2026-07-14  
**Revisor:** IngKevin95  
**Estado:** ✅ FINAL — Documentación Cerrada, Listo para Ejecución
