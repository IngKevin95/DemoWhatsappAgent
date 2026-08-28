# Arquitectura del Sistema

Este documento describe la arquitectura y las decisiones de diseño técnico detrás del **DemoCorp AI Agent**. El sistema evolucionó desde un simple bot transaccional hacia un agente inteligente basado en RAG y frameworks avanzados.

## 1. Resumen de Alto Nivel

El DemoAgent es un asesor virtual para WhatsApp (usando WABA / Meta Cloud API) para una empresa tipo DemoCorp. Utiliza **Gemini** (vía LangChain) como motor de inferencia, **Function Calling** (Tools) para interactuar con bases de datos transaccionales, y un **Pipeline RAG** (vía LangChain PGVector) para contestar consultas técnicas basadas en PDFs corporativos no estructurados. 

La administración de las tablas transaccionales (ofertas, configuración) se delega a **NocoDB**, evitando construir paneles de administración a medida.

## 2. Infraestructura & Servicios (`docker-compose.yml`)

| Servicio   | Imagen/build | Rol |
|------------|--------------|-----|
| `demobot`   | `build: .` (FastAPI + Uvicorn) | API que recibe webhooks de Meta, orquesta el Agente ReAct (LangGraph) y responde por WhatsApp. |
| `postgres` | `pgvector/pgvector:pg16` | Única BD física. Contiene datos de negocio (`modulos`, `ofertas`), el historial conversacional, y la base de datos vectorial de embeddings para RAG (`democorp_knowledge`). |
| `nocodb`   | `nocodb/nocodb:latest` | Interfaz (UI admin tipo Airtable) sobre Postgres que permite a usuarios sin conocimiento técnico editar configuraciones y precios en tiempo real. |
| `seed`     | `build: .` (Corre 1 vez) | Script idempotente: crea esquemas relacionales si faltan y siembra datos iniciales indispensables (`agent.db.SyncSession`). |

## 3. Stack Técnico Detallado

| Pieza | Herramienta | Contexto / Justificación |
|---|---|---|
| **Web Framework** | FastAPI | Async nativo y tipado fuerte, crucial para la latencia en webhooks. |
| **Orquestador LLM** | LangChain / LangGraph | Patrón arquitectónico estandarizado. Permite definir el ciclo "Pensamiento -> Acción -> Observación -> Respuesta" (ReAct) con resiliencia superior a la ejecución cruda de SDKs. |
| **Base Vectorial / RAG** | Langchain-Postgres (`pgvector`) | En lugar de utilizar bases separadas como Pinecone o Chroma, centralizar en Postgres vía `pgvector` disminuye el mantenimiento y simplifica el despliegue Docker. |
| **Embeddings** | `GoogleGenerativeAIEmbeddings` | Generación de vectores asequible y altamente semántica a través de los modelos `embedding-001`. |
| **ORM / DB** | SQLAlchemy 2.0 (Sync/Async) | Dos engines sobre la misma BD: Async (`asyncpg`) para los flujos principales de FastAPI y Sync (`psycopg2`) para la compatibilidad con ciertas herramientas de LangChain y lógica bloqueante. |
| **Resiliencia** | Circuit Breaker (Local) | Envoltorio (Wrapper) que monitoriza los fallos 429 o timeouts de la API del LLM. Si caen en bucle, abre el circuito e inyecta fallbacks estáticos para mantener sano el servicio. |
| **Métricas** | Prometheus | Exposición de `/metrics` al host, con instrumentación dinámica y anotaciones `@_instrument_tool` en el motor de herramientas. |

## 4. Flujo de Información (RAG y Agente)

1. **Ingestión (ETL RAG):** El script `scripts/ingest_rag.py` parsea los directorios `/knowledge` y `/static/pdfs` dividiendo los textos con `RecursiveCharacterTextSplitter`. Luego, guarda los embeddings en la base PostgreSQL (PGVector).
2. **Recepción Webhook:** El mensaje de WhatsApp entra a FastAPI, que sanitiza y valida el payload (Rate Limiting y Firmas Hmac de Meta).
3. **Clasificación Rápida:** Una invocación cero-shot rápida del LLM determina la intención (Soporte, Comercial, Otro).
4. **AgentExecutor Loop:** El mensaje entra al Grafo ReAct de LangGraph. El Agente deduce si debe invocar herramientas (`consultar_ofertas_activas`, `agendar_cita`, o la más importante `buscar_en_knowledge`).
5. **Retrieval Tool:** Si invoca `buscar_en_knowledge`, LangChain convierte la query del LLM a un embedding y extrae los top 4 bloques (Similarity Search k=4) de PGVector.
6. **Respuesta Final:** El agente formatea la respuesta en un tono corporativo y la envía de vuelta vía la API de Graph de WhatsApp.

## 5. Diseño para Fallos (Degradación con Gracia)

El bot está diseñado para nunca fallar de forma ruidosa al cliente final:
- Si el LLM tiene Timeout, el _Circuit Breaker_ devuelve la respuesta fallback: *"Servicio temporalmente inactivo..."* y escala silenciosamente un ticket.
- Si Google Calendar está desautenticado para verificar los horarios libres de un agente de ventas específico, el bot consulta la tabla paramétrica en la base de datos (Ej: `09:00 a 18:00`), asume el riesgo y la agenda allí, alertando internamente al equipo de Infraestructura sin bloquear al usuario.