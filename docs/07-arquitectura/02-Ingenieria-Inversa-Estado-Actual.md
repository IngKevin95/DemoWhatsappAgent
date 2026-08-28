# Ingeniería Inversa: Estado Actual (Fase 1 Demo)

**Fecha:** 2026-07-12  
**Análisis:** Estático de codebase Python (1513 LOC)  
**Nota:** Análisis sin code-review-graph (se refinará con grafo una vez compilado)

---

## 📊 Estadísticas Codebase

| Módulo | LOC | Función |
|--------|-----|---------|
| `agent/tools.py` | 587 | Tools que Gemini invoca (8 fijas + 8 dinámicas por user) |
| `agent/main.py` | 182 | FastAPI webhook, lifecycle, inactividad checker |
| `agent/brain.py` | 174 | Orquestación Gemini, wrapping de tools con telefono |
| `agent/db.py` | 150 | ORM: Contacto, Parametro, Modulo, Oferta, Mensaje |
| `agent/integrations/espocrm.py` | 119 | CRM wrapper: leads, casos, tickets |
| `agent/memory.py` | 90 | Async chat history (Postgres) |
| `agent/integrations/google.py` | 86 | Google Calendar/Gmail OAuth2 |
| `agent/providers/meta.py` | 65 | Meta Cloud API webhook (entry point) |
| `agent/providers/base.py` | 28 | ABC de proveedores (Meta, Twilio future) |
| **Total** | **1513** | **Sistema funcional de bot WhatsApp** |

---

## 🏗️ Arquitectura: Capas & Flujos

### Ingreso (Webhook)

```
Meta Cloud API
    ↓
agent/providers/meta.py::webhook_handler()
    ↓
validar firma, parsear mensaje
    ↓
app.py::@app.post("/webhook")
```

**Módulos:** `agent/providers/meta.py` (65 LOC)

---

### Orquestación

```
main.py::webhook_handler()
    ↓
brain.py::generar_respuesta(telefono, mensaje)
    ↓
[1] Cargar historial (memory.py)
[2] Enviar a Gemini con tools
[3] Gemini elige tool o responde
[4] Ejecutar tool (tools.py)
[5] Guardar respuesta en historial
    ↓
enviar_mensaje_seguro(telefono, respuesta)
    ↓
Meta Cloud API
```

**Módulos clave:**
- `agent/brain.py` — Orquestación + wrapping de tools (174 LOC)
- `agent/memory.py` — Chat history (90 LOC)
- `agent/main.py` — Lifecycle + background tasks (182 LOC)

---

### Tools (Function-Calling)

#### 8 Tools Fijas (Siempre disponibles)

| Tool | Módulo | LOC | Propósito |
|------|--------|-----|----------|
| `buscar_en_knowledge` | tools.py | ~40 | RAG: buscar en base de conocimiento (no implementado aún) |
| `consultar_precio_modulo` | tools.py | ~25 | Precios de módulos desde Postgres |
| `consultar_disponibilidad_agenda` | tools.py | ~35 | Slots libres en Google Calendar |
| `consultar_ticket_soporte` | tools.py | ~30 | Estado de ticket en EspoCRM |
| `consultar_licencia` | tools.py | ~50 | Validar soporte/vigencia en Firebird (demo-only) |
| `crear_tarea` | tools.py | ~25 | Crear tarea en Postgres (uso interno) |
| `consultar_ofertas_activas` | tools.py | ~20 | Ofertas en Postgres |
| `consultar_parametro` | tools.py | ~20 | Parámetros configurables (horarios, etc.) |

#### 8 Tools Dinámicas (Por usuario)

Se crean en `brain.py::_tools_con_telefono(telefono)` para que `telefono` sea implícito:

| Tool | Propósito |
|------|----------|
| `registrar_lead_crm` | Lead comercial → EspoCRM |
| `consultar_estado_cliente` | ¿Cliente, lead, en qué estado? (EspoCRM) |
| `guardar_datos_contacto` | Guardar nombre, empresa, correo en Postgres |
| `agendar_cita` | Google Calendar + crear caso en EspoCRM |
| `crear_ticket_soporte` | Abrir ticket en EspoCRM |
| `escalar_a_humano` | Marcar caso como escalado (EspoCRM + Gmail) |
| `reclasificar_caso_sin_licencia` | Si consultó licencia y es negativa, reescalar a comercial |
| `registrar_cliente` | Marcar como cliente confirmado (Postgres + EspoCRM) |

