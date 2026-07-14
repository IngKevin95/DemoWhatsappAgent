# conversacion Specification

## Purpose
TBD - created by archiving change ep-006. Update Purpose after archive.
## Requirements
### Requirement: Entidad Conversacion
El sistema MUST persistir conversaciones ligadas a un radicado y requerir el consentimiento explícito del contacto.
#### Scenario: Asociar y persistir la entidad y el consentimiento
**Given** que el usuario requiere trazabilidad (HU-034 a HU-037)
**When** un contacto envía su primer mensaje
**Then** el sistema abrirá una Conversación asociada al Contacto y requerirá registrar el estado del consentimiento de tratamiento de datos.

