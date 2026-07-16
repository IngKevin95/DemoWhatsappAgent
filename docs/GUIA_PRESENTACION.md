# Guía de presentación — Tableros DemoWhatsappAgent

> Cifras a la fecha de esta corrida (6 meses de operación simulada). Los números de negocio son estables; los técnicos (Monitoreo) son en vivo y varían.

## Audiencia y estrategia

Tenés dos públicos en la sala:
- **Un ingeniero de sistemas sólido** → va a cuestionar el *cómo*: origen del dato, latencia, arquitectura, integridad. Ganás credibilidad mostrando que los números salen de la BD real y que sabés dónde están los límites.
- **Personas funcionales de cada área** (comercial, soporte, operación) → les importa el *qué significa para mi trabajo*. Hablales en su lenguaje: leads, tiempos de respuesta, carga del equipo.

**Regla de oro:** abrí con negocio (engancha a todos), cerrá con lo técnico (para el ingeniero). Nunca empieces por Prometheus.

---

## Estructura general (15–20 min)

1. **Apertura (2 min)** — el problema y la solución en una frase.
2. **Central / Visión 360 (3 min)** — la foto completa, para orientar.
3. **Recorrido por área (8 min)** — Comercial → Soporte → Operación → Conversacional.
4. **Monitoreo técnico (3 min)** — para el ingeniero, cierre de confianza.
5. **Cierre + preguntas (4 min)**.

### Diálogo de apertura

> "Este es el bot de WhatsApp de SysPlus operando. Atiende consultas comerciales, soporte y licencias, y cuando hace falta escala a una persona. Lo que van a ver son **6 meses de operación** medidos en tiempo real: 2.568 personas atendidas, más de 10.000 mensajes, y todo el equipo de soporte trabajando sobre los mismos datos. No son mockups: cada número sale de la base de datos de producción."

---

## 1. Central (Visión 360)

**Para qué es:** la foto ejecutiva. Se abre acá para dar contexto antes de bajar al detalle.

**Números actuales:**
- Negocio: **2.568 contactos**, **347 clientes**, **conversión 23,9%**, **2.568 conversaciones**.
- Soporte: **841 radicados**, **11 en backlog**, **resolución media 4 h**.

**Diálogo:**
> "Arriba, el negocio: 2.568 personas escribieron, de las cuales el 23,9% terminó siendo cliente. Abajo, soporte: 841 casos escalados a un humano, de los cuales solo 11 siguen abiertos. Con esta pantalla, un gerente sabe en 10 segundos si el mes va bien. Desde acá pueden saltar a cualquier área con los botones de arriba."

**Mensaje clave:** una sola pantalla, decisión en segundos.

---

## 2. Comercial y Ventas

**Números actuales:**
- **2.568 contactos** · **1.105 leads** · **347 clientes** · **conversión 23,9%**.
- **2 ofertas vigentes** hoy. Catálogo de 13 módulos (de $350.000 a $700.000/mes).

**Diálogo:**
> "El embudo: de cada 100 personas que escriben, unas 24 se vuelven clientes. Los 1.105 leads son oportunidades abiertas que el equipo comercial puede trabajar. La gráfica de barras muestra la captación día a día en los 6 meses: se ve el ritmo del negocio. Y acá abajo, las ofertas vigentes hoy y el catálogo con precios: el bot responde con esta misma información."

**Para el área comercial:** "¿Ven la distribución por sector? Ahí está dónde están cerrando: les dice en qué industrias enfocar el esfuerzo."

**Mensaje clave:** el bot no solo informa, alimenta el pipeline comercial.

---

## 3. Soporte y Escalamientos

**Números actuales:**
- **841 radicados** · **830 resueltos** · **11 en backlog**.
- **Resolución media: 4 h** · **espera en cola P50: ~7,7 min**.
- **Solo 8,9% sin sincronizar al CRM** (91% se registra automático en EspoCRM).

**Diálogo:**
> "Cada vez que el bot no puede resolver algo, crea un radicado y escala a una persona. En 6 meses: 841 casos, 830 ya cerrados, 11 pendientes. El tiempo medio de resolución es 4 horas, y la gente espera en cola menos de 8 minutos en la mitad de los casos. Lo importante: el 91% de estos casos se registró solo en el CRM, sin que nadie los cargue a mano."

**Para el área soporte:** "La tabla de abajo es su backlog en vivo: los 11 casos abiertos, ordenados por antigüedad, con el agente asignado. Es su lista de trabajo."

**Mensaje clave:** trazabilidad total y menos carga manual.

---

## 4. Operación y Agentes

**Números actuales:**
- **10 agentes activos** (5 comercial + 5 soporte) · **11 en backlog**.
- Carga y tiempo de resolución **repartidos por agente** (barras).

**Diálogo:**
> "Acá se ve el equipo. 10 agentes activos, la carga de casos repartida entre ellos, y cuánto tarda cada uno en resolver. Si pasan el mouse sobre una barra, ven el nombre completo. Esto sirve para balancear: si alguien está saturado o alguien resuelve mucho más lento, salta a la vista."

**Para el área operación / líderes:** "La tabla de cobertura horaria muestra quién está disponible y en qué franja. Útil para planear turnos."

**Mensaje clave:** gestión del equipo con datos, no por intuición.

---

## 5. Conversacional y Volumen

**Números actuales:**
- **10.244 mensajes** · **2.568 conversaciones** · **4 mensajes por conversación**.
- **Consentimiento de datos: 66,2%** · canales WhatsApp (Meta) y Telegram · 8 ciudades.

