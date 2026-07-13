# User Story Map: DemoWhatsappAgent

**Patrón:** Jeff Patton (Backbone horizontal, tareas bajo cada actividad, épicas como líneas)  
**Perspectiva primaria:** Cliente B2B buscando información (usuario externo)  
**Perspectivas secundarias:** Equipo Soporte, Equipo Comercial (internos)  
**Fecha:** 2026-07-12

---

## Backbone (Actividades Principales — Eje Temporal)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  1. INICIO  2. CONSULTA  3. BÚSQUEDA  4. DECISIÓN  5. ESCALACIÓN  6. SEGUIMIENTO  7. CIERRE
│    DE       COMERCIAL    DE INFO      DE CONTACTO  A HUMANO        (POST-ACCIÓN)   DE FLUJO
│  CONVERSACIÓN
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Detalle: Historias por Actividad

### 1️⃣ INICIO DE CONVERSACIÓN

**Descripción:** Usuario abre WhatsApp, busca el bot, envía primer mensaje.  
**Épica(s) bloqueador:** EP-001 (tests), EP-002 (error handling), EP-003 (security)

#### Historias

| ID | Título | Descripción | Prioridad |
|----|--------|------------|-----------|
| HU-001 | Como usuario, quiero saludar al bot y recibir respuesta amigable | Primer contacto: "Hola", bot responde con bienvenida contextual | MUST |
| HU-002 | Como usuario, quiero decirle al bot qué necesito en lenguaje natural | "Quiero info de precios" → bot entiende intent sin menú | MUST |
| HU-003 | Como usuario, quiero que el bot sea accesible 24/7 | No esperar horario comercial | SHOULD |

#### Criterios de Éxito

- ✅ Webhook recibe mensaje Meta, valida firma
- ✅ Gemini orquesta respuesta (no cuelga)
- ✅ Respuesta llega en <30s
- ✅ Historial inicia (memoria)

---

### 2️⃣ CONSULTA COMERCIAL

**Descripción:** Usuario pregunta sobre precio, disponibilidad, qué incluye un módulo.  
**Épica(s) atendida:** EP-001 (tests), EP-004 (RAG si es pregunta compleja)

#### Historias

| ID | Título | Descripción | Prioridad |
|----|--------|------------|-----------|
| HU-004 | Como usuario, quiero consultar el precio de un módulo específico | "¿Cuánto cuesta el módulo X?" → bot devuelve precio actual | MUST |
| HU-005 | Como usuario, quiero saber qué incluye cada módulo/plan | "¿Qué viene en plan Pro?" → descripción detallada | MUST |
| HU-006 | Como usuario, quiero ver ofertas/promociones activas | "¿Hay descuentos?" → lista promociones vigentes | SHOULD |
| HU-007 | Como usuario, quiero comparar dos planes | "Diferencia entre Plan A y Plan B" → comparativa | COULD |

#### Criterios de Éxito

- ✅ Tool `consultar_precio_modulo()` devuelve datos correctos (Postgres)
- ✅ Tool `consultar_ofertas_activas()` devuelve data fresh
- ✅ Gemini formatea respuesta de forma legible
- ✅ Latencia <500ms (query DB + Gemini)

#### Dependencias

- Postgres actualizado con precios/ofertas
- Parámetros configurables (NocoDB) si cambian precios sin deploy

---

### 4️⃣ DECISIÓN DE CONTACTO

**Descripción:** Usuario quiere dar un paso: agendar demo, contactar equipo, registrarse.  
**Épica(s) atendida:** EP-001 (tests), EP-003 (security, audit logging)

#### Historias

| ID | Título | Descripción | Prioridad |
|----|--------|------------|-----------|
| HU-011a | Como usuario, quiero agendar una demo en un slot disponible | "Quiero hablar con alguien el martes a las 3pm" → cita en calendario con confirmación explícita | MUST |
| HU-011b | Como equipo interno, quiero recibir notificación de nueva demo agendada | Email + caso EspoCRM con ticket ID cuando se confirma la cita | SHOULD |
| HU-012 | Como usuario, quiero saber si mi soporte está vigente | "¿Tengo soporte incluido?" → valida licencia en BD | MUST |
| HU-013 | Como usuario, quiero registrarme como cliente nuevo | "Quiero contratar Plan Pro" → captura datos, crea oportunidad | SHOULD |
| HU-014 | Como usuario, quiero ver el estado de mi licencia | "¿Cuándo vence mi soporte?" → fecha exacta | SHOULD |

