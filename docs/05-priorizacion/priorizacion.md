# Priorización: Matriz Valor/Esfuerzo

**Framework:** Valor / Esfuerzo (2×2)  
**Criterio:** Impacto usuario × Complejidad técnica + riesgo  
**Fecha:** 2026-07-12  
**Versión:** 6 (Fase 1 Demo + Security + Deployment: 24 HU v1.0 COMPLETO)

---

## Matriz (Posicionamiento Conceptual)

```
ALTO VALOR
    ↑
    │  Quick Wins              Strategic
    │  (V:4-5, E:1-2)          (V:4-5, E:3-5)
    │                          ← HACER PRIMERO
    │  HU-004,005,014,024      HU-001,002,011,012,015
    │
────┼───────────────────────────→ ESFUERZO
    │
    │  Fill-ins                Time Sinks
    │  (V:2-3, E:1-2)          (V:2-3, E:3-5)
    │
BAJO VALOR
```

---

## Tabla Ordenada (Valor ÷ Esfuerzo Ratio) — 24 Historias (Fase 1 Demo COMPLETO)

| Prioridad | HU | Título | Valor | Esfuerzo | Ratio | Cuadrante | Épica |
|-----------|----|----|-------|----------|-------|----------|-------|
| 1️⃣ | HU-004 | Consultar precio | 5 | 1 | 5.0 | Quick Win | EP-001 |
| 2️⃣ | HU-005 | Qué incluye módulo | 5 | 1 | 5.0 | Quick Win | EP-001 |
| 3️⃣ | HU-012 | Consultar licencia | 5 | 1 | 5.0 | Quick Win | EP-001 |
| 4️⃣ | HU-030 | Rate limiting en webhook | 5 | 1 | 5.0 | Quick Win | EP-003-MINI |
| 5️⃣ | HU-031 | Input validation & sanitization | 5 | 1 | 5.0 | Quick Win | EP-003-MINI |
| 6️⃣ | HU-033 | Secrets scrubbing en logs | 5 | 1 | 5.0 | Quick Win | EP-003-MINI |
| 7️⃣ | HU-001 | Primer contacto | 5 | 1 | 5.0 | Quick Win | EP-001 |
| 8️⃣ | HU-024 | Usuario cierra | 4 | 1 | 4.0 | Quick Win | EP-001 |
| 9️⃣ | HU-014 | Estado de licencia | 4 | 1 | 4.0 | Quick Win | EP-001 |
| 🔟 | HU-025 | Inactividad detector | 4 | 1 | 4.0 | Quick Win | EP-001 |
| 1️⃣1️⃣ | HU-006 | Ofertas y promociones | 4 | 1 | 4.0 | Quick Win | EP-001 |
| 1️⃣2️⃣ | HU-011b | Notificaciones post-agenda | 4 | 1 | 4.0 | Quick Win | EP-001 |
| 1️⃣3️⃣ | HU-003 | Disponibilidad 24/7 | 4 | 1 | 4.0 | Quick Win | EP-005-MINI |
| 1️⃣4️⃣ | HU-032 | Audit logging en high-stakes tools | 5 | 2 | 2.5 | Strategic | EP-003-MINI |
| 1️⃣5️⃣ | HU-002 | Intent recognition | 5 | 2 | 2.5 | Fill-in* | EP-001 |
| 1️⃣6️⃣ | HU-015 | Escalar a humano | 5 | 2 | 2.5 | Fill-in* | EP-001 |
| 1️⃣7️⃣ | HU-011a | Agendar cita | 5 | 2 | 2.5 | Fill-in* | EP-001 |
| 1️⃣8️⃣ | HU-026 | Dockerization multi-stage | 3 | 2 | 1.5 | Fill-in | EP-005-MINI |
| 1️⃣9️⃣ | HU-028 | Health checks & monitoring | 3 | 2 | 1.5 | Fill-in | EP-005-MINI |
| 2️⃣0️⃣ | HU-013 | Registrarse cliente | 3 | 2 | 1.5 | Fill-in | EP-001 |
| 2️⃣1️⃣ | HU-019 | Reclasificar caso | 3 | 2 | 1.5 | Fill-in | EP-002 |
| 2️⃣2️⃣ | HU-021 | Comercial notificado | 3 | 2 | 1.5 | Fill-in | EP-005-MINI |
| 2️⃣3️⃣ | HU-007 | Comparar módulos | 3 | 2 | 1.5 | Fill-in | EP-001 |
| 2️⃣4️⃣ | HU-027 | CI/CD pipeline GitHub Actions | 3 | 3 | 1.0 | Time Sink | EP-005-MINI |

---

## Resumen por Cuadrante (24 HU — Fase 1 Demo COMPLETO v1.0)

### 🟢 Quick Wins (Hacer Primero)
**13 historias** — Alto valor, bajo esfuerzo

Incluye: HU-001, 003, 004, 005, 006, 011b, 012, 014, 024, 025, 030, 031, 033

