---
titulo: DemoWhatsappAgent PRD
estado: draft
version: 0.1.0
fecha_creacion: 2026-07-12
autores: Factory CLI + IngKevin95
stakeholders: Product Manager (TBD), Tech Lead (IngKevin95), Equipo Comercial, Equipo Soporte
framework_priorizacion: Valor / Esfuerzo
---

# PRD: DemoWhatsappAgent

## 1. Visión / Problema

### Problema

Las empresas B2B que venden software/servicios con modelo de licencias enfrentan tres desafíos operacionales fragmentados:

1. **Comercial:** Consultas de precio, disponibilidad, demos → requiere respuesta inmediata (hoy: email/llamada, turnaround = horas)
2. **Soporte:** Casos técnicos llegan por múltiples canales → requiere triaje y escalación inteligente (hoy: manual, error-prone)
3. **Administración:** Validar si usuario tiene licencia vigente → requiere consulta BD + decisión (hoy: manual, sin auditoria)

**Costo:** Tiempo de respuesta elevado, caídas de leads, carga manual de equipos, experiencia de usuario fragmentada.

### Visión

Un asistente conversacional en WhatsApp que:
- **Responde** consultas comerciales al instante (precios, disponibilidad, agendar demos)
- **Escala** casos de soporte con contexto (categorizar, crear tickets, notificar equipo)
- **Valida** elegibilidad de licencias y soporte en tiempo real
- Funciona **24/7** en el canal preferido del usuario (WhatsApp)
- Recolecta información que genera **leads cualificados** para comercial

---

## 2. Solución / Propuesta

### Arquitectura en Alto Nivel

```
Usuario WhatsApp
    ↓ (enviá un mensaje)
Meta Cloud API (webhook)
    ↓
DemoWhatsappAgent (FastAPI)
    ├─ Memoria: obtén historial de chat
    ├─ Brain: envía a Gemini con function-calling
    ├─ Tools (16): consulta precio, disponibilidad, agenda cita, crea ticket, etc.
    │   ├─ Servicios externos: Google Calendar, Gmail, EspoCRM, Firebird
    │   └─ Persistencia: Postgres (contactos, ofertas, parámetros, historial)
    └─ Respuesta: devuelve texto a usuario, persiste interacción
```

### Componentes Clave

| Componente | Tecnología | Propósito |
|-----------|-----------|----------|
| **Brain** | Gemini 3.1 Flash Lite | Orquestación conversacional con function-calling automático |
| **Tools** | Python (587 LOC) | 16 herramientas de negocio (consultar, agendar, escalar, validar) |
| **Integración Comercial** | Google Calendar API + Gmail | Agendar citas, enviar confirmaciones |
| **Integración CRM** | EspoCRM REST API | Crear leads, casos, tickets, comentar |
| **Integración Licencias** | Firebird DB | Validar elegibilidad de soporte (demo-only hoy) |
| **Persistencia** | PostgreSQL + asyncpg | Chat history, contactos, ofertas, parámetros |
| **Webhook** | Meta Cloud API | Recibir/enviar mensajes WhatsApp |

### Diferenciadores

1. **Function-calling automático:** Gemini elige qué tool usar automáticamente → experiencia conversacional fluida, no menús
2. **Wrapping implícito de teléfono:** Tools no requieren pasar teléfono explícitamente → LLM no puede alucinar/confundir teléfonos
3. **Historial persistido:** Conversaciones se recuperan → contexto continuo entre sesiones
4. **Escalación inteligente:** Detecta casos sin licencia, reclasifica automáticamente → reduce tiempo de triaje

---

## 3. Objetivos (Goals SMART)

### Objetivos de Negocio (v1.0 Demo)

1. **Reducir turnaround de respuesta comercial**
   - Métrica: Turnaround 24h (email hoy) → 30 segundos (bot)
   - Target: 40% de consultas resueltas sin escalación humana
   - Plazo: Semana 3 (Sprint 1 + 2)