#### Criterios de Éxito (High-Stakes — Requiere Audit Logging)

- ✅ Tool `agendar_cita()` crea evento real en Google Calendar
- ✅ Confirmación por email llega al usuario
- ✅ Caso se crea en EspoCRM
- ✅ Audit log: usuario, acción, timestamp, resultado
- ✅ Tool `consultar_licencia()` devuelve estado correcto desde Firebird
- ✅ Si sin_licencia → sugerir renovación (no negar acceso agresivo)

#### Dependencias

- Google Calendar OAuth funciona
- Firebird tiene datos de licencias (demo hoy, producción después)
- Email delivery confiable (Gmail API)
- Audit logging implementado (EP-003)

---

### 5️⃣ ESCALACIÓN A HUMANO

**Descripción:** Usuario necesita hablar con un humano (pregunta muy compleja, o bot no puede resolver).  
**Épica(s) atendida:** EP-001 (tests), EP-002 (error handling), EP-003 (security + audit)

#### Historias (Usuario → Bot)

| ID | Título | Descripción | Prioridad |
|----|--------|------------|-----------|
| HU-015 | Como usuario, quiero contactar directo con el equipo | "Quiero hablar con alguien" → escala a humano | MUST |
| HU-016 | Como usuario, quiero que mi caso tenga número de ticket | Seguimiento: "¿Cuál es mi caso?" → devuelve ticket ID | SHOULD |

#### Historias (Equipo Soporte → Sistema)

| ID | Título | Descripción | Prioridad |
|----|--------|------------|-----------|
| HU-017 | Como Soporte, quiero recibir notificación de escalación | Email con: usuario, qué preguntó, por qué escaló | MUST |
| HU-018 | Como Soporte, quiero acceder al contexto de la conversación | Historial de chat visible en EspoCRM (caso) | MUST |
| HU-019 | Como Soporte, quiero trijar si es comercial o técnico | Reclasificar caso (cambiar área responsable) | SHOULD |

#### Criterios de Éxito

- ✅ Tool `escalar_a_humano()` crea caso en EspoCRM
- ✅ Email enviado a grupo Soporte (gmail)
- ✅ Audit log completo (usuario escaló qué, por qué, cuándo)
- ✅ Historial de chat persisted en BD (visible en caso)
- ✅ Si sin_licencia detectado → reclasificar a comercial automáticamente
- ✅ Usuario recibe número de ticket en chat

#### Dependencias

- EspoCRM REST API accesible
- Email delivery confiable
- Historial persistido en Postgres
- Error handling robusto (EP-002)

---

### 6️⃣ SEGUIMIENTO

**Descripción:** Post-cierre de chat: confirmación por email, notificación a comercial, follow-up automático.  
**Épica(s) atendida:** EP-001 (tests), EP-005 (deploy necesario para 24/7 automation)

#### Historias (Usuario)

| ID | Título | Descripción | Prioridad |
|----|--------|------------|-----------|
| HU-020 | Como usuario, quiero confirmación por email de lo acordado | "Tu cita está agendada para..." (resumen) | SHOULD |

#### Historias (Equipo Comercial)

| ID | Título | Descripción | Prioridad |
|----|--------|------------|-----------|
| HU-021 | Como Comercial, quiero ser notificado de nuevos leads | Daily digest: usuarios que consultaron + datos capturados | SHOULD |
| HU-022 | Como Comercial, quiero saber qué preguntó cada lead | Lead source = "bot", contexto = historial chat | SHOULD |

#### Criterios de Éxito

- ✅ Email enviado automáticamente post-cita
- ✅ Lead creado en EspoCRM con source = "bot"
- ✅ Lead tiene contexto: qué preguntó, cuándo, prioridad (implicada)
- ✅ Follow-up cron job corre 24/7 (depende deployment)

#### Dependencias

