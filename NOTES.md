# Notas de configuración WhatsApp Cloud API

## Webhook no llegaba: suscripción app↔WABA faltante

Síntoma: Callback URL correcta, Verify Token correcto, campo `messages` marcado como "Suscrito" en la UI de la app — pero ningún POST real llegaba al servidor (solo el GET de verificación). El panel de "Test" de Meta sí mostraba payloads, pero eso es simulado, no viene por el Callback URL real.

Causa: existen dos niveles de suscripción independientes:

1. **Campos del webhook** (UI: Configurar Webhooks → toggle `messages`): le dice a la *app* qué tipos de evento le interesan.
2. **`subscribed_apps` de la WABA**: le dice a Meta *qué app* debe recibir los eventos de esa WhatsApp Business Account específica. Sin esto, aunque el campo esté suscrito, la WABA no le envía nada a tu app.

En este caso la WABA (`WABA_ID`) estaba suscrita solo a una app ajena default de Meta ("WA DevX Webhook Events 1P App"), no a la app propia.

## Fix

```bash
curl -X POST "https://graph.facebook.com/v25.0/{WABA_ID}/subscribed_apps" \
  -H "Authorization: Bearer {ACCESS_TOKEN}"
```

Verificar con:

```bash
curl "https://graph.facebook.com/v25.0/{WABA_ID}/subscribed_apps" \
  -H "Authorization: Bearer {ACCESS_TOKEN}"
```

Debe listar tu app en `data[].whatsapp_business_api_data.id`.

## Otras notas del setup

- Número de prueba de Meta necesita destinatarios agregados como "tester" (Paso 1 → sección "Envía un mensaje desde tu número de prueba" → Destinatario). Se verifica con código enviado por WhatsApp. No requiere SIM ni número de negocio real.
- Publicar la app (App Review + Business Verification) NO es necesario para pruebas con testers — solo para producción real con usuarios externos.
- Windows/git-bash: `pkill -f "uvicorn agent.main"` no mata el proceso de forma confiable. Usar:
  ```bash
  netstat -ano | grep ":8000" | grep LISTENING
  taskkill //PID <pid> //F
  ```