2. **Disponibilidad 24/7 sin operador**
   - Métrica: Uptime 99%, respuesta <30s incluso fuera de horario
   - Target: 0 leads perdidos por "no atender fuera de 9-17h"
   - Plazo: Semana 4 (Sprint 1 + 2 + validación)

3. **Automatizar triaje de soporte**
   - Métrica: 50% de casos pre-categorizados automáticamente (comercial vs. soporte)
   - Target: Reducir carga manual de triaje en 50%
   - Plazo: Semana 4 (Sprint 2 con HU-019)

4. **Capturar leads con contexto**
   - Métrica: 100% de leads que consultaron quedan registrados (hoy: manual, pierde 40%)
   - Target: Comercial recibe daily digest con historial de preguntas
   - Plazo: Semana 4 (Sprint 2 con HU-021)

5. **Validar elegibilidad de licencias en tiempo real**
   - Métrica: 100% de consultas de licencia respondidas sin call a Firebird manual
   - Target: 0 escalaciones por "no sé si tengo soporte vigente"
   - Plazo: Semana 2 (Sprint 1 con HU-012/014)

---

## 3.1. Audiencia / Target User

### Usuarios Finales PRIMARIOS (3 capas)

#### 1. Cliente B2B (Comprador Potencial)
- **Quién:** Empresas buscando software/servicios, personas en rol de decisión técnica/comercial
- **Necesidad:** Obtener información rápido (especialmente fuera de horario comercial) sin esperar email
- **Ubicación:** En WhatsApp (ya lo tienen abierto)
- **Frecuencia:** 1-3 consultas por ciclo de evaluación (días/semanas)

#### 2. Equipo Soporte Interno
- **Quién:** Técnicos que resuelven tickets, manejan escalaciones
- **Necesidad:** Que el bot pre-filtre casos simples, agrupe info, cree tickets automáticamente
- **Beneficio:** Enfocarse en problemas complejos, reducir carga manual de triaje
- **Frecuencia:** Continua (cada vez que usuario escala)

#### 3. Equipo Comercial Interno
- **Quién:** Sales, account executives, business development
- **Necesidad:** Leads cualificados con contexto (qué preguntó, cuándo, urgencia implicada)
- **Beneficio:** Seguimiento automatizado, nunca pierde un lead que consultó pero no cerró
- **Frecuencia:** Diaria (revisar leads capturados ayer)

---

## 4. Beneficios / Valor

### Para Cliente Final (Externo)
| Beneficio | Métrica |
|-----------|---------|
| Respuesta inmediata (no esperar correo) | Turnaround: 24h → 30s |
| Disponible 24/7 (sin horario) | Cobertura: 9-17h → 24/7 |
| Experiencia conversacional (no formularios) | Satisfacción: N/A → NPS +15 (proyectado) |

### Para Equipo Soporte (Interno)
| Beneficio | Métrica |
|-----------|---------|
| 40-50% de casos resuelen automáticamente (precio, disponibilidad, estado licencia) | Reducción carga: TBD |
| Información pre-categorizada (comercial vs. soporte vs. técnico) | Reclasificación: manual → automática |
| Tickets pre-llenados (contexto + contacto) | Creación: 5 min → 10 seg |

### Para Equipo Comercial (Interno)
| Beneficio | Métrica |
|-----------|---------|
| Leads con contexto (qué preguntó, cuándo, urgencia) | Cualificación: manual → automatizada |
| Nunca pierde un lead que consultó fuera de horas | Captura: 60% → 100% (estimado) |
| Follow-up automático después de X horas de inactividad | Velocidad cierre: TBD |

---

## 5. Features / Funcionalidades

### Nivel 1: Consultas Comerciales (Comercial-facing)

| Feature | Tool | Descripción |
|---------|------|------------|
| Consultar precio módulo | `consultar_precio_modulo()` | "¿Cuánto cuesta el módulo X?" → Postgres |
| Consultar disponibilidad agenda | `consultar_disponibilidad_agenda()` | "¿Hay horarios libres el martes?" → Google Calendar |
| Agendar cita/demo | `agendar_cita()` | Gemini elige fecha/hora sugerida, crea evento Google + caso EspoCRM |
| Consultar ofertas activas | `consultar_ofertas_activas()` | "¿Qué promociones hay?" → Postgres |

