# Guía de Dashboards Grafana — DemoWhatsappAgent

Explicación panel por panel. Dos fuentes de datos:
- **PostgreSQL** (`demobot`): datos de negocio, se llenan con el seed y el uso real.
- **Prometheus**: métricas técnicas en vivo; requieren que el bot esté corriendo y scrapeando.

Rango temporal por defecto: negocio `now-6M`, técnicos `now-6h` (ajustable arriba a la derecha).

---

## 1. DemoBot Central (Visión 360)

Tablero ejecutivo. Tres filas (Negocio / Soporte / Salud técnica) + links de navegación por tag a los demás.

| Panel | Qué arroja | Fuente / cálculo |
|---|---|---|
| Contactos (rango) | Cuántas personas escribieron al bot en el rango | `count(contactos)` por `creado_en` |
| Clientes | Contactos ya convertidos en cliente | `clientes` donde `tipo='cliente'` |
| Conversión (%) | % de leads+clientes que llegaron a cliente | `clientes cliente / total clientes` |
| Conversaciones | Sesiones de conversación abiertas en el rango | `count(conversaciones)` |
| Nuevos leads/clientes por día | Barras apiladas diarias: leads vs clientes nuevos | `clientes` agrupado por día |
| Radicados (rango) | Escalamientos a humano generados | `count(radicados)` |
| Backlog abierto | Radicados aún sin resolver (verde/naranja/rojo) | `radicados` estado ≠ resuelto |
| Tiempo medio resolución (h) | Promedio de horas entre escalar y resolver | `avg(resuelto_en - creado_en)` |
| Escalamientos por área | Torta comercial vs soporte | `radicados` join `areas` |
| Radicados creados vs resueltos/día | Dos líneas: entrada vs salida de casos | `radicados` por `creado_en` y `resuelto_en` |
| Uptime | Segundos que lleva vivo el servicio | Prometheus `demobot_uptime_seconds` |
| Conversaciones activas (live) | Conversaciones en curso ahora | `demobot_active_conversations` |
| Error 5xx (%) | % de requests HTTP con error de servidor | `rate(http_requests_total{5xx}) / total` |
| Latencia P95 | 95% de requests responden bajo este tiempo | `histogram_quantile(0.95, ...)` |
| Salud de dependencias | Línea de estado por dependencia (Gemini, Google, CRM, Firebird) | `demobot_dependency_health` (1=ok, 0.5=degradado, 0=caído) |

---

## 2. DemoBot Comercial y Ventas  (PostgreSQL)

| Panel | Qué arroja | Cálculo |
|---|---|---|
| Contactos totales | Volumen de personas alcanzadas | `count(contactos)` |
| Leads | Prospectos sin cerrar | `clientes tipo='lead'` |
| Clientes | Cerrados | `clientes tipo='cliente'` |
| Tasa de conversión (%) | Eficiencia comercial | `cliente / total` |
| Nuevos leads/clientes por día | Tendencia de captación (barras apiladas) | `clientes` por día |
| Distribución Leads vs Clientes | Proporción de la cartera | torta `clientes.tipo` |
| Solicitudes por tipo | Naturaleza de la demanda (comercial/soporte/info) | `conversaciones.tipo_solicitud` |
| Clientes por sector | En qué industrias estás vendiendo | `clientes.sector_empresa` |
| Tamaño de empresa (empleados) | Perfil de tamaño de la cartera | `clientes.empleados_empresa` |
| Catálogo de módulos | Tabla de productos y precio mensual | `modulos` ordenado por precio |
| Ofertas activas hoy | Promociones vigentes en la fecha actual | `ofertas` activas y dentro de vigencia |

---

## 3. DemoBot Soporte y Escalamientos  (PostgreSQL)

| Panel | Qué arroja | Cálculo |
|---|---|---|
| Radicados en el rango | Total de escalamientos generados | `count(radicados)` |
| Resueltos | Casos cerrados | estado='resuelto' |
| Abiertos (backlog) | Casos pendientes | estado ≠ resuelto |
| Tiempo medio de resolución (h) | Cuánto tarda soporte en cerrar | `avg(resuelto_en - creado_en)` |
| Radicados creados vs resueltos/día | Salud del flujo: ¿entra más de lo que sale? | series por día |
| Radicados por estado | Torta escalado / en_cola / resuelto | `radicados.estado` |
| Radicados por área | Carga comercial vs soporte | join `areas` |
| Distribución tiempo de resolución (P50/P90/P95) | Percentiles en horas: la mayoría vs los peores casos | `percentile_cont` sobre horas |
| Tiempo de espera en cola (P50/P95) | Cuánto espera el usuario antes de ser atendido | `conversaciones.duracion_espera_seg` |
| Modo de escalamiento | Conectado (mismo hilo) vs notificación | `radicados.modo` |
| Carga por agente | Radicados atendidos por cada persona | join `agentes` |
| Motivo de cierre | Cerró el usuario o fue por inactividad | `conversaciones.motivo_cierre` |
| Sincronización CRM | Radicados sin `crm_case_id` (huérfanos, rojo si >0) | `crm_case_id IS NULL` |
| Backlog abierto (tabla) | Lista de casos sin resolver con horas abiertas | `radicados` estado≠resuelto |

