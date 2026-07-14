# Voice-to-Text

## MODIFIED Requirements

### Requirement: Transcripción de audios (Voice-to-Text)
The system SHALL descargar el archivo de audio cuando llegue un webhook de `type: audio`, transcribirlo y enviar el texto resultante al LLM.

#### Scenario: Recibir una nota de voz
- **Given** un mensaje de voz enviado por el usuario
- **When** el webhook lo recibe
- **Then** el agente lo descarga, lo procesa usando STT, y el texto resultante se envía a Gemini como si fuera un texto escrito.