### Nivel 2: Escalación de Soporte (Soporte-facing)

| Feature | Tool | Descripción |
|---------|------|------------|
| Crear ticket soporte | `crear_ticket_soporte()` | Gemini detecta "necesito help técnico" → abre caso en EspoCRM |
| Consultar estado ticket | `consultar_ticket_soporte()` | "¿Cómo va mi caso?" → EspoCRM |
| Escalar a humano | `escalar_a_humano()` | Crea caso EspoCRM, envía email a equipo, persiste en Postgres |
| Reclasificar caso | `reclasificar_caso_sin_licencia()` | Detecta "sin licencia" → cambia prioridad, notifica comercial |

### Nivel 3: Gestión de Licencias (Soporte + Comercial-facing)

| Feature | Tool | Descripción |
|---------|------|------------|
| Consultar licencia | `consultar_licencia()` | Valida si teléfono tiene licencia vigente en Firebird |
| Determinar módulos accesibles | Lógica en `agendar_cita()` | Si sin_licencia → no puede agendar, sugerir renovación |
| Registrar cliente | `registrar_cliente()` | Marca como cliente confirmado (Postgres + EspoCRM) |

### Nivel 4: Backend / No-tool Features

| Feature | Descripción |
|---------|------------|
| Historial de chat persistido | Recupera últimas 50 mensajes de usuario |
| Inactividad checker | Cada 60s, si sin respuesta >5min → check-in; >10min → cierre graceful |
| Validación de firma Meta | HMAC SHA256 en webhook |
| Parámetros configurables | Horarios, ofertas, textos — editables sin deploy (NocoDB) |

---

## 5.1. Historias de Usuario (Alto Nivel)

| Rol | Historia | Beneficio |
|-----|----------|-----------|
| **Cliente B2B externo** | Quiero consultar precio y disponibilidad sin esperar email/llamada | Decisión rápida, sin fricción |
| **Cliente B2B externo** | Quiero agendar demo en un slot disponible desde WhatsApp | Conversación natural, sin formulario |
| **Cliente potencial** | Quiero validar si tengo licencia vigente y qué soporte incluye | Confianza antes de contactar comercial |
| **Equipo Soporte** | Quiero recibir escalaciones con contexto completo (qué preguntó el usuario) | Resolver más rápido sin contexto perdido |
| **Equipo Comercial** | Quiero ser notificado de nuevos leads con su historial de preguntas | Seguimiento informado sin esperar |

---

## 5.2. Casos de Uso (UC)

### UC-001: Cliente Consulta Precio Fuera de Horas
**Rol:** Cliente B2B externo  
**Escenario:** Sábado 20:30, necesita saber cuánto cuesta módulo X antes de reunion lunes  
**Flujo:**
1. Usuario envía "¿Cuánto cuesta el módulo Premium?"
2. Bot (Gemini) reconoce intención: `consultar_precio(modulo="Premium")`
3. Bot devuelve "$500/mes, 5 usuarios incluidos"
4. Usuario decide sin esperar email

### UC-002: Soporte Recibe Escalación con Contexto
**Rol:** Equipo Soporte interno  
**Escenario:** Usuario reporta "No puedo hacer login", bot escala  
**Flujo:**
1. Bot detecta intención soporte, crea ticket EspoCRM
2. Bot adjunta historial (qué preguntó antes, cuándo se registró)
3. Soporte abre ticket, ve contexto, responde en <10min (vs. hoy: leyendo emails, 2h)

### UC-003: Comercial Sigue Lead que Consultó Ayer
**Rol:** Equipo Comercial interno  
**Escenario:** Lunes mañana, revisar leads de fin de semana  
**Flujo:**
1. Comercial recibe daily digest: "3 leads nuevos ayer"
2. Abre lead #1: "Preguntó por módulo Enterprise, disponibilidad demo"
3. Comercial contacta directo (sin perder contexto), cierra en 24h (vs. hoy: 3+ días)

