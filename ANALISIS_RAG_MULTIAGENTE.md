# Análisis: Estado actual vs. RAG vs. Multi-agente (DemoAgent)

Fecha: 2026-07-10

## 0. Advertencia sobre capacidad

Los números de "peticiones/clientes simultáneos" de este documento son **estimaciones direccionales**, no benchmarks medidos. La capacidad real depende más de la arquitectura de despliegue (workers, conexiones DB, si las llamadas a Firebird/EspoCRM/Google corren bloqueando el event loop o en thread pool) que de si usas RAG o multi-agente. Antes de vender un número de capacidad garantizado, correr una prueba de carga real (`locust`/`k6`) contra un ambiente igual a producción.

**Limitante técnica ya presente hoy, independiente de RAG/multi-agente**: las tools en `agent/tools.py` (consultas a Firebird, EspoCRM vía `httpx` sync, Google APIs) son llamadas síncronas invocadas desde un webhook async. Si no corren en threadpool (`run_in_executor` o similar), cada una bloquea el event loop de Uvicorn mientras espera respuesta — esto limita la concurrencia real mucho antes de que Gemini o el vector store sean el cuello de botella.

---

## 1. Estado actual (LLM Chatbot + tools, sin RAG)

**Cómo funciona:** Gemini con function calling decide qué tool llamar; `buscar_en_knowledge` hace match literal de encabezado markdown.

**Capacidad estimada:** en una sola instancia (1 proceso Uvicorn, workers por defecto), del orden de **10-30 conversaciones simultáneas** antes de que la latencia se degrade notablemente — acotado principalmente por: latencia de Gemini (1-3s por respuesta), rate limits de la API de Gemini, y el bloqueo síncrono mencionado arriba. Escala horizontalmente agregando instancias/workers detrás de un load balancer, sin cambios de arquitectura.

**Límites (no de capacidad, de calidad de respuesta):**
- Solo encuentra información si el título del bloque markdown coincide con lo que Gemini infiere como "módulo".
- No sirve para manuales largos/no estructurados (ver conversación previa) — o no encuentra nada, o devuelve el documento completo sin filtrar.
- No cruza información entre documentos.

**Pros:**
- Ya construido, cero costo adicional, cero deuda técnica nueva.
- Arquitectura simple: menos piezas que puedan fallar.
- Latencia mínima (solo 1 llamada a Gemini por mensaje, más las tools que ya tenía).

**Contras:**
- No cumple el objetivo de "intuir información de manuales no estructurados" (confirmado en el análisis previo).
- Calidad de respuesta cae rápido a medida que la base de conocimiento crece o se vuelve menos estructurada.

**Costo:** $0 adicional — ya está pagado dentro de la base construida.
**Horas:** 0h adicionales.
**Precio de venta:** $0 (ya incluido en el proyecto entregado).

---

## 2. RAG (pgvector + embeddings)

**Cómo funciona:** manuales troceados en chunks → embeddings (Gemini embedding API) → guardados en `pgvector` (extensión sobre el Postgres que ya existe) → en cada pregunta, se embebe la consulta, se buscan los chunks más similares, y esos chunks (no el documento completo) se pasan a Gemini para redactar la respuesta.

**Capacidad estimada:** prácticamente **igual al estado actual**. El paso adicional es una llamada a embeddings (rápida, decenas-cientos de ms) + una consulta vectorial en Postgres (rápida a la escala de unos pocos manuales, <50-100ms con pgvector bien indexado con HNSW/IVFFlat). No mueve el cuello de botella real (Gemini + I/O síncrono de las otras integraciones). Mismo orden de magnitud: **10-30 conversaciones simultáneas por instancia**, mismo camino de escalamiento horizontal.

**Límites:**
- Calidad de retrieval depende de qué tan bien se trocean los manuales — chunking mal hecho = recuperar el pedazo equivocado, y el error es silencioso (no hay excepción, solo una respuesta mediocre).
- Requiere mantenimiento: reindexar cuando cambian los manuales.
- Nuevo punto de falla: si la API de embeddings falla, hay que degradar con gracia (ej. caer al lookup por header actual).

**Pros:**
- Resuelve el objetivo real: inferencia semántica sobre manuales no estructurados.
- No agrega vendor nuevo (pgvector vive en el Postgres existente).
- Costo marginal por consulta bajísimo (embeddings son baratos).
- No degrada capacidad de forma perceptible frente a lo que hay hoy.

