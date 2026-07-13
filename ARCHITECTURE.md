# Arquitectura

## Resumen

SysBot: asesor virtual de WhatsApp (WABA/Meta Cloud API) para SysPlus, con
Gemini como motor conversacional, function-calling contra Postgres/Google
APIs, y NocoDB como panel admin para que comerciales editen precios/ofertas
sin tocar código.

## Servicios (dev, `docker-compose.yml`)

| Servicio   | Imagen/build | Rol |
|------------|--------------|-----|
| `sysbot`   | `build: .` (FastAPI + Uvicorn) | API que recibe webhook de Meta, orquesta Gemini, responde por WhatsApp. Puerto host `8000`. |
| `postgres` | `postgres:16` | Única BD física. Contiene datos de negocio (`modulos`, `ofertas`, `parametros`, `mensajes`) y la metadata interna de NocoDB (BD separada `nocodb` en el mismo motor). Puerto host `5441`. |
| `nocodb`   | `nocodb/nocodb:latest` | UI admin tipo Airtable sobre Postgres — permite a un comercial editar precios/ofertas/parámetros en caliente. Puerto host `8080`. |
| `seed`     | `build: .`, corre una vez | Idempotente: crea tablas si faltan (`Base.metadata.create_all`) y siembra los 13 módulos + parámetros base (`horario_atencion`, `email_soporte`) solo si las tablas están vacías. `sysbot` depende de que termine (`service_completed_successfully`). |

`cloudflared` (túnel a internet) **no está en `docker-compose.yml`** — corre
como proceso nativo en el host. Detalle en la sección de túnel más abajo.

## Stack de desarrollo y por qué se eligió

| Pieza | Dev | Por qué (contexto de demo) |
|---|---|---|
| Web framework | FastAPI + Uvicorn | Async nativo, tipado, arranque rápido para un webhook HTTP simple. |
| LLM | Gemini (`google-genai` SDK), modelo configurable vía `MODEL_NAME` | El SDK auto-registra funciones Python planas (con docstring) como tools de function-calling — cero boilerplate de schemas JSON manuales (`agent/brain.py` pasa `TOOL_FUNCTIONS` directo a `GenerateContentConfig`). |
| Prompt | `config/prompts.yaml` | Prompt de sistema editable sin tocar código Python. |
| ORM/DB | SQLAlchemy 2.0, **dos engines** sobre el mismo `DATABASE_URL` | Sync (`psycopg2`) para las tools que Gemini invoca (`agent/tools.py`, llamadas sync); async (`asyncpg`) para historial de chat (`agent/memory.py`, ya en el `async def` del handler). Un solo engine no calzaba con ambos contextos sin añadir complejidad de bridging async/sync. |
| BD | Postgres 16 en Docker | Reemplazó un SQLite inicial — necesario para que NocoDB (UI compartida) y `sysbot` lean/escriban la misma fuente de verdad concurrentemente. |
| Admin UI | NocoDB | Da UI de edición tipo spreadsheet sin construir un panel admin a mano — el objetivo es que un comercial cambie un precio y el bot lo refleje al instante (siguiente pregunta ya lee de Postgres). |
| Calendar/Email | Google Calendar API + Gmail API (OAuth2 "installed app", `agent/integrations/google.py`) | `agendar_cita` crea evento real en Calendar; `escalar_a_humano` manda correo real por Gmail. Token persistido en `token.json` (montado como volumen), se auto-refresca. |
| Exposición a internet | Cloudflare Quick Tunnel (`cloudflared.exe`, fuera de Docker) | Cero configuración/cuenta para levantar HTTPS público apuntando a `localhost:8000` — suficiente para que Meta pueda pegarle al webhook durante la demo. |
| Mensajería WhatsApp | Meta Cloud API vía provider abstraction (`agent/providers/base.py` + `agent/providers/meta.py`) | `ProveedorWhatsApp` (ABC) desacopla `main.py` del proveedor concreto — permite swap futuro a Twilio/360dialog sin tocar el handler HTTP. |

### Qué es simulado / no persistente (demo-only)

`agent/tools.py`: citas internas (`_CITAS_DB`) son un **dict en memoria del
proceso** — se resetea en cada restart del contenedor `sysbot`. CRM
(leads/casos) y licencias/soporte ya no viven en memoria: usan EspoCRM y
Firebird respectivamente (ver sección siguiente), persistentes pero en
infra de demo separada. Solo `modulos`, `ofertas`, `parametros` y
`mensajes` son persistentes en el Postgres de producción. Calendar y correo
sí son reales/externos (Google), no simulados.

## Infraestructura de demo (aparte)

Para demostrar validación de licencias/soporte y CRM a usuarios
funcionales, sin mezclar con producción, hay un **segundo compose**:
`docker-compose.demo.yml`. Se levanta junto al compose actual (no lo
reemplaza), conectado por una red Docker externa compartida.