### UC-004: Usuario Valida Elegibilidad de Licencia
**Rol:** Cliente con licencia vigente o expirada  
**Escenario:** Usuario intenta acceder a feature, no sabe si tiene soporte  
**Flujo:**
1. Usuario pregunta "¿Puedo agendar demo si mi licencia vence el 15/7?"
2. Bot (sin intervención humana) consulta Firebird: "Licencia vigente, soporte hasta 15/7"
3. Bot responde con módulos accesibles + aviso "Renovar antes de 15/7"

### UC-005: Usuario Agenda Demo sin Formulario
**Rol:** Cliente B2B, decisor técnico  
**Escenario:** Conversación natural, user dice "Quiero ver cómo funciona el módulo X"  
**Flujo:**
1. User: "¿Puedo agendar una demo del módulo Enterprise?"
2. Bot: "Claro, te muestro slots disponibles. ¿Preferís hoy 15:00 o mañana 10:00?"
3. User: "Mañana 10:00"
4. Bot: "Listo, evento creado. Te llega email con link Zoom + contexto de tu consulta"

---

## 5.3. Diseño y Experiencia de Usuario (UX)

### Principios de Diseño

- **Conversational-first:** Respuestas en lenguaje natural, sin menús JSON
- **Graceful degradation:** Si falla Gemini, devolver fallback legible (no crash)
- **Trust by auditability:** Decisiones high-stakes (escalación, validación de licencia) registradas en audit log visible en EspoCRM
- **Context awareness:** Bot retiene historial de chat (últimas 50 mensajes) para evitar repetición

### Interfaz

- **Medios:** Solo texto en v1 (emoji permitido); v1.1 → botones, carruseles
- **Velocidad target:** <30seg respuesta user-facing (incl. Gemini + tool calls)
- **Error messaging:** Usuario siempre sabe por qué falló ("No tengo esa info documentada" vs. silencio)
- **Cierre graceful:** Cuando usuario dice "chao" → bot detecta y archiva conversación

### Accesibilidad

- Respuestas sin jerga técnica
- Confirmación explícita antes de comprometer (ej. "¿Confirmas demo el 15/7 15:00?")
- Audit trail en EspoCRM para que Soporte pueda leer qué sucedió

---

## 5.4. Criterios de Aceptación (Nivel Producto)

Checklist de verificación post-release:

- ✅ Webhook Meta recibe y procesa mensajes sin lag (latencia <500ms visible al usuario)
- ✅ Consultas comerciales (precio, incluye, ofertas) devuelven datos frescos (actualización diaria)
- ✅ Agendar cita crea evento Google Calendar real + envía confirmación email al usuario
- ✅ Validación de licencia es precisa: sin_licencia → verdadero si vencida, falso si vigente
- ✅ Escalación crea ticket en EspoCRM + notifica a Soporte + muestra ticket ID al usuario
- ✅ Historial de chat visible en EspoCRM para Soporte (no solo en BD)
- ✅ Si Gemini falla (timeout, error de API) → fallback sin crash ("Disculpa, no puedo responder ahora")
- ✅ Bot cierra conversación cuando detecta "chao" / "gracias" / variantes (no deja colgada)
- ✅ Inactividad >10min → cierre automático + archiva historial
- ✅ Audit log completo: quién preguntó qué, timestamp, qué decisión tomó el bot (alto-stakes)

---

## 6. Criterios de Éxito

### Métricas de Negocio

| Métrica | Target v1 | Target v1.1 |
|---------|-----------|------------|
| **Cobertura:** % de consultas respondidas por bot (vs. escaladas) | 40% | 60% |
| **Velocidad:** Tiempo promedio de respuesta | <30 seg | <10 seg |
| **Conversión:** Consultas → leads calificados | 25% | 40% |
| **Disponibilidad:** Uptime de bot | 99% | 99.9% |
| **Satisfacción usuario:** NPS (Net Promoter Score) | TBD | >30 |

### Métricas Técnicas (Quality Gates)