**Contras:**
- Costo de construcción no trivial (pipeline + troceo de manuales).
- Calidad requiere afinamiento (tamaño de chunk, top-k, umbral de similitud) — no es "conectar y listo".
- Rompe parcialmente el modelo de "pago único sin mantenimiento": crecer o actualizar manuales implica reindexar.

**Costo interno de desarrollo (tarifa base ~50.000 COP/hora):**
- Pipeline (chunking + embeddings + tabla pgvector + integración en `tools.py`, sin LangChain): **40-80 horas** → 2.000.000 - 4.000.000 COP de costo interno.
- Troceo/preparación de manuales existentes (PDF seleccionable, texto limpio): **1-2 horas por manual** limpio, **3-5+ horas** si el PDF está mal formateado (tablas, columnas) — costo aparte, depende de cuántos manuales y su extensión (aún no definido).

**Precio de venta al cliente (pago único, margen ~50% sobre costo interno):**
- Pipeline RAG completo: **3.000.000 - 6.000.000 COP**.
- Troceo/preparación por manual: **90.000 - 150.000 COP/manual** limpio, **250.000 - 400.000 COP/manual** si requiere reformateo.

---

## 3. Multi-agente (orquestador + agentes especializados)

**Cómo funciona:** un LLM orquestador recibe la consulta y la delega a agentes especializados (Retrieval Agent = RAG, CRM Agent = EspoCRM, Soporte Agent = Firebird, Agenda Agent = Calendar/Gmail, Escalamiento Agent), coordinados por un protocolo que reparte tareas y junta resultados antes de responder al usuario.

**Capacidad estimada:** **notablemente menor por instancia** que las dos opciones anteriores, a igual infraestructura. Cada turno de conversación puede disparar 2-4 llamadas a LLM (orquestador + 1-3 agentes) en vez de 1 — esto multiplica la latencia percibida (aunque se paralelicen los agentes independientes) y, más crítico, consume la cuota/rate-limit de la API de Gemini varias veces más rápido que el modelo actual. A igual límite de requests-por-minuto de la API, la capacidad efectiva de conversaciones simultáneas puede caer a una fracción (orden de **la mitad o menos** frente a las opciones 1 y 2), a menos que se aumente el tier de la API o se paralelice agresivamente.

**Límites:**
- Complejidad operativa alta: más piezas, más superficie de fallo, más difícil de debuggear (¿cuál agente falló? ¿el protocolo se colgó esperando a uno?).
- Necesita observabilidad dedicada (trazas por agente) para ser mantenible.
- No resuelve nada que el modelo actual + RAG no resuelva ya para el alcance de DemoAgent (WhatsApp de un solo hilo, intención mayormente única por mensaje).

**Pros:**
- Permite paralelismo real entre dominios independientes (ej. consultar Firebird y EspoCRM al mismo tiempo).
- Cada dominio (retrieval, CRM, soporte) se puede mejorar/tunear por separado sin arriesgar romper los demás.
- Reusable si mañana se necesitan los mismos agentes especializados en otro canal/producto.

**Contras:**
- Sobre-ingeniería clara para el alcance actual (12 módulos, un puñado de integraciones, un solo canal de WhatsApp).
- Más costoso, más lento por turno, más frágil operativamente.
- El modelo de "pago único + garantía de 1 mes" es más riesgoso aquí: más piezas nuevas = más probabilidad de bugs que aparecen después del arranque limpio (ver lección ya documentada sobre verificación post-deploy).

**Costo interno de desarrollo (tarifa base ~50.000 COP/hora):**
- Estimado: **120-240 horas** → 6.000.000 - 12.000.000 COP de costo interno — incluye rediseñar `tools.py` en agentes separados, lógica de orquestación/planning, protocolo de coordinación, y pruebas de integración adicionales por la complejidad nueva.

**Precio de venta al cliente (pago único, margen ~50% sobre costo interno):**
- **9.000.000 - 18.000.000 COP**.
- Probable necesidad de presupuesto de mantenimiento recurrente (monitoreo, ajustes de coordinación) que no encaja limpio en "pago único sin soporte continuo" — cobrar aparte o dejar explícito en el contrato que no incluye soporte post-garantía más allá del mes estándar.

