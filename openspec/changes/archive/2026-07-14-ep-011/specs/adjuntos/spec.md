# Adjuntos PDF

## MODIFIED Requirements

### Requirement: Descargar documentos adjuntos y enviar PDFs
The system SHALL procesar archivos adjuntos entrantes (`type: document`) y poder enviar adjuntos a los usuarios.

#### Scenario: Enviar PDF de cotización
- **Given** que el LLM decide enviar una cotización
- **When** se ejecuta la herramienta con el archivo PDF
- **Then** se hace una llamada a la API de WhatsApp usando `type: document` y el link/documento correspondiente.