| Métrica | Target v1 |
|---------|-----------|
| Test coverage (unit + integration) | 60% |
| Error rate (API 5xx / total requests) | <1% |
| P99 latency (Gemini call + tool execution) | <3s |
| Chat history recovery time (after restart) | <100ms |

---

## 7. Requisitos Técnicos

### Stack de Desarrollo y Selección

| Capa | Tecnología | Por qué |
|-----|-----------|--------|
| **LLM Orquestación** | Gemini 3.1 Flash Lite | Function-calling automático, latencia <2s, costo razonable para demo v1 |
| **Backend** | FastAPI + asyncpg | Async-first, integración natural con webhooks Meta, performance <30ms para solicitudes internas |
| **Persistencia** | PostgreSQL 14+ | ACID, jsonb para chat history, soporte nativo de full-text search |
| **Integración Comercial** | Google Calendar API v3, Gmail v1 | OAuth2, no reinventar rueda, licencia de Google ya asumida |
| **Integración CRM** | EspoCRM REST API 8.x | CRM existente en demo, compatibilidad demostrada con Firebird backend |
| **Base Licencias** | Firebird 3.0 (demo) | Existente en repositorio; migración a producción TBD |
| **Webhooks** | Meta Cloud API (WhatsApp) | Única interface WhatsApp soportada; HMAC SHA256 para validación |
| **Admin UI** | NocoDB | Gestión parámetros sin deploy; no crítico para bot core |

### No-Funcionales Obligatorios

| Atributo | Requisito | Medición | Rationale |
|----------|-----------|----------|-----------|
| **Performance** | P99 <3s (Gemini call + tool execution) | APM instrumentation (OpenTelemetry) | Bot debe responder dentro de tolerancia WhatsApp (~30s visible, <3s ideal) |
| **Disponibilidad** | Uptime 99% v1, 99.9% v1.1+ | Prometheus + alertas en P1 | Servicio debe ser suficientemente confiable para producción demo |
| **Seguridad** | Rate limiting 3-tier (global/IP/user), input validation 100%, secrets no en logs, audit logging en high-stakes tools | Load tests + security tests + log scanning | Proteger contra abuso, inyección, fuga de credenciales, vulnerabilidad a auditoria |
| **Observabilidad** | Logs estructurados (JSON), trazas distribuidas end-to-end, alertas P1 <15min | Datadog/CloudWatch/Prometheus | Debuggeo eficiente, incident response rápido |
| **Escalabilidad** | Soportar 100 concurrentes (v1), 1000+ (v1.1) con event loop async | Load testing con Locust | Base de usuarios crece; no regresar por throttling |

### Integraciones Externas

| Servicio | Autenticación | Rate Limit | Fallback |
|----------|---------------|-----------|----------|
| **Gemini API** | API Key (GOOGLE_GEMINI_KEY) | 100 QPM (pricing tier) | Respuesta pregrabada ("Disculpa, no puedo responder ahora") + retry exponencial |
| **Google Calendar** | OAuth2 (GOOGLE_OAUTH_TOKEN) | 1000 req/100s | Graceful error, email manual de confirmación |
| **Gmail** | OAuth2 (mismo token) | 100 msg/día (demo) | Retry + queue, alertar admin |
| **Meta Cloud API** | Webhook token (META_WEBHOOK_VERIFY_TOKEN) | 100 msg/seg (según tier) | Drop silencioso (log), no reintentar (evitar duplicate) |
| **EspoCRM** | Basic auth (ESPOCRM_USER:ESPOCRM_PASSWORD) | Ninguno declarado (demo) | Retry 3x, queue para sincronización eventual |
| **Firebird** | Native auth (FIREBIRD_USER/PASS) | Ninguno | Default a "sin_licencia", notificar admin |

### Layers y Responsabilidades

- **Layer 1 (Deterministic):** `tools.py` (function implementations), `brain.py` (prompt building) — decisiones + lógica de negocio, sin alucinaciones
- **Layer 2 (External/AI):** Gemini LLM, Google APIs, EspoCRM, Firebird — servicios cuya salida no es determinista
- **Layer 3 (Infrastructure):** PostgreSQL, logging, rate limiting, encryption — soporte transversal

