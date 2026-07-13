# Backlog Consolidado: DemoWhatsappAgent

**Fuente:** 17 Historias de Usuario — Fase 1 Demo SOLAMENTE  
**Épicas Activas v1.0:** 3 (EP-001, EP-002, EP-005)  
**Épicas Diferidas v1.1:** EP-003 (Security), EP-004 (RAG)  
**Framework:** Valor / Esfuerzo  
**Fecha:** 2026-07-12  
**Alcance v1.0:** Bienvenida, consultas comerciales, agendar demo, escalación, cierre graceful, disponibilidad 24/7, notificación de leads

---

## Tabla Consolidada: Todas las Historias

| Prioridad | HU | Título | Épica | Complejidad | Estado | Actividad |
|-----------|----|----|-------|-------------|--------|-----------|
| **MUST** | HU-001 | Primer contacto — bienvenida | EP-001 | 1 | draft | 1. Inicio |
| **MUST** | HU-002 | Reconocimiento de intención (NLU) | EP-001 | 2 | draft | 1. Inicio |
| **SHOULD** | HU-003 | Disponibilidad 24/7 | EP-005 | 1 | draft | 1. Inicio |
| **MUST** | HU-004 | Consultar precio de módulo | EP-001 | 1 | draft | 2. Consulta |
| **MUST** | HU-005 | Saber qué incluye cada módulo | EP-001 | 1 | draft | 2. Consulta |
| **SHOULD** | HU-006 | Ver ofertas y promociones | EP-001 | 1 | draft | 2. Consulta |
| **COULD** | HU-007 | Comparar dos módulos | EP-001 | 2 | draft | 2. Consulta |
| **MUST** | HU-011a | Agendar demo/consultoría | EP-001 | 2 | lista | 4. Decisión |
| **SHOULD** | HU-011b | Notificaciones post-agenda | EP-001 | 1 | lista | 4. Decisión |
| **MUST** | HU-012 | Consultar si soporte vigente | EP-001 | 1 | lista | 4. Decisión |
| **SHOULD** | HU-013 | Registrarse como cliente nuevo | EP-001 | 2 | draft | 4. Decisión |
| **SHOULD** | HU-014 | Ver estado de licencia | EP-001 | 1 | draft | 4. Decisión |
| **MUST** | HU-015 | Contactar directo con equipo (escalación + ticket + contexto) | EP-001 | 2 | draft | 5. Escalación |
| **SHOULD** | HU-019 | Soporte triaja (comercial vs técnico) | EP-002 | 2 | draft | 5. Escalación |
| **SHOULD** | HU-021 | Comercial notificado de nuevos leads | EP-005 | 2 | draft | 6. Seguimiento |
| **SHOULD** | HU-024 | Usuario cierra conversación | EP-001 | 1 | draft | 7. Cierre |
| **SHOULD** | HU-025 | Sistema detecta inactividad | EP-001 | 1 | draft | 7. Cierre |

---

## Resumen por Épica

| Épica | Historias v1.0 | Cantidad | Estado |
|-------|-----------|----------|--------|
| **EP-001** (Test Suite + Features) | HU-001, 002, 004, 005, 006, 007, 011a, 011b, 012, 013, 014, 015, 024, 025 | 14 HU | ✅ ACTIVA |
| **EP-002** (Error Handling + Triaje) | HU-019 | 1 HU | ✅ ACTIVA |
| **EP-005** (Deploy + Disponibilidad) | HU-003, 021 | 2 HU | ✅ ACTIVA |

---

## Resumen por Actividad (Journey Usuarios)

| Actividad | Historias v1.0 | Estado |
|-----------|-----------|--------|
| 1. Inicio de Conversación | HU-001, 002, 003 | ✅ v1.0 |
| 2. Consulta Comercial | HU-004, 005, 006, 007 | ✅ v1.0 |
| 4. Decisión de Contacto | HU-011a/b, 012, 013, 014 | ✅ v1.0 |
| 5. Escalación a Humano | HU-015, 019 | ✅ v1.0 |
| 6. Seguimiento | HU-021, 022 | ✅ v1.0 |
| 7. Cierre de Flujo | HU-024, 025 | ✅ v1.0 |

---

## Distribución de Complejidad (17 HU v1.0)

| Complejidad | Cantidad | Ejemplos |
|------------|----------|----------|
| **1 (Trivial)** | 8 | HU-001, 003, 004, 005, 006, 011b, 014, 024 |
| **2 (Media)** | 8 | HU-002, 007, 011a, 013, 015, 019, 021, 025 |
| **3 (Alta)** | 1 | HU-012 |

**Observación:** Mayoría son triviales-media (8+8 = 16 de 17). Solo 1 es alta (consultar licencia — high-stakes y bien justificada).

---

## Resumen de Cobertura

| Criterio | Cumple | Detalles |
|----------|--------|----------|
| **Cobertura PRD** | ✅ 100% | Todos los objetivos cubiertos por historias |
| **Cobertura Épicas** | ✅ 100% | 3 épicas activas tienen historias (EP-001, EP-002, EP-005) |
| **Cobertura USM** | ✅ 100% | 6 actividades v1.0 tienen historias |
| **AC Formato** | ✅ 100% | Todas en Given/When/Then (con error/edge tras remediación) |
| **High-Stakes Audit Logging** | ✅ | HU-011a, 012, 015, 019 marcadas |
| **INVEST Validation** | 🔄 En progreso | 4/17 aprobadas; 13 en remediación |
| **Roles Específicos** | 🔄 En progreso | 17/17 requieren re-titulación (eliminar "usuario" genérico) |

---

## Notas Finales

- **Backlog Fase 1 Demo:** 17 historias (HU-001 a HU-007, HU-011a/b, HU-012 a HU-015, HU-019, HU-021, HU-022, HU-024, HU-025)
- **Épicas v1.0:** 3 (EP-001, EP-002, EP-005)
- **Actividades Completas:** 6 de 7 (excluye búsqueda semántica que es v1.1)
- **Remediación en curso:** Ampliar AC de error/edge + re-titular roles + declarar dependencias

---

**Generado:** 2026-07-12  
**Estado:** Draft, listo para Paso 6 (Priorización)