**Diálogo:**
> "El pulso de la conversación: más de 10.000 mensajes, un promedio de 4 por conversación (el bot resuelve rápido, no marea). El 66% de los contactos autorizó el tratamiento de datos: eso es cumplimiento, importante para legal. Y vemos de qué ciudades y por qué canal llegan."

**Mensaje clave:** volumen sano y cumplimiento medible.

---

## 6. Monitoreo (en vivo) — para el ingeniero

**Números actuales (en vivo, varían):**
- **Uptime ~17 h** · **error 5xx: 0%** · **latencia P95 ~2,2 s**.
- **Salud de dependencias:** EspoCRM degradado (0,5), Firebird / Gemini / Postgres OK (1).

**Diálogo:**
> "Esta es la capa técnica en tiempo real. El servicio está arriba, cero errores de servidor, y la latencia P95 está en torno a 2 segundos. Lo más útil: el semáforo de dependencias. Ahora mismo EspoCRM aparece degradado, lo cual explica por qué un pequeño porcentaje de casos no sincroniza al CRM al instante. Esto es observabilidad real, no inventada."

**Mensaje clave:** el sistema se auto-monitorea y sabemos dónde falla antes que el usuario.

---

## Preguntas probables y cómo responderlas

### Del ingeniero de sistemas (técnicas)

**"¿De dónde salen estos datos?"**
> Los de negocio, de PostgreSQL (esquema `sysbot`) vía SQL directo en cada panel. Los técnicos, de Prometheus que scrapea el endpoint `/metrics` del bot. Grafana solo lee; no hay capa intermedia que transforme.

**"¿Por qué el monitoreo no muestra 6 meses como el negocio?"**
> Porque Prometheus solo almacena lo que scrapea en tiempo real; no acepta datos con fecha pasada. El negocio sí lo sembramos hacia atrás en SQL. La retención de Prometheus está en 1 año, así el histórico real se acumula operando. Es una diferencia de naturaleza entre una base transaccional y una serie temporal.

**"¿Qué pasa si se cae una dependencia, por ejemplo EspoCRM?"**
> El bot sigue operando; el caso se crea igual en Postgres y queda marcado como no sincronizado (hoy 8,9%). Cuando EspoCRM vuelve, se puede reintentar. El panel de dependencias lo muestra degradado en tiempo real.

**"¿Latencia P95 de 2 segundos no es alta?"**
> Es la latencia de los health-checks internos, no de la conversación con el usuario. Aun así es un dato real y medible; si fuera crítico, el panel lo marca en rojo sobre 1s. Es justo el tipo de cosa que este tablero permite vigilar.

**"¿Cómo escala esto? ¿Qué pasa con más volumen?"**
> El bot es stateless sobre Postgres; las métricas de throughput y latencia por endpoint están en el Monitoreo, así que el cuello de botella se ve antes de que sea problema. La retención a 1 año permite análisis de capacidad.

**"¿Los números son reales o simulados?"**
> Los técnicos son 100% reales (operación en vivo). Los de negocio son datos sintéticos de demo, generados con un seed para mostrar cómo se ve a 6 meses; la estructura y las consultas son las de producción.

### Del área Comercial

**"¿Puedo ver los leads concretos, no solo el número?"**
> El tablero muestra agregados; el detalle de cada lead vive en el CRM / NocoDB. Este panel es para leer la tendencia y priorizar.

**"¿La conversión de 23,9% es buena?"**
> Es una cifra sana para un canal conversacional automatizado. Lo valioso es que ahora es medible y se puede mejorar con datos.

### Del área Soporte

**"¿Qué pasa con los 11 casos abiertos?"**
> Están en la tabla de backlog, ordenados por antigüedad y con agente asignado. Es la lista de trabajo pendiente en vivo.

**"¿El 8,9% sin CRM se pierde?"**
> No. El caso existe en la base; solo no llegó a EspoCRM (por la degradación que vimos). Se reintenta cuando el CRM se recupera.

**"¿Los tiempos de resolución son por agente?"**
> Sí, en el tablero de Operación. Permite ver quién necesita apoyo o formación.

### Del área Operación / Liderazgo

**"¿Cómo balanceo la carga del equipo?"**
> Con las barras de carga por agente y tiempo de resolución. Si una barra se dispara, ese agente está saturado. La tabla de cobertura horaria ayuda a planear turnos.

**"¿Cuántos agentes necesito?"**
> El promedio es ~84 casos por agente en 6 meses. Con estos tableros podés proyectar: si el volumen sube X%, ves cuántos agentes hacen falta para mantener las 4 h de resolución.

---

## Cierre

> "En resumen: el bot no es una caja negra. Cada interacción deja un rastro medible, cada área tiene su tablero, y la capa técnica se auto-vigila. Comercial ve su pipeline, soporte ve su backlog, operación ve su equipo, y sistemas ve la salud del servicio. Todo sobre la misma fuente de verdad. ¿Qué les gustaría profundizar?"

---

### Tips de entrega

- **No leas los números, contá la historia detrás.** "830 de 841 resueltos" → "casi todo lo que entra, se cierra".
- Cuando el ingeniero pregunte algo técnico, **respondé y devolvé la pelota a negocio** para no perder a los funcionales.
- Si un panel técnico está en rojo (latencia, dependencia), **no lo escondas**: mostralo como prueba de que el monitoreo funciona.
- Ten a mano el rango de tiempo: negocio en "Last 6 months", monitoreo en "Last 6 hours".