**Costo:** ~24-26 story points  
**Beneficio:** Bienvenida, consultas, disponibilidad, cierre, rate limiting, input validation, secrets scrubbing

### 🔵 Strategic (Hacer Segundo)
**4 historias** — Alto valor, alto esfuerzo

Incluye: HU-002, 011a, 015, 032

**Costo:** ~10-12 story points  
**Beneficio:** Intent routing + agendar + escalación + audit logging (cierra Fase 1 Demo)

### 🟡 Fill-ins (Hacer Después si Tiempo)
**6 historias** — Valor medio, esfuerzo medio

Incluye: HU-007, 013, 019, 021, 026, 028

**Costo:** ~14-16 story points  
**Beneficio:** Licencias, comparativa, registro, triaje, notificaciones, Dockerization, monitoring

### 🔴 Time Sinks (Evaluar vs Timeline)
**1 historia** — Valor medio, alto esfuerzo

Incluye: HU-027 (CI/CD 3 stages)

**Costo:** ~3 story points  
**Beneficio:** Automatización deploy (diferible si presión timeline)


---

## Roadmap de Sprints (Propuesto)

### Sprint 1 (2 semanas) — MVP Foundation
**Objetivo:** Quick Wins — Bienvenida, consultas, cierre

| Historias | Costo | Épica |
|-----------|-------|-------|
| HU-001 | 1 pt | EP-001 (bienvenida) |
| HU-004, 005, 006 | 3 pts | EP-001 (consultas: precio, módulos, ofertas) |
| HU-012, 014 | 2 pts | EP-001 (licencia: consulta, estado) |
| HU-024, 025 | 2 pts | EP-001 (cierre: usuario cierra, inactividad) |
| HU-003 | 1 pt | EP-005 (disponibilidad 24/7) |
| **Subtotal** | **10 pts** | **EP-001, EP-005** |

**Blockers:** EP-001 (Test Suite) + EP-005 (Deployment basics) deben estar ✅

---

### Sprint 2 (2 semanas) — Escalación Completa
**Objetivo:** Intent routing + escalación con ticket + agendar demo + reclasificación

| Historias | Costo | Épica |
|-----------|-------|-------|
| HU-002 | 2 pts | EP-001 (intent recognition) |
| HU-015 | 2 pts | EP-001 (escalación: ticket + email + contexto integrado) |
| HU-011a | 2 pts | EP-001 (agendar: evento + slots + confirmación) |
| HU-011b | 1 pt | EP-001 (agendar: notificaciones post-agenda) |
| HU-019 | 2 pts | EP-002 (reclasificación de caso) |
| **Subtotal** | **9 pts** | **EP-001, EP-002** |

**Blockers:** EP-002 (Error Handling) para retry/graceful degradation

---

### Sprint 3 (2 semanas) — Fill-ins
**Objetivo:** Comparativa, registro, lead digest, detalles técnicos

| Historias | Costo | Épica |
|-----------|-------|-------|
| HU-007 | 2 pts | EP-001 (comparar módulos) |
| HU-013 | 2 pts | EP-001 (registrar cliente) |
| HU-019 | 2 pts | EP-002 (reclasificación) |
| HU-021 | 2 pts | EP-005 (lead digest daily) |
| **Subtotal** | **8 pts** | **EP-001, EP-002, EP-005** |

**Objetivo:** Completar cobertura de Fase 1 Demo. Opcional si tiempo limitado.

---

## Ratios y Métricas (17 HU Fase 1 Demo v1.0)

| Métrica | Valor |
|---------|-------|
| **Valor Promedio (1-5)** | 3.8 |
| **Esfuerzo Promedio (1-5)** | 1.5 |
| **Ratio Promedio (V/E)** | 2.85 |
| **Story Points Totales** | ~24-26 pts |
| **Quick Wins %** | 59% (10/17) |
| **Strategic %** | 18% (3/17) |
| **Fill-ins %** | 24% (4/17) |
| **Coverage (Fase 1 Demo)** | 100% (17/17) |

---

## Recomendaciones (Fase 1 Demo v1.0)

1. **Orden de Sprints:** Sprint 1 (Quick Wins) → Sprint 2 (Strategic) → Sprint 3 (Fill-ins)
2. **Parallelización:** EP-001 (sprints 1-2) y EP-005 (sprint 1+) son independientes; posible paralelizar si hay equipo
3. **MVP Gate:** Después de Sprint 2 (~26-28 pts), MVP cubre escalación completa (bienvenida + consultas + agendar + escalación + cierre)
4. **Futuro (Fase 2):** Búsqueda semántica (RAG), follow-up automático, multi-canal — fuera de alcance Fase 1

---

**Generado:** 2026-07-12  
**Versión:** 5 (Fase 1 Demo final, Fase 2 ELIMINADAS)  
**Estado:** 17 HU v1.0 priorizadas, listo para `/build:setup`