### Datos Sensibles (PII Regulada)

| Dato | Ubicación | Protección | Retención |
|-----|----------|-----------|-----------|
| Teléfono WhatsApp | PostgreSQL (users.phone) | Encriptación en reposo (AES-256) | Mientras cliente activo |
| Tokens OAuth (Google) | Disk (token.json) + env (GOOGLE_OAUTH_TOKEN) | Encriptación en reposo, no en logs | Regenerar cada 3 meses |
| Credenciales BD | Env vars (DATABASE_URL, FIREBIRD_*) | Encriptación en reposo, scrubbing en logs | Rotación cada 6 meses |
| Chat history | PostgreSQL (chats.messages) | Encriptación en reposo | 90 días (archivado luego) |
| Audit trail (high-stakes) | PostgreSQL (audit_logs table) | Encriptación en reposo, inmutable | 2 años (compliance) |

### Decisiones de Diseño Técnico Clave

1. **Function-calling automático (Gemini):** El LLM elige qué tool usar → evita that teléfono se alucine en prompt de usuario
2. **Wrapping implícito de teléfono:** Tools internamente inyectan el teléfono desde contexto webhook → LLM nunca lo ve como parámetro
3. **Async-first (asyncpg + FastAPI):** Webhooks Meta son bloqueos IO, no CPU-bound → async libera threads para manejo de picos
4. **Persistencia de chat en Postgres:** Recuperación rápida, integración con audit logging, backups ACID nativas
5. **Graceful degradation:** Fallo de Gemini → fallback, fallo de Google Calendar → error legible + retry, nunca crash silencioso
6. **Audit logging obligatorio en high-stakes tools:** `escalar_a_humano()`, `agendar_cita()`, `reclasificar_caso()`, `consultar_licencia()` → cada invocación loguea usuario, timestamp, input, output, resultado

---

## 8. Restricciones / Out of Scope

### Restricciones v1 (In Scope, pero con limitaciones conocidas)

1. **WhatsApp only:** No Telegram, SMS, web yet
2. **Mocks:**
   - Firebird: Datos demo (no producción)
   - EspoCRM: Instancia demo (no productiva)
   - NocoDB: UI de administración, no parte de bot
3. **Auth:** Implícita por teléfono WhatsApp (no user/password)
4. **Media:** Solo texto, sin imágenes/archivos/botones interactivos
5. **Escalación:** Humano debe verificar antes de agendar cita en Google Calendar

### Out of Scope (v1.0 — Fase 1 Demo)

**Diferidas a v1.1:**
- [ ] Security Hardening (EP-003): Rate limiting, input validation, audit logging, encryption at rest
- [ ] RAG Backend (EP-004): Búsqueda semántica, casos de uso, preguntas técnicas
- [ ] Go-to-Market (PRD §8): Estrategia de lanzamiento, posicionamiento, gobernanza

### Out of Scope (v1.1+)

- [ ] Bi-directional sync con Salesforce (solo EspoCRM v1)
- [ ] Llamadas de voz en WhatsApp
- [ ] Rich media (carruseles, botones, archivos)
- [ ] Múltiples idiomas (solo español v1)
- [ ] Mobile app nativa (WhatsApp es interface v1)
- [ ] Analytics dashboard (solo logs, sin UI v1)
- [ ] Multi-canal (Telegram, SMS)

---

## 9. Roadmap / Timeline

### Fase 0: Validación (2-3 semanas) — ✅ COMPLETADO

- Reverse engineering de código existente
- Grafo de dependencias (156 nodos, 5 comunidades)
- Identificación de deuda técnica

### Fase 1: Demo Funcional (4-5 semanas) — ⏳ EN MARCHA

