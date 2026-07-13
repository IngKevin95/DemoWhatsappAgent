# Spec: Audit Logging for High-Stakes Tools

## Qué

Registro de auditoría en Postgres para operaciones críticas (escalar, agendar, reclasificar, consultar licencia).

## Dónde

- `agent/middleware/audit_logger.py` (nueva)
- Tabla: `audit_log` en Postgres (creada via migration)
- Aplicado en: `tools.py` (4 funciones high-stakes)

## Por Qué

**Problema actual:**
- Sin trazabilidad: "¿quién escaló este caso y cuándo?"
- Sin evidencia: fallos en compliance/support
- Sin rolling back: no hay forma de revertir cambios
- Sin analytics: no sabemos cuántos casos se escalan por qué motivo

**Solución:**
- Audit trail para escalar_a_humano, agendar_cita, reclasificar_caso, consultar_licencia
- Inmutable (INSERT only)
- Queryable (para compliance, support investigations)

## Schema

```sql
CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY,
  user_phone VARCHAR(20) NOT NULL,
  tool_name VARCHAR(50) NOT NULL,
  action VARCHAR(100) NOT NULL,
  result VARCHAR(20),  -- "success", "failure"
  error_message TEXT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX audit_log_user_phone ON audit_log(user_phone);
CREATE INDEX audit_log_tool_name ON audit_log(tool_name);
CREATE INDEX audit_log_created_at ON audit_log(created_at);
```

## Uso

### 1. escalar_a_humano

```python
@audit_log
def escalar_a_humano(user_phone, case_description, reason=""):
    try:
        case_id = espocrm.create_case(...)
        email_id = gmail.send_email(...)
        
        # Audit log automático vía decorator
        return {"status": "escalated", "case_id": case_id}
    except Exception as e:
        # Audit log con error automático
        raise
```

Audit entry:
```json
{
  "user_phone": "+573001234567",
  "tool_name": "escalar_a_humano",
  "action": "escalation_created",
  "result": "success",
  "metadata": {
    "case_id": 98765,
    "reason": "license_expired",
    "email_sent": true
  },
  "created_at": "2026-07-13T23:40:00Z"
}
```

### 2. agendar_cita

```python
def agendar_cita(user_phone, fecha, hora, motivo):
    audit = AuditLogger("agendar_cita", user_phone)
    
    try:
        event_id = google.calendar.create_event(...)
        sms_id = meta.send_whatsapp(...)
        
        audit.log_success(
            action="appointment_scheduled",
            metadata={
                "event_id": event_id,
                "fecha": fecha,
                "hora": hora,
                "motivo": motivo,
            }
        )
        return {"status": "scheduled", "event_id": event_id}
    except Exception as e:
        audit.log_failure(action="appointment_failed", error=str(e))
        raise
```

### 3. reclasificar_caso (HU-019)

```python
def reclasificar_caso_sin_licencia(case_id, nueva_categoria):
    audit = AuditLogger("reclasificar_caso", get_user_phone())
    
    old_categoria = get_caso(case_id).categoria
    
    update_caso(case_id, categoria=nueva_categoria)
    
    audit.log_success(
        action="case_reclassified",
        metadata={
            "case_id": case_id,
            "old_categoria": old_categoria,
            "new_categoria": nueva_categoria,
        }
    )
```

### 4. consultar_licencia

```python
def consultar_licencia(cliente_id):
    audit = AuditLogger("consultar_licencia", get_user_phone())
    
    try:
        resultado = firebird.query(f"SELECT * FROM LICENCIAS WHERE ID={cliente_id}")
        audit.log_success(
            action="license_queried",
            metadata={
                "cliente_id": cliente_id,
                "status": resultado.get("status"),
            }
        )
        return resultado
    except Exception as e:
        audit.log_failure(action="license_query_failed", error=str(e))
        raise
```

## API

```python
from agent.middleware.audit_logger import AuditLogger, audit_log

# Vía decorator
@audit_log(tool_name="escalar_a_humano")
def mi_funcion(user_phone, ...):
    pass

# Vía contexto
audit = AuditLogger(
    tool_name="agendar_cita",
    user_phone=user_phone,
    trace_id=trace_id,  # opcional, para correlación
)

audit.log_success(
    action="appointment_scheduled",
    metadata={"event_id": 123}
)

audit.log_failure(
    action="failed",
    error="Google API 503"
)
```

## Query Ejemplos

Compliance/Support:

```sql
-- Casos escalados hoy
SELECT COUNT(*) FROM audit_log
WHERE tool_name='escalar_a_humano'
  AND created_at >= NOW() - INTERVAL '1 day'
  AND result='success';

-- Por qué motivo se escalan
SELECT 
  metadata->>'reason' as reason,
  COUNT(*) as count
FROM audit_log
WHERE tool_name='escalar_a_humano'
GROUP BY metadata->>'reason'
ORDER BY count DESC;

-- Auditoría de usuario
SELECT * FROM audit_log
WHERE user_phone='+573001234567'
ORDER BY created_at DESC;

-- Fallos en agendar_cita
SELECT * FROM audit_log
WHERE tool_name='agendar_cita' AND result='failure'
ORDER BY created_at DESC;
```

## Testing

Ver `tests/integration/test_audit_logging.py`:
- ✓ Entrada creada en DB
- ✓ user_phone, tool_name, action, result correctos
- ✓ metadata JSONB parseado
- ✓ Timestamp asignado
- ✓ Timestamp ordering
- ✓ Transacción rollback no pierde audit

## Métricas de Éxito

- Tests: ≥6 casos (integración con DB real)
- Coverage: >85% en audit_logger.py
- Query latency: <100ms (índices)
- Data integrity: 100% (INSERT only)

## Notas

- Audit table es append-only (sin UPDATE, DELETE)
- Retención: mantener 1 año (archivable después)
- Metadata JSONB para flexibilidad futura
- Correlación con logs estructurados vía trace_id