**Módulo:** `agent/tools.py` (587 LOC)

---

### Integración Gemini

```python
# brain.py
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-3.1-flash-lite"  # Configurable

# Function-calling automático desde docstrings
response = client.models.generate_content(
    contents=messages,
    tools=[TOOL_FUNCTIONS_FIJAS + _tools_con_telefono(telefono)],
    tool_config={"automatic_function_calling": True},
)
```

**Capa:** `agent/brain.py::generar_respuesta()` (invoca `client.generate_content`)

---

### Persistencia

#### Bases de Datos Usadas

| BD | Motor | Tablas | Propósito |
|----|-------|--------|----------|
| **demobot** | Postgres | Contacto, Parametro, Modulo, Oferta, Mensaje | Datos de negocio + historial |
| **nocodb** | Postgres (schema separado) | (Gemelas de demobot) | UI admin (NocoDB) |
| **licencias.fdb** | Firebird 3.0 | LICENCIAS | Validación de soporte (demo-only) |
| **EspoCRM** | Postgres (espocrm_demo DB) | Lead, Case, Account, Opportunity | CRM (demo-only) |

**Módulo ORM:** `agent/db.py` (150 LOC)

```python
class Contacto:
    __tablename__ = 'contacto'
    id, telefono, nombre, empresa, correo, ciudad, fecha_creacion

class Parametro:
    __tablename__ = 'parametro'
    clave, valor  # Key-value de configuración

class Modulo, Oferta, Mensaje:
    # Referencia de datos
```

---

### Historial de Chat

```
agent/memory.py (90 LOC)
├── guardar_mensaje(telefono, role, content)  # Insert en tabla Mensaje
├── obtener_historial(telefono, limit=100)    # SELECT con contexto reciente
├── ultimo_mensaje(telefono)                  # Last message timestamp
├── limpiar_historial(telefono)               # DELETE (cierre de charla)
└── telefonos_con_actividad_reciente()        # Active users (para inactividad check)
```

**Implementación:** Async con `asyncpg` para no bloquear webhook.

---

### Background Tasks

En `main.py::lifespan()`:

```python
async def _revisar_inactividad():
    # Corre cada 60s
    # Si usuario no responde > 5 min: "¿hay algo más?"
    # Si sigue sin responder > 5 min: "Ha sido un gusto"
    # Limpia historial
```

**Propósito:** Auto-cierre de conversaciones inactivas.

---

## 🔌 Integraciones

### Google APIs

**Módulo:** `agent/integrations/google.py` (86 LOC)

```
OAuth2 flow (installed app)
├── token.json (persisted, auto-refresh)
├── Calendar API
│   ├── Listar slots disponibles
│   └── Crear evento
└── Gmail API
    └── Enviar correo de escalación
```

**Tools que lo usan:**
- `consultar_disponibilidad_agenda` → Calendar.freebusy()
- `agendar_cita` → Calendar.events.insert() + create case in EspoCRM
- `escalar_a_humano` → Gmail.send()

---

### EspoCRM

**Módulo:** `agent/integrations/espocrm.py` (119 LOC)

```
REST API (http://espocrm:8081/api/v1)
├── POST /Lead
├── GET /Lead?filter=phone
├── POST /Case
├── GET /Case/{id}
├── PATCH /Case/{id}  (cambiar estado, comentar)
├── POST /Account
└── POST /Opportunity
```

**Implementación:** `requests` sync (no async; EspoCRM API no es apta para concurrencia).

**Tools que lo usan:**
- `registrar_lead_crm`
- `consultar_estado_cliente`
- `agendar_cita` (crear caso)
- `crear_ticket_soporte`
- `escalar_a_humano`
- `reclasificar_caso_sin_licencia`
- `registrar_cliente`

---

### Firebird (Demo Only)

**Consulta de licencias:**

```python
# agent/tools.py::consultar_licencia(telefono)
# Conecta a Firebird, busca en LICENCIAS (tabla)
# Devuelve: con_licencia_con_soporte | con_licencia_sin_soporte | sin_licencia
```