---

## 4. Resumen comparativo

| | Estado actual | RAG (pgvector) | Multi-agente |
|---|---|---|---|
| Resuelve "intuir info de manuales no estructurados" | No | Sí | Sí (vía su Retrieval Agent = RAG) |
| Capacidad simultánea (misma infra) | Base (~10-30/instancia) | ~Igual a la base | Menor (~50% o menos) |
| Complejidad operativa | Baja | Media | Alta |
| Encaja en pago único + garantía 1 mes | Sí | Sí, con matices (reindexado) | Difícil, riesgo de mantenimiento continuo |
| Horas estimadas | 0h | 40-80h (+ troceo por manual) | 120-240h |
| Costo interno (COP) | $0 | 2M - 4M + troceo por manual | 6M - 12M |
| Precio de venta (COP) | $0 | 3M - 6M + troceo por manual | 9M - 18M |
| Justificado para alcance actual de DemoAgent | Ya cubierto | **Sí, si el objetivo es manuales reales** | No — sobre-ingeniería para este caso |

## 5. Recomendación

Para el objetivo declarado (agente que infiere respuestas desde manuales de usuario no estructurados): **implementar RAG con pgvector**, no multi-agente. El multi-agente resuelve un problema de coordinación entre múltiples dominios con lógica condicional compleja que DemoAgent no tiene hoy — agregarlo ahora es costo y riesgo sin beneficio proporcional. Si en el futuro el bot necesita encadenar rutinariamente varios sistemas con lógica condicional entre pasos, o reusar agentes especializados en otros canales, ahí se reevalúa.

---

## 6. Plan detallado para llevar cada arquitectura a producción

Parte de la base ya vendida/entregada (~10M COP): 12 módulos, WhatsApp webhook, Calendar/Gmail, EspoCRM, Firebird, historial en Postgres. Cada plan abajo es **incremental** sobre esa base, no un rehacer.

### 6.1 Estado actual — endurecer lo ya construido (gaps conocidos, no funcionalidad nueva)

Esto no es "nuevo requerimiento", es cerrar deuda ya identificada para que el sistema actual sea sólido en producción real, independiente de si se agrega RAG o no.

| # | Tarea | Detalle | Horas |
|---|---|---|---|
| 1 | Sacar I/O síncrono del event loop | `agent/tools.py` llama Firebird (`firebird.driver`), EspoCRM (`httpx` sync) y Google APIs de forma bloqueante dentro de un webhook async — envolver en `run_in_executor`/`asyncio.to_thread` para no tumbar la concurrencia real | 4-8h |
| 2 | Corregir `liberar_agente` | `agent/main.py:181` usa `proveedor.enviar_mensaje` directo en vez de `enviar_mensaje_seguro` — un fallo ahí no queda contenido | 0.5-1h |
| 3 | Suite de pruebas automatizadas | Ya documentada en memoria previa: `TestClient`, mock de HMAC/`generar_respuesta`/`proveedor.enviar_mensaje`, cubrir desde saludo simple hasta escalamiento+cola+cita | 16-24h |
| 4 | Logging estructurado + verificación post-deploy | Ya hay logger básico; agregar niveles claros y correlación por `telefono` para poder diagnosticar sin `--tail=100` a ciegas (lección ya aprendida en este proyecto) | 4-8h |
| 5 | Manejo de rate limit de Meta/Gemini | Backoff/reintento simple si la API de WhatsApp o Gemini responde 429 | 2-4h |

**Total:** 26-45h → **Costo interno:** 1.3M - 2.25M COP → **Precio de venta:** ~2M - 3.4M COP.
**Verificación:** correr la suite completa en CI o localmente, generar tráfico real de prueba contra `/webhook` (no solo revisar logs de arranque), confirmar que `liberar_agente` no revienta si Meta responde error.

### 6.2 RAG — plan de construcción

Requiere 6.1 hecho primero (ítem 1 en particular: si las tools ya bloquean el event loop, agregar otra llamada async de embeddings no ayuda si el resto sigue bloqueando).