- Gmail API confiable
- EspoCRM actualizado en tiempo real
- Scheduler en background (lifespan en main.py)
- Deployment en producción (EP-005)

---

### 7️⃣ CIERRE DE FLUJO

**Descripción:** Conversación terminada. Usuario se fue, caso se archiva o pasa a Comercial.  
**Épica(s) atendida:** Todas (cierre graceful requiere todo lo anterior funcionando)

#### Historias

| ID | Título | Descripción | Prioridad |
|----|--------|------------|-----------|
| HU-024 | Como usuario, quiero cerrar la conversación cuando termine | "Gracias, chao" → bot detecta fin, archiva historial | SHOULD |
| HU-025 | Como sistema, quiero cleanup de inactividad | Si >5 min sin respuesta → check-in; >10 min → cierre automático | SHOULD |

#### Criterios de Éxito

- ✅ Historial finalizado en BD
- ✅ Caso escalado (si aplica) está en manos de Soporte/Comercial
- ✅ Inactividad detector corre cada 60s (background)
- ✅ Graceful shutdown: "Fue un gusto. Quedamos en contacto" + archiva

---

## Matriz: Actividades × Épicas (Fase 1 Demo)

| Actividad | EP-001 | EP-002 | EP-003 | EP-005 |
|-----------|--------|--------|--------|--------|
| 1. Inicio | **✓** | ✓ | ✓ | |
| 2. Consulta Comercial | ✓ | ✓ | | |
| 4. Decisión Contacto | **✓** | ✓ | **✓** | |
| 5. Escalación | **✓** | **✓** | **✓** | |
| 6. Seguimiento | ✓ | | | **✓** |
| 7. Cierre | ✓ | ✓ | | ✓ |

**Leyenda:** `**✓**` = bloqueador directo, `✓` = atendida pero no crítica

---

## Línea de MVP (v1.0)

### Dónde Corta (Rebanada Vertical)

**MVP cubre todas las 7 actividades del backbone, pero con profundidad variable:**

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. INICIO │ 2. CONSULTA │ 4. DECISIÓN │ 5. ESCALACIÓN │ 6. SEG. │ 7. CIERRE
│(HU-001-03)│ (HU-004-07) │(HU-011a-b   │  (HU-015-019) │(HU-020-22│ (HU-024-25)
│           │             │ HU-012-14)  │               │ Notif) │
└─────────────────────────────────────────────────────────────────┘
 ▓▓▓▓▓▓▓▓▓▓  ▓▓▓▓▓▓▓▓▓▓   ▓▓▓▓▓▓▓▓▓▓    ▓▓▓▓▓▓▓▓▓▓     ░░░░░░░░░░  ░░░░░░░░░░
      MVP         MVP          MVP           MVP          MVP mín.    MVP mín.
    (welcome,    (price,      (booking,   (escalation   (email +    (close +
     intent)   includes,      license,     w/ ticket,   lead       inactiv.
               offers)        register)    triage)      digest)     detect)
```

### Por Qué Este Corte (Vertical, No Horizontal)

| Característica | v1.0 | Razón |
|---|---|---|
| Consultas comerciales | ✅ **Completo** | Core value, simple de implementar |
| Búsqueda (RAG) | ✅ **Completo** | Diferenciador, realista en 2-3 sem |
| Agendar cita + Licencias | ✅ **Completo** | High-value, integraciones Google + Firebird |
| Escalación inteligente | ✅ **Completo** | Cierre de loop, necesario para confianza |
| Confirmación de cita | ⚠️ **Mínimo** | Email básico + notificación a Soporte (HU-011b); lead digest automático = v1.1 |
| Cierre de conversación | ⚠️ **Mínimo** | Detección de fin de sesión + cierre graceful (HU-024/025); follow-up automático = v1.1 |
| Lead nurturing automático | ❌ **v1.1** | Requiere scheduler robusto (EP-005 foundation); manual: OK en v1.0 |
| Multi-canal (Telegram, SMS) | ❌ **v1.1** | Fase 2 después de estabilizar WhatsApp |
| Rich media (botones, carruseles) | ❌ **v1.1** | Constrains v1: solo texto |

### Esfuerzo Estimado

**MVP (v1.0):** 5 épicas × 6 sem = ~30 person-weeks  
**Extras para v1.1:** EP-004b (RAG refinement), multi-channel, rich media = +2-3 sem

---

## Gaps de Cobertura Detectados

### Histórico Sin Épica Explícita

| Gap | Ubicación | Acción | Épica |
|-----|-----------|--------|-------|
| HU-007 (Comparativa módulos) | Actividad 2 | Básico: Gemini formatea comparativa | EP-001 (tests) |

### Actividades sin Test Explícito

| Actividad | Riesgo | Mitigación |
|-----------|--------|-----------|
| 4. Decisión (agendar + licencia) | Google/Firebird down | EP-002 (circuit breaker) + EP-003 (audit) |
| 5. Escalación (EspoCRM email) | Email no entrega | EP-002 (retry) + alerting |
| 6. Seguimiento (cron job) | Scheduler falla silencioso | EP-001 (tests cron) + EP-005 (monitoring) |

### Historias Que Necesitan Refinamiento

| HU | Refinamiento | Prioridad |
|----|--------------|-----------|
| HU-019 (Reclasificación) | ¿Automática o manual? Especificar | SHOULD |

---

## Priorización Vertical: Orden de Escritura de Historias

### Fase 1: Cimientos (Semana 1-2, en paralelo con épicas)

1. **EP-001 Tests** (escribir HU de testing infrastructure, no de features)
   - No hay HU de usuario aquí, pero escribir "test scenarios" para los tests

2. **EP-003 Security** (escribir HU que cubre validación + audit)
   - HU-S001: Como sistema, quiero validar firmas Meta en webhook
   - HU-S002: Como sistema, quiero logging de high-stakes actions

### Fase 1B: Features (Semana 2-4)

3. **Actividad 1 (Inicio):** HU-001, HU-002, HU-003
4. **Actividad 2 (Consulta):** HU-004, HU-005, HU-006
5. **Actividad 4 (Decisión):** HU-011a, HU-011b, HU-012, HU-013

### Fase 1C: Escalación (Semana 5-6)

6. **Actividad 5 (Escalación):** HU-015, HU-016, HU-017, HU-018, HU-019

### Fase 1D: Seguimiento y Cierre (Semana 6-7)

7. **EP-005 Deploy** (necesario para automation)
8. **Actividad 6 (Seguimiento):** HU-020, HU-021, HU-022
9. **Actividad 7 (Cierre):** HU-024, HU-025

---

## Notas Finales

### Journey Primario vs. Secundarios

**Primario:** Usuario cliente B2B → Consulta → Escalación (si aplica) → Lead capturado  
**Secundario 1:** Equipo Soporte → Recibe escalación → Triaja → Resuelve  
**Secundario 2:** Equipo Comercial → Revisa leads → Follow-up → Cierre venta

Todas las tres perspectivas están mapeadas, pero el backbone sigue el journey cliente.

### Fuera de Alcance: Fase 1 Demo (v1.0)

**Esta fase 1 Demo SOLAMENTE cubre:**
- Inicio de conversación (bienvenida, intent recognition)
- Consulta comercial (precios, qué incluye, ofertas)
- Decisión de contacto (agendar, licencias, registrarse)
- Escalación a humano (ticket, contexto, triaje)
- Seguimiento mínimo (emails básicos, lead digest)
- Cierre de conversación (detección de fin, inactividad)

**Postergado a fases futuras:**
- v1.1: RAG (búsqueda semántica), follow-up automático avanzado
- v1.2: Multi-channel (Telegram, SMS), rich media, analytics
- v2.0: Salesforce sync, AI recomendaciones, custom training

---

## Próximo Paso

**Opción A:** `/factory:historia HU-001` — Empezar a escribir historias (una por una)  
**Opción B:** `/factory:flujo` — Automatizar generación de todas las historias (recomendado)  
**Opción C:** `/factory:revisar` — Auditar mapa antes de historias

**Recomendación:** Opción B (`/factory:flujo`) — es más rápido y revisa los TODOs.

---

**Documento generado:** 2026-07-12  
**Historias esperadas:** 25 (HU-001 a HU-025, + HU-S001-S002 de security)  
**Estado:** Draft, listo para `/factory:historia`