**Degradación:** Si Firebird no responde → devuelve "sin_licencia" (no crashea).

---

## 🔒 Seguridad (Estado Actual)

### Credenciales

| Credencial | Almacenamiento | Riesgo | Status |
|-----------|----------------|--------|--------|
| `.env` (local dev) | Plain text `.env` | Si se commitea → expuesto | ⚠️ En .gitignore, confiar |
| `GOOGLE_APPLICATION_CREDENTIALS` | `/app/credentials.json` (volumen) | Si volumen se filtra | ⚠️ Aceptable demo |
| `GOOGLE_OAUTH_TOKEN` | `token.json` (volumen) | Sin encriptación en filesystem | ⚠️ Aceptable demo |
| `META_API_TOKEN` | `.env` | Plain text | ⚠️ Aceptable demo |
| `DATABASE_URL` | `.env` | Default user `demobot`/`demobot` | ⚠️ Weak credenciales |

### Validaciones

- ✓ Meta webhook: validar firma (HMAC)
- ✓ Gemini tools: validar `telefono` (no confiar en user input)
- ✗ Rate limiting: NO EXISTE (vulnerable a scraping)
- ✗ Chat history encryption: NO (legible en Postgres)
- ✗ Input sanitization: MÍNIMA (confiar en Gemini)

---

## 📈 Funcionalidad Implementada

### ✅ Completado

- [x] Webhook de Meta Cloud API
- [x] Conversación con Gemini (function-calling)
- [x] Historial de chat (Postgres)
- [x] 8 tools fijas (precio, disponibilidad, licencia, etc.)
- [x] 8 tools dinámicas (registrar lead, agendar cita, escalar, etc.)
- [x] Integración Google Calendar/Gmail (OAuth2)
- [x] Integración EspoCRM (REST API)
- [x] Integración Firebird (demo: validar licencias)
- [x] NocoDB (UI admin tipo Airtable)
- [x] Inactividad checker (background task)

### ⚠️ Parcialmente Implementado

- [ ] RAG/Knowledge base (`buscar_en_knowledge` → no tiene backend)
- [ ] Reclasificación de caso sin licencia (tools existe, pero flujo no está probado)
- [ ] Prompt templates (en `config/prompts.yaml`, pero muy genérico)

### ❌ No Implementado

- [ ] Rate limiting (vulnerable hoy)
- [ ] Chat history encryption
- [ ] Proper error handling (fallback respuestas fijas, pero no logging de trazas)
- [ ] Tests (no hay suite de pruebas)
- [ ] Monitoreo/alertas
- [ ] Audit logging (quién hizo qué cuándo)
- [ ] CI/CD pipeline
- [ ] Production hardening (Gunicorn, reverse proxy, TLS, etc.)

---

## 🔧 Refactorización Pendiente

### Deuda Técnica Identificada

| Item | Módulo | Impacto | Dificultad |
|------|--------|--------|-----------|
| **RAG Backend** | tools.py::buscar_en_knowledge | Funcionalidad bloqueada | Media |
| **Error Handling** | tools.py, brain.py | Resiliencia débil | Media |
| **Test Suite** | N/A | Confianza cero en cambios | Alta |
| **Rate Limiting** | main.py | Seguridad | Baja |
| **Input Validation** | tools.py, brain.py | Robustez | Media |
| **Async/Sync Mismatch** | tools.py, espocrm.py | Concurrencia limitada | Media |
| **Logging** | Todos | Debugging imposible en prod | Baja |
| **Config Management** | main.py, brain.py | Variabilidad | Baja |

---

## 📡 Flujos End-to-End (Identificados)

### Flujo 1: Consulta Comercial Simple

```
Usuario: "¿Cuál es el precio de X?"
    ↓
brain.py: generar_respuesta(telefono, "¿Cuál es el precio de X?")
    ↓
Gemini elige tool: consultar_precio_modulo(modulo="X")
    ↓
tools.py: Query Postgres → precio
    ↓
Gemini: "El precio de X es $Y"
    ↓
main.py: enviar_mensaje_seguro(telefono, "El precio...")
```

**Status:** ✅ Funciona

---

### Flujo 2: Agendar Cita (High-Stakes)