> Nota: en el seed sintético `crm_case_id` queda vacío, así que "Sincronización CRM" marcará todos en rojo. Con uso real se llena al crear el caso en EspoCRM.

---

## 4. DemoBot Operación y Agentes  (PostgreSQL)

| Panel | Qué arroja | Cálculo |
|---|---|---|
| Agentes activos | Personas disponibles para atender | `agentes.activo` |
| Ocupados ahora | Agentes atendiendo a alguien en este momento | `contactos.atendido_por` distinto |
| Radicados en backlog | Casos pendientes globales | estado≠resuelto |
| Radicados/agente (promedio) | Carga media por agente en el rango | radicados / agentes activos |
| Agentes por área | Distribución del equipo | `agentes` join `areas` |
| Carga por agente | Ranking de radicados atendidos | join `agentes` |
| Tiempo medio de resolución por agente (h) | Quién cierra más rápido | `avg` por agente |
| Cobertura horaria y estado | Tabla: horario, teléfono, activo/inactivo por agente | `agentes` join `areas` |

---

## 5. DemoBot Conversacional y Volumen  (PostgreSQL)

| Panel | Qué arroja | Cálculo |
|---|---|---|
| Mensajes totales | Volumen de mensajes intercambiados | `count(mensajes)` |
| Conversaciones | Sesiones totales | `count(conversaciones)` |
| Mensajes / conversación (prom.) | Profundidad media del diálogo | mensajes / conversaciones |
| Consentimiento de datos (%) | % de contactos que autorizaron tratamiento (compliance) | `contactos.consentimiento_datos` |
| Mensajes por día (user vs assistant) | Volumen diario partido por rol | `mensajes.role` por día |
| Conversaciones por canal | Meta (WhatsApp) vs Telegram | `contactos.canal` |
| Estado de conversaciones | Abiertas vs cerradas | `conversaciones.estado` |
| Contactos por ciudad | Distribución geográfica | `contactos.ciudad` |
| Conversaciones por día | Tendencia de volumen | series por día |

---

## 6. DemoBot Monitoreo (en vivo)  (Prometheus)

Consolida la salud técnica en tiempo real. Rango por defecto `now-6h` (no 6 meses: ver nota abajo).

| Panel | Qué arroja | Métrica |
|---|---|---|
| Uptime | Tiempo vivo del proceso | `demobot_uptime_seconds` |
| Conversaciones activas | En curso ahora | `demobot_active_conversations` |
| Tasa de error 5xx (%) | Salud de la API | 5xx / total |
| Latencia P95 | 95% responde bajo este tiempo | `histogram_quantile(0.95,...)` |
| Salud de dependencias | Estado en el tiempo por dependencia (espocrm/firebird/gemini/postgres) | `demobot_dependency_health` (1=ok, 0.5=degradado, 0=caído) |
| Throughput por endpoint | Qué rutas reciben más tráfico | `sum by(endpoint)(rate(...))` |
| Latencia P50/P95/P99 | Percentiles: típico, cola, peor caso | 3 series de `histogram_quantile` |
| Requests por status | Barras apiladas 2xx/4xx/5xx | `sum by(status)(rate(...))` |

**Cómo leer percentiles:** P50 = mediana (experiencia típica); P95/P99 = los casos más lentos. Si P99 se dispara pero P50 no, hay casos puntuales lentos, no un problema general.

---

## Por qué el monitoreo es "en vivo" y no de 6 meses

Este dashboard lee de **Prometheus**, que solo almacena lo que scrapea en tiempo real — no acepta datos con fecha pasada (a diferencia del negocio, que sembramos hacia atrás en PostgreSQL con SQL). Por eso muestra la operación **desde el arranque del servicio**, no 6 meses. La retención está configurada en **1 año** (`--storage.tsdb.retention.time=1y`), así el histórico real se preserva a medida que el bot opera. Se eliminaron los dashboards separados de Salud/API/Tools (y sus paneles vacíos por falta de tráfico) para consolidar solo lo que aporta valor con datos reales.