| Servicio | Imagen/build | Rol |
|---|---|---|
| `firebird` | `jacobalberty/firebird:3.0-sc` | BD de licencias (`licencias.fdb`, tabla `LICENCIAS`) — cubre los 3 escenarios de soporte (con licencia+soporte, con licencia sin soporte, sin licencia). |
| `seed-firebird` | `build: .`, corre una vez | Siembra 3 identificaciones fijas (ver `scripts/seed_firebird.py`) de forma idempotente. |
| `postgres-demo` | `postgres:16` | BD propia y aislada solo para EspoCRM — no comparte instancia/credenciales con el `postgres` de producción. |
| `espocrm` | `espocrm/espocrm:latest` | CRM open source con módulos Lead/Case nativos vía API REST. Puerto host `8081`. |

Puente entre los dos compose: red Docker externa **`sysplus-demo`**
(`docker network create sysplus-demo`, una sola vez, antes del primer
`up`), declarada `external: true` en ambos archivos. El servicio `sysbot`
(compose actual) se une también a esta red y le habla a `firebird`/
`espocrm` por nombre de servicio — sin `depends_on` cruzado entre
proyectos Compose (no lo soporta), así que `docker-compose.demo.yml` se
levanta antes o en paralelo, nunca después de que `sysbot` ya esté
respondiendo tráfico crítico.

`agent/tools.py::consultar_licencia` y las tools de CRM
(`registrar_lead_crm`, `consultar_estado_cliente`, `crear_ticket_soporte`,
`consultar_ticket_soporte`) degradan con gracia (devuelven
`sin_licencia`/`error` en vez de crashear) si esta infra de demo no está
levantada — el compose de producción sigue funcionando solo, sin estas
capacidades.

## Alternativas de producción

| Pieza dev | Alternativa producción | Por qué cambiar |
|---|---|---|
| Uvicorn solo | Uvicorn + Gunicorn (workers) detrás de un reverse proxy, o Cloud Run/ECS con autoscaling | Un solo proceso Uvicorn no escala con concurrencia real ni tiene supervisión de crashes. |
| CRM/citas/tickets en dicts de memoria | Tablas Postgres reales (mismo patrón que `Modulo`/`Oferta`/`Parametro`) | Los dicts se pierden en cada restart/deploy — inaceptable para datos de clientes reales. |
| Cloudflare Quick Tunnel | Cloudflare Named Tunnel (cuenta + `credentials.json`, dockerizable con volumen) o un LB/ingress con dominio propio + TLS gestionado (ALB, Nginx+certbot, Cloudflare proxy delante de un dominio) | Quick Tunnel no tiene SLA de uptime y la URL cambia en cada arranque — el propio CLI de Cloudflare advierte que no es para producción. |
| Postgres en contenedor único, sin réplica | Postgres gestionado (RDS/Cloud SQL/Neon) con backups automáticos y réplica | Un solo contenedor sin backup pierde todo ante un fallo de disco/host. |
| Credenciales en `.env` plano | Secrets manager (AWS Secrets Manager, Vault, Docker secrets) | `.env` en texto plano es legible por cualquiera con acceso al filesystem/imagen. |
| Puerto de Postgres publicado a `0.0.0.0:5441` | Sin publicar al host, o restringido a `127.0.0.1` / red interna únicamente | Hoy el puerto está expuesto en la interfaz del host con credenciales débiles (`sysbot`/`sysbot`) — alcanzable desde fuera del contenedor. |
| NocoDB con credenciales compartidas del bot | Usuario Postgres dedicado y de solo los permisos que NocoDB necesita | Hoy NocoDB usa el mismo user/password que `sysbot`, mismo blast radius si se compromete uno. |
| Gemini free tier (20 req/día) | Proyecto con billing habilitado en Google AI Studio/Cloud | Cuota gratuita se agota rápido en tráfico real (ya ocurrió durante pruebas — error 429). |
| Sin rate limiting ni CORS/security headers en FastAPI | Middleware de rate limit (ej. `slowapi`) + headers de seguridad | El webhook público hoy no tiene ninguna protección contra abuso de tráfico. |

## Túnel Cloudflare (exposición a internet)

No está dockerizado ni en `docker-compose.yml`. Es un **Quick Tunnel**
(`cloudflared tunnel --url http://localhost:8000`) sin cuenta Cloudflare:
genera una URL aleatoria en `trycloudflare.com` en cada arranque
(`patches-railway-owners-tigers.trycloudflare.com` es la actual) y no hay
garantía de uptime — el propio Cloudflare CLI advierte que no es apto para
producción, pero suficiente para demo.

Se dejó fuera de Docker a propósito: dockerizarlo (imagen
`cloudflare/cloudflared`) reiniciaría la sesión del túnel y generaría una
URL nueva, rompiendo la URL ya configurada como Callback en el dashboard de
Meta. Migrar a Named Tunnel (URL fija, sí dockerizable con volumen para
`credentials.json`) requiere cuenta Cloudflare — pendiente, no se creó por
decisión del usuario (no quiere crear cuenta por ahora).

