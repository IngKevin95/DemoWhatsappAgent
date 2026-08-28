# DemoCorp AI Agent (WhatsApp & Web) 🚀

Un bot conversacional avanzado para WhatsApp diseñado para automatizar la atención comercial, soporte técnico y gestión de clientes de una empresa tipo ERP o de Software.

Este proyecto ha sido diseñado como una **aplicación de grado de producción**, demostrando las mejores prácticas en el ecosistema actual de Inteligencia Artificial utilizando **LangChain, LangGraph y RAG (Retrieval-Augmented Generation)** con bases de datos vectoriales.

## 🌟 Características Principales (Portfolio Highlights)

- **Arquitectura Multi-Herramienta (Tool Calling):** El agente usa el paradigma ReAct a través de `LangGraph` para orquestar de manera autónoma más de 12 herramientas.
- **RAG con PGVector:** Ingesta de archivos PDF (Manuales, Fichas Técnicas) y Markdown (Base de Conocimiento) utilizando `GoogleGenerativeAIEmbeddings` hacia una base de datos PostgreSQL vectorizada.
- **Circuit Breakers y Resiliencia:** Lógica robusta de protección contra caídas de la API del LLM, fallos de red o tiempos de espera excedidos (`agent/middleware/circuit_breaker.py`).
- **Integraciones Nativas:**
  - **Google Calendar:** Verifica disponibilidad de agentes en tiempo real y agenda citas cruzando franjas horarias.
  - **EspoCRM / Firebird:** Escalado de leads, creación de casos y validación de licencias activas interactuando con bases de datos legadas y CRMs vía API REST.
  - **Prometheus Metrics:** Trazabilidad completa de errores, uso de herramientas, latencias (Yellow Zone Logging) y contadores exportados en `/metrics`.

## 🛠️ Stack Tecnológico

- **Core AI:** `langchain`, `langgraph`, `langchain-google-genai` (Modelo: Gemini 1.5 Flash).
- **RAG & Vectores:** `langchain-postgres`, `psycopg-pool`, `pgvector`, `PyPDF`.
- **Backend:** `FastAPI`, `Uvicorn`, `SQLAlchemy`, `asyncpg`.
- **Infraestructura:** Docker & Docker Compose.
- **Administración DB:** `NocoDB` (interfaz No-Code sobre PostgreSQL para que el equipo comercial edite ofertas/parámetros en tiempo real).

## 🚀 Guía de Inicio Rápido (Local Setup)

### 1. Clonar e Instalar
```bash
git clone https://github.com/tu-usuario/DemoWhatsappAgent.git
cd DemoWhatsappAgent
python -m venv .venv
# Activar entorno (Windows)
.venv\Scripts\activate 
# Instalar dependencias
pip install -r requirements.txt
```

### 2. Variables de Entorno
Crea un archivo `.env` en la raíz (puedes basarte en `.env.example`):
```env
GEMINI_API_KEY=tu_api_key_de_google_aqui
DATABASE_URL=postgresql://demobot:demobot@localhost:5441/demobot
META_ACCESS_TOKEN=tu_token_de_whatsapp
META_PHONE_NUMBER_ID=tu_phone_id
```

### 3. Levantar Infraestructura y Base de Datos (Docker)
Levanta PostgreSQL (que ahora incluye la extensión `pgvector` nativa) y NocoDB:
```bash
docker compose up -d postgres nocodb
```

### 4. Ingestar la Base de Conocimiento (RAG)
Para que el bot pueda leer los manuales (PDFs) y los markdowns corporativos:
```bash
python scripts/ingest_rag.py
```
*(Esto procesará los textos, creará embeddings y los insertará en PGVector).*

### 5. Iniciar la Aplicación
```bash
# Run server locally (FastAPI webhook on port 8000)
python -m uvicorn agent.main:app --reload
```
Accede a http://localhost:8000/docs para ver el OpenAPI (Swagger UI) de la aplicación.

## 🧪 Testing

La plataforma cuenta con un robusto framework de pruebas con Pytest:
```bash
# Correr tests unitarios
pytest tests/unit/ -v

# Correr tests con reporte de cobertura
pytest --cov=agent --cov-report=html
```

## 🏗️ Arquitectura Interna

- `agent/main.py`: Punto de entrada FastAPI, middleware de seguridad, webhooks de Meta.
- `agent/brain.py`: Núcleo conversacional. Configura el LLM (`ChatGoogleGenerativeAI`), conecta las Tools con LangChain y ejecuta el grafo reactivo con `create_react_agent`.
- `agent/tools.py`: Implementación de más de 12 funciones de negocio documentadas de forma estricta (exigencia de LangChain) conectadas al RAG o APIs externas.
- `scripts/ingest_rag.py`: Tubería ETL para procesamiento e inserción de datos no estructurados en la base vectorial PGVector.
