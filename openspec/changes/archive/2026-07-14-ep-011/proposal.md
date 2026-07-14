# Change Proposal: Rich Media & Componentes Interactivos

## Por qué
Actualmente, el DemoWhatsappAgent (v1.0) está limitado a texto plano y botones simples (respuestas interactivas limitadas a Sí/No). En los flujos comerciales, los clientes esperan una experiencia más rica visualmente y con menos fricción (ej. notas de voz en lugar de escribir). Para cumplir con los objetivos comerciales de "Scale-Out" de la Fase 3, es indispensable procesar Media.

## Qué cambia
Se ampliará el proveedor `agent/providers/meta.py` para soportar mensajes de tipo `image`, `document`, y `audio`. Adicionalmente, el agente podrá enviar mensajes estructurados como `carousel templates` y enviar adjuntos PDF desde las herramientas del LLM.
Se añadirá una herramienta `transcribir_audio` que utilizará un proveedor STT para convertir las notas de voz en texto antes de pasarlas a Gemini.

## Capacidades

1. **Enviar carruseles de ofertas:** El bot enviará plantillas interactivas que contienen catálogos (imágenes + botones).
2. **Enviar y recibir adjuntos:** Recepción de documentos PDF y envío de archivos (ej. cotizaciones generadas).
3. **Voice-to-Text:** Transcripción de notas de voz enviadas por el usuario para su interpretación por el LLM.

## Impacto
- **Archivos modificados:** `agent/providers/meta.py` (recepción y envío de media), `agent/tools.py` (nuevas herramientas para envío de catálogos y PDFs), `agent/main.py` (preprocesamiento de audios).
- **Dependencias:** Requiere configurar la descarga de media usando la URL de Meta Graph API y enviar archivos hacia allá. Podría requerirse un nuevo SDK/Librería para STT (ej. `openai-whisper` o una llamada a la API de Google/OpenAI STT).

## Trazabilidad
- **Épica:** EP-011
- **Historias de Usuario:**
  - HU-048
  - HU-049
  - HU-050