| # | Tarea | Detalle | Horas |
|---|---|---|---|
| 1 | Habilitar `pgvector` | Extensión sobre el Postgres existente, migración para tabla `documento_chunks` (embedding, texto, manual, sección, página) | 2-4h |
| 2 | Extracción de texto de PDFs | `pypdf`/`pdfplumber` (PDF seleccionable, ya confirmado que no hay escaneados) + limpieza básica (headers/footers repetidos, saltos de página) | 4-8h |
| 3 | Chunking | Trocear ~300-500 tokens con overlap, conservando metadata de sección/página para citar la fuente | 6-10h |
| 4 | Pipeline de ingestión (`scripts/ingest_manual.py`) | Script idempotente: PDF → chunks → embeddings (Gemini) → upsert en `pgvector`; reindexa si el manual cambió | 6-10h |
| 5 | Tool `buscar_en_manual_rag` | Nueva tool en `agent/tools.py`/`brain.py`: embebe la pregunta, busca top-k por similitud coseno, pasa los chunks a Gemini para redactar la respuesta — reemplaza `buscar_en_knowledge` para manuales | 8-12h |
| 6 | Degradación si falla la API de embeddings | Fallback al lookup actual por header en vez de romper la respuesta | 2-4h |
| 7 | Prueba de calidad de retrieval | Set de preguntas reales por manual, medir si recupera el chunk correcto, ajustar tamaño de chunk/top-k/umbral | 8-16h |
| 8 | Vectorización real de cada manual | Ejecutar el pipeline del ítem 4 contra los manuales reales — cotizado aparte por manual (ver sección 2) | según # de manuales |

**Total pipeline (sin contar troceo por manual):** 36-64h → alinea con el rango 40-80h ya cotizado (incluye margen para imprevistos de PDFs mal formateados).
**Verificación:** correr el set de preguntas de prueba del ítem 7 y confirmar que las respuestas citan información real de los manuales, no alucinaciones; probar el fallback del ítem 6 apagando la API de embeddings a propósito.

### 6.3 Multi-agente — plan de construcción

**Depende de 6.2 completo** — el Retrieval Agent del esquema multi-agente *es* el RAG. No tiene sentido construir el orquestador sin tener antes el agente de conocimiento funcionando solo.

| # | Tarea | Detalle | Horas |
|---|---|---|---|
| 1 | Protocolo de coordinación | Definir contratos de entrada/salida entre orquestador y cada agente (qué recibe, qué devuelve, cómo reporta error) | 8-16h |
| 2 | Refactor de `brain.py` a Orchestrator | Hoy `brain.py` llama tools directo; pasa a decidir a qué agente delega y componer la respuesta final | 16-24h |
| 3 | Agentes especializados como módulos separados | Retrieval (RAG ya construido), CRM (EspoCRM), Soporte/Licencias (Firebird), Agenda (Calendar/Gmail), Escalamiento — cada uno con su propio prompt acotado y tools | 24-40h |
| 4 | Memory compartida | Extender `agent/memory.py` si hace falta que los agentes compartan contexto de la conversación en curso | 4-8h |
| 5 | Planning / descomposición multi-paso | Lógica para que el orquestador rompa un pedido en sub-tareas y las reparta | 8-16h |
| 6 | Observabilidad por agente | Trazas de qué agente respondió qué y en cuánto tiempo — sin esto es indebuggeable en producción | 8-16h |
| 7 | Manejo de fallos parciales | Si un agente falla o no responde a tiempo, el orquestador debe degradar la respuesta, no colgarse | 8-12h |
| 8 | Pruebas de integración multi-agente | Escenarios donde se coordinan 2+ agentes en un mismo turno | 16-24h |

**Total orquestación (sin contar el RAG de 6.2):** 92-156h.
**Total del proyecto completo (RAG + multi-agente):** 128-220h → alinea con el rango 120-240h ya cotizado.
**Verificación:** escenarios de prueba donde falla un agente a propósito (timeout simulado) y confirmar que el orquestador degrada en vez de colgar toda la conversación; medir latencia real por turno con 2+ agentes activos.

### 6.4 Orden recomendado si se hacen las tres

1. 6.1 (endurecer base) — se beneficia cualquier camino futuro, y ya es deuda identificada hoy.
2. 6.2 (RAG) — resuelve el objetivo real declarado por el cliente (manuales no estructurados).
3. 6.3 (multi-agente) — solo si en el futuro aparecen las condiciones ya discutidas (cadenas de 3+ sistemas con lógica condicional, necesidad de tuning independiente por dominio). No construir en paralelo a 6.2; depende de él.