```
Usuario: "Quiero agendar una cita el lunes a las 3pm"
    ↓
Gemini elige: agendar_cita(nombre, telefono, motivo, fecha, hora, area)
    ↓
tools.py::agendar_cita():
    [1] consultar_disponibilidad_agenda(fecha, hora)  → Google Calendar
    [2] Si hay slot: crear evento en Google Calendar
    [3] Crear "Case" en EspoCRM
    [4] Guardar en Postgres (Mensaje)
    ↓
Gemini: "Listo, cita agendada para lunes 15 de julio, 3pm"
    ↓
(Opcional) Gmail notifica al usuario
```

**Status:** ⚠️ Funciona pero sin tests. Riesgo: Google Calendar no disponible → falla silenciosa.

---

### Flujo 3: Escalar a Humano (High-Stakes)

```
Usuario: "Necesito hablar con un agente"
    ↓
Gemini elige: escalar_a_humano(nombre, resumen_caso, area)
    ↓
tools.py::escalar_a_humano():
    [1] Crear "Case" en EspoCRM (status "Escalado")
    [2] Enviar correo via Gmail al equipo
    [3] Guardar en Postgres
    ↓
Gemini: "Un agente de soporte te contactará en las próximas 2 horas"
    ↓
(Background) main.py limpia historial tras 5 min de inactividad
```

**Status:** ⚠️ Funciona pero sin audit trail. Riesgo: qué pasó si Gmail falló? No se sabe.

---

### Flujo 4: Validación de Licencia (High-Stakes)

```
Usuario: "¿Qué módulos puedo usar?"
    ↓
Gemini llama: consultar_licencia(telefono)  [implícito]
    ↓
tools.py::consultar_licencia():
    [1] Conecta a Firebird DB
    [2] SELECT desde LICENCIAS (por telefono)
    [3] Devuelve: con_licencia_con_soporte | con_licencia_sin_soporte | sin_licencia
    ↓
Gemini ajusta respuesta según licencia
    ↓
Si sin_licencia: puede escalar a comercial (reclasificar_caso_sin_licencia)
```

**Status:** ⚠️ Lógica existe, flujo no probado end-to-end. Riesgo: Firebird no disponible → degrada a "sin_licencia" (puede ser mal).

---

## 📊 Análisis del Grafo de Dependencias (Code-Review-Graph)

**Compilado:** 2026-07-12 | **156 nodos, 1253 edges, 25 flujos, 5 comunidades detectadas**

### Hub Nodes (Puntos Calientes — Mayor Impacto)

| Nodo | Ubicación | Grado Total | Propósito |
|------|-----------|-------------|----------|
| `escalar_a_humano` | agent/tools.py | 32 | High-stakes decision, usado en múltiples flujos |
| `recibir_webhook` | agent/main.py | 28 | Entry point principal |
| `agendar_cita` | agent/tools.py | 23 | High-stakes, integración triple (Google+EspoCRM+Postgres) |
| `promover_colas` | agent/tools.py | 23 | Orquestación de estados de caso |

**Insight:** Refactores en tools.py (esp. escalar_a_humano, agendar_cita) tienen máximo efecto cascada. Cambios aquí impactan ≥32 dependencias.

### Bridge Nodes (Nodos Arquitectónicos Críticos)

| Nodo | Betweenness | Rol | Criticidad |
|------|------------|-----|-----------|
| `generar_respuesta` | 0.000565 | Puente Webhook→Tools (orquestación Gemini) | **MÁXIMA** |
| `obtener_historial` | 0.000415 | Puente Entrada→Estado (contexto conversación) | Alta |
| `escalar_a_humano` | 0.000336 | Puente Decisión→Acción (desencadena email+CRM) | Alta |

**Insight:** `generar_respuesta` en brain.py es el principal chokepoint arquitectónico. Si falla, toda la conversación se interrumpe. Sin tests dedicados = riesgo crítico.

### Comunidades de Código (5 Identificadas)

| Comunidad | Tamaño | Cohesión | Propósito |
|-----------|--------|----------|----------|
| `agent-consultar` | 66 nodos | 0.087 | **Core:** brain.py, tools.py, main.py, integrations |
| `scripts-demo` | 20 nodos | 0.108 | SQL demo data, backup scripts |
| `integrations-crear` | 19 nodos | 0.174 | Google APIs + EspoCRM adapters |
| `providers-validar` | 14 nodos | 0.161 | Meta Cloud API + webhooks + firma HMAC |
| `tests-check` | 14 nodos | 0.067 | E2E + unit tests |