Archivos relacionados: `cloudflared.exe`, `cloudflared.log` (raíz del repo,
sí están en `.gitignore` — binarios/logs operativos, no se versionan).

### Detener el túnel

Si la terminal donde se lanzó sigue abierta: `Ctrl+C` ahí mismo.

Si quedó corriendo en background (terminal cerrada o lanzado con `start`),
en PowerShell:

```powershell
tasklist /FI "IMAGENAME eq cloudflared.exe"   # ver PID
taskkill /PID <PID> /F
# o directo por nombre:
taskkill /IM cloudflared.exe /F
```

Al detenerlo, el webhook de Meta pierde a dónde llegar — `sysbot` sigue
corriendo en Docker pero sin exposición a internet.

### Levantar el túnel de nuevo (tras una caída)

1. Verificar que `sysbot` responde localmente antes de exponerlo:
   ```powershell
   curl http://localhost:8000
   ```
   Si no responde, arrancar el stack (`docker compose up -d`) antes de seguir.

2. Revisar si quedó un proceso `cloudflared.exe` colgado (puede seguir "vivo"
   en memoria aunque el binario ya no exista en disco — pasó exactamente eso
   el 2026-07-10: el `.exe` desapareció de la raíz del repo pero el proceso
   viejo seguía corriendo, sin loguear nada nuevo, y el túnel dejó de
   funcionar sin avisar):
   ```powershell
   tasklist /FI "IMAGENAME eq cloudflared.exe"
   taskkill /IM cloudflared.exe /F   # si aparece uno
   ```

3. Si `cloudflared.exe` no está en la raíz del repo, descargarlo de nuevo
   (no se versiona, está en `.gitignore`):
   ```powershell
   curl -L -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
   ```

4. Lanzar el túnel (deja la terminal abierta, o usa `start` para dejarlo en
   background):
   ```powershell
   .\cloudflared.exe tunnel --url http://localhost:8000 > cloudflared.log 2>&1
   ```

5. Leer `cloudflared.log` — la URL nueva aparece en el bloque "Your quick
   Tunnel has been created!" (`https://<palabras-aleatorias>.trycloudflare.com`).
   **Cada arranque genera una URL distinta.**

6. Actualizar el Callback URL del webhook en Meta for Developers
   (WhatsApp > Configuration) con la nueva URL + `/webhook`, y volver a
   verificar el token si Meta lo pide.

URL actual (generada 2026-07-10): `https://unlimited-expects-keith-solutions.trycloudflare.com`

## Seguridad — estado actual

Auditoría hecha sobre el servicio completo (túnel + API + BD):

1. **Validación de firma de webhook — resuelto.** `POST /webhook` ahora
   valida `X-Hub-Signature-256` (HMAC-SHA256 con `META_APP_SECRET`) antes de
   parsear el body, vía `ProveedorWhatsApp.validar_firma` /
   `ProveedorMeta.validar_firma` (`agent/providers/meta.py`,
   `agent/main.py`). Rechaza con 403 si la firma no calza. No requiere
   ningún cambio en Meta — el header ya se envía automáticamente siempre
   que el App tenga App Secret configurado (`META_APP_SECRET` ya existía en
   `.env`). Self-check: `agent/providers/test_meta_firma.py`.
2. **`META_ACCESS_TOKEN` fue mostrado en texto plano** durante debugging en
   esta sesión — recomendado rotarlo en Meta Business dashboard. No hecho
   (decisión del usuario, no del asistente).
3. **Postgres con credenciales débiles y puerto expuesto** (`sysbot`/`sysbot`,
   `5441:5432` bindeado a todas las interfaces del host). Pendiente.
4. **Secretos en `.env` plano**, sin cifrar, aunque correctamente listado en
   `.gitignore` (no se commitea). Pendiente para producción real (ver tabla
   de alternativas).
5. **NocoDB comparte credenciales de Postgres con `sysbot`** en vez de un
   user con permisos acotados. Pendiente.
6. **Sin rate limiting** en el webhook público. Pendiente.
7. **Sin CORS ni security headers** configurados en FastAPI. Pendiente.
8. **Token OAuth de Google (`token.json`) persistido en volumen montado**
   en texto plano — mismo nivel de riesgo que `.env`. Pendiente.
9. **Túnel Quick Tunnel sin SLA / URL efímera** — ver sección de túnel.
   Migrar a Named Tunnel (con Cloudflare Access/WAF opcional) queda como
   mejora de producción, no aplicada por decisión del usuario.

De estos, el punto 1 (firma de webhook) era el más barato de resolver y el
único con impacto directo en integridad de datos (evita que cualquiera con
la URL del túnel inyecte mensajes falsos al bot) — ya está implementado.