| Épica | Duración | Scope v1.0 |
|-------|----------|-----------|
| **EP-001:** Test Suite + Features Negocio (generar_respuesta + hub nodes) | 3 sem | ✅ ACTIVA |
| **EP-002:** Error Handling & Resilience | 1 sem | ✅ ACTIVA (HU-019 triaje) |
| **EP-005:** Deployment + Disponibilidad 24/7 | 2 sem | ✅ ACTIVA (HU-003, HU-021) |
| **EP-003:** Security Hardening (rate limit, audit logging) | 2 sem | 🔄 v1.1 (deferred) |
| **EP-004:** RAG Backend (buscar_en_conocimiento) | 3 sem | 🔄 v1.1 (deferred) |

### Fase 2: Production Deployment (2-3 semanas) — 📅 SIGUIENTE

| Tarea | Duración |
|-------|----------|
| Gunicorn + reverse proxy (Nginx) | 1 sem |
| Monitoring (Prometheus/CloudWatch) | 1 sem |
| CI/CD (GitHub Actions) | 1 sem |

### Fase 3: Scale-Out (post-v1.0)

- Multi-channel (Telegram, SMS)
- Analytics dashboard
- Bi-directional Salesforce sync
- Rich media support

---

## 10. Riesgos

| Riesgo | Impacto | Probabilidad | Mitigación |
|--------|---------|------------|----------|
| Gemini API latency > 3s → mal UX | Alto | Media | Circuit breaker + fallback (frase pre-grabada) |
| Google Calendar unavailable → no se agenda cita | Alto | Baja | Graceful error message + email confirmación manual |
| Firebird down → bot deniega acceso (conservador) | Medio | Baja | Default a "sin_licencia", notificar admin |
| EspoCRM auth error → ticket no se crea | Medio | Media | Retry + queue, alertar Soporte |
| Rate limiting attack → bot se atasca | Alto | Media | IP rate limiting + per-user limits |
| Chat history corrupted → usuario pierde contexto | Medio | Baja | DB backups diarios + read-only failover |

### Riesgos Arquitectónicos (Grafo)

| Chokepoint | Betweenness | Riesgo | Mitigación |
|-----------|------------|--------|-----------|
| `generar_respuesta()` (brain.py) | 0.000565 | Si falla → conversación se detiene | Tests unitarios + E2E |
| `escalar_a_humano()` (degree 32) | 0.000336 | Cambio aquí → 32+ dependencias afectadas | Refactor en sub-functions + tests |
| `obtener_historial()` (memory.py) | 0.000415 | Si falla → no hay contexto previo | Redundancia de BD + retry |

---

## 11. Dependencias

### Externas (Producción esperada post-v1)

- **Google Calendar API v3** — Agendar eventos, leer disponibilidad
- **Google Gmail API v1** — Enviar notificaciones
- **Meta Cloud API (WhatsApp)** — Recibir/enviar mensajes, webhooks
- **EspoCRM 8.x** — CRM productivo (hoy demo)
- **Firebird 3.0** — Licencias BD productiva (hoy demo)
- **PostgreSQL 14+** — Persistencia de chat + datos

### Internas (Este proyecto)

- **Gemini API key** — LLM orchestration (asumido: presupuesto Google)
- **OAuth tokens** — Google Calendar, Gmail (almacenados vía token.json)
- **Postgres credentials** — DATABASE_URL, permiso de lectura/escritura
- **Meta webhook token** — META_API_TOKEN, META_WEBHOOK_VERIFY_TOKEN

### Infraestructura

- **Docker + docker-compose** — Para development + staging
- **Cloudflare Quick Tunnel** — Exposición pública del webhook (interim)
- **Nginx reverse proxy** — Para producción
- **GitHub** — CI/CD + source control

---

## 12. Métricas & KPIs

### KPIs de Producto (Medibles)

| KPI | Baseline | Target v1.0 | Medición |
|-----|----------|------------|----------|
| **Consultas/día** | 0 | 50-100 | Google Analytics + logs |
| **% Resueltas automáticamente** | 0% | 40% | EspoCRM case categorization |
| **Avg response time** | N/A | <500ms | APM (Datadog/New Relic) |
| **Error rate** | N/A | <1% | Prometheus + alertas |
| **Leads capturados** | 0 | 10-20/mes | CRM field: source = "bot" |
| **NPS** | N/A | >0 (cualquier cosa > 0 es victoria) | Post-chat survey (opt-in) |