**Warning:** 19 edges entre `agent-consultar` ↔ `tests-check` → tests fuertemente acoplados a lógica. Es normal pero indica que tests+ código de dominio son inseparables (cambia uno, fallan los otros).

### Flujos Más Profundos (Propagación de Cambios)

| Flujo | Profundidad | Criticidad | Módulos Afectados |
|-------|------------|-----------|-------------------|
| `reclasificar_caso_sin_licencia` | **7 nodos** | 0.37 | tools → brain → EspoCRM → memory |
| `lifespan` | 4 | 0.37 | main → background tasks |
| Google Calendar flows | 3 | 0.45 | tools → integrations |

**Insight:** Cambios a `consultar_licencia` propagarían en 7 lugares (profundidad máxima). Requiere refactor cuidadoso con tests E2E.

---

## 📋 Épicas Priorizadas (Basadas en Grafo)

### EP-01: Test Suite Foundation (BLOCKER CRÍTICO)
**Por qué:** `generar_respuesta` (bridge node crítico) sin tests dedicados. 5 hub nodes sin coverage.
- Unit tests para brain.py::generar_respuesta (wrapper de Gemini)
- Integration tests para los 4 high-stakes tools (escalar, agendar, reclasificar, consultar_licencia)
- E2E test para flujo de licencia completo (profundidad 7)
- **Riesgo actual:** Cambiar any hub node = crash desconocido

### EP-02: Error Handling & Resilience (BLOCKER DE CONFIANZA)
**Por qué:** Profundidad del grafo (7 nodos en flujo de licencia) sin retry/circuit-breaker. Falla en Google Calendar o EspoCRM = cascada.
- Retry logic (exponential backoff) en escalar_a_humano (degree 32)
- Circuit breakers para Google APIs + EspoCRM
- Logging estructurado en bridge nodes (generar_respuesta, obtener_historial)
- Graceful degradation cuando integraciones fallan

### EP-03: Security Hardening (BLOCKER DE PRODUCCIÓN)
**Por qué:** escalar_a_humano (high-stakes, degree 32) sin audit trail. No hay input sanitization en webhook handler (recibir_webhook, degree 28).
- Rate limiting en recibir_webhook (entry point)
- Audit logging en 3 bridge nodes + 4 high-stakes tools
- Input validation en webhook (antes de pasar a generar_respuesta)
- Chat history encryption (memory.py, bridge node)

### EP-04: RAG Backend (BLOQUEADOR DE FUNCIONALIDAD)
**Por qué:** `buscar_en_conocimiento` tool existe pero no tiene backend. Es un hub node que está desconectado.
- Vector store setup (Pinecone/Weaviate)
- Chunking + embedding pipeline
- Retrieval integration en generar_respuesta
- Tests con datos reales

### EP-05: Production Deployment (ÚLTIMO)
**Por qué:** Mitigado por testing + security, pero necesario para scale.
- Gunicorn + reverse proxy (Nginx)
- Health checks en lifespan (flow con 4 nodos)
- Monitoring de hub nodes (escalar_a_humano, agendar_cita)
- CI/CD (GitHub Actions)

---

## 🎯 Cambios Recomendados Inmediatos

1. **Agregar test unitario a `generar_respuesta`** (bridge node crítico, 0 tests)
   - Mock Gemini client
   - Test injection de telefono implícito
   - Impact: protege 28+ dependencias

2. **Refactor de `escalar_a_humano`** para extraer lógica de envío
   - Separar "crear caso" de "enviar email"
   - Reduce grado 32 → dos funciones de grado ~16
   - Impact: reduce blast radius de cambios futuros

3. **Agregar rate limiting en `recibir_webhook`** (entry point, degree 28)
   - Middleware simple (token bucket)
   - Prevent brute force / spam
   - Impact: mueve seguridad hacia adentro

---

**Nota:** Análisis combinado estático + grafo de dependencias. Épicas están priorizadas por criticidad arquitectónica (bridge/hub nodes) + profundidad de propagación (flujos).