### KPIs de Ingeniería (Quality)

| KPI | Target v1.0 |
|-----|------------|
| Test coverage (unit + integration) | 60% minimum |
| Code review SLA | 24h |
| Incident response time (P1) | <15 min |
| MTTR (mean time to recovery) | <1h |

---

## 13. Inversión / Recursos

### Equipo Requerido

| Rol | Horas/semana | Duración (Fase 1) | Dedicación |
|-----|-------------|------------------|-----------|
| Tech Lead (IngKevin95) | 20h | 6 sem | 50% |
| Backend Engineer | 40h | 6 sem | 100% |
| QA Engineer | 20h | 6 sem | 50% |
| Product Manager | 10h | 6 sem | 25% |
| DevOps (part-time) | 10h | 6 sem | 25% |

**Total:** ~5 FTE × 6 semanas = 30 person-weeks

### Costo de Infraestructura (Estimado)

| Servicio | Costo/mes | Justificación |
|----------|-----------|------------|
| Google APIs (Calendar + Gmail) | $20-50 | Pay-as-you-go, usage-based |
| Meta Cloud API (WhatsApp) | $50-200 | Per-message billing + webhook |
| PostgreSQL (Managed, 2vCPU + 10GB) | $100-150 | AWS RDS o similar |
| Docker/Gunicorn (app server) | $50-100 | 2-4 containers |
| EspoCRM hosting (demo) | $0 (internal Docker) | Puede ser on-prem o managed |
| Monitoring + Logging | $100-200 | Datadog basic tier |
| **Total** | **$320-700/mes** | Pre-scale (pre-1000 consultas/día) |

### Timing Crítico

- **Bloqueador de Fase 1:** Test Suite + Security (4 semanas) — no avanza a deploy sin esto
- **Bloqueador de Fase 2:** Production hardening — 2-3 semanas antes de GO
- **Fecha Go/No-Go:** Fin de Fase 1 (semana 6) — decisión de escalada a producción

---

## Appendix A: Fases Secuenciales (Para Automatización)

### Fase 1: Testing & Hardening

```json
{
  "phase": "testing_and_hardening",
  "duration": "4-6 semanas",
  "gates": [
    {
      "gate": "dor",
      "requirements": [
        "EP-01 especificada (test suite scope)",
        "Grafo de dependencias compilado (✅ done)",
        "Deuda técnica mapeada (✅ done)"
      ]
    },
    {
      "gate": "dod",
      "requirements": [
        "Test coverage ≥60%",
        "All hub nodes tested (escalar_a_humano, agendar_cita)",
        "Bridge node (generar_respuesta) con tests E2E",
        "Security tests (HMAC, input validation)",
        "CI/CD pipeline verde"
      ]
    }
  ],
  "epics": [
    { "id": "EP-01", "title": "Test Suite Foundation", "weeks": 2 },
    { "id": "EP-02", "title": "Error Handling & Resilience", "weeks": 2 },
    { "id": "EP-03", "title": "Security Hardening", "weeks": 2 },
    { "id": "EP-04", "title": "RAG Backend", "weeks": 3, "optional": true }
  ]
}
```

---

## Notas de Revisión

<!-- TODO: Confirmar con Equipo Comercial detalle de flujos de lead nurturing -->
<!-- TODO: Validar con Equipo Soporte: % actual de casos que podrían automatizarse (asumimos 40%) -->
<!-- TODO: Presupuesto Google APIs: ¿está autorizado? Límite mensual? -->
<!-- TODO: Firebird + EspoCRM: ¿cuándo pasan de demo a producción? Timing? -->
<!-- TODO: Métricas v1.1: definir NPS survey + implementación -->

---

**Documento generado:** 2026-07-12  
**Próximo paso:** `/factory:epicas` (descomponer PRD en épicas)  
**Revisor asignado:** (pendiente `/factory:revisar`)
