# Guía de Paso a Producción - Sysbot (DemoWhatsappAgent)

Este documento detalla todos los aspectos técnicos, configuraciones y precauciones necesarias para desplegar exitosamente la aplicación en un entorno productivo.

---

## 1. Infraestructura y Hosting
- **Requisitos Mínimos:** Se recomienda un servidor VPS (ej. AWS EC2, DigitalOcean Droplet) con al menos 2 vCPU y 4GB de RAM para soportar los contenedores de Postgres, NocoDB, la aplicación Python (Sysbot) y los agentes de monitoreo (Prometheus/Grafana).
- **Orquestación:** Utilizar `docker-compose.prod.yml` para levantar los servicios. Asegurarse de que este archivo no exponga puertos de bases de datos directamente al exterior (ej. el puerto de Postgres debe ser solo interno a la red de Docker o filtrado por firewall).
- **Reverse Proxy y SSL/TLS:** 
  - La aplicación **debe** correr detrás de HTTPS. Meta no envía webhooks a URLs inseguras (HTTP).
  - Configurar un proxy inverso (como Nginx, Traefik o Caddy) o utilizar Cloudflare Tunnels (`cloudflared`) para exponer el servicio local hacia internet con certificados SSL válidos.

---

## 2. Configuración de Variables de Entorno (`.env`)
El archivo `.env` en producción debe estar estrictamente protegido (sin commits a git). Presta especial atención a:
- `PUBLIC_BASE_URL`: **Crítico.** Debe apuntar a la URL raíz pública (ej. `https://api.tuempresa.com`). De esto dependen las rutas absolutas para descargar los PDFs y la resolución del conocimiento estático.
- `WHATSAPP_TOKEN` y `WHATSAPP_PHONE_NUMBER_ID`: Utilizar tokens permanentes (o de sistema) en lugar de los de prueba de 24 horas proporcionados por Meta for Developers.
- `VERIFY_TOKEN`: Debe ser un token robusto y único para validar los webhooks de Meta.
- `DATABASE_URL`: Utilizar credenciales seguras y nunca `postgres:postgres`.
- `GEMINI_API_KEY`: Asegurarse de tener límites de cuota (billing) configurados en la plataforma del LLM para evitar caídas de servicio por rate limiting en alto tráfico.

---

## 3. Base de Datos y Persistencia
- **Volúmenes de Docker:** Los datos de PostgreSQL y NocoDB deben persistir en volúmenes nombrados de Docker o montajes directos en el host para evitar pérdida de datos si los contenedores se reinician o reconstruyen.
- **Backups:** Configurar un cron job o servicio (ej. `pg_dump`) para respaldar regularmente la base de datos `sysbot.db`. Las conversaciones y estados de clientes se guardan allí.

---

## 4. Archivos Estáticos y Documentos (PDFs)
- **Rutas Públicas:** El sistema ahora envía documentos utilizando el tipo `document` nativo de Meta. Esto significa que cuando el bot recomienda un manual, Meta descargará el PDF de tu servidor usando la `PUBLIC_BASE_URL`. 
- **Disponibilidad:** Asegúrate de que la carpeta `static/` (y `/static/pdfs/`) esté accesible públicamente y no esté bloqueada por configuraciones restrictivas en tu Reverse Proxy.
- **Actualización de Conocimiento:** Cada vez que actualices un manual o un archivo markdown en la carpeta `knowledge/`, deberás reconstruir la imagen Docker de `sysbot` (ya que estos archivos se integran a la imagen mediante el comando `COPY` en el `Dockerfile`).

---

## 5. Concurrencia, Bloqueos y Gunicorn
- **Workers:** El archivo `gunicorn_conf.py` orquesta múltiples workers concurrentes. Esto es necesario para procesar ráfagas de mensajes simultáneos.
- **Race Conditions (Inactividad):** Gracias a la refactorización reciente (`SELECT ... FOR UPDATE SKIP LOCKED`), el servicio puede escanear conversaciones inactivas sin que dos workers intenten cerrar el mismo chat simultáneamente, previniendo errores de transacciones en la base de datos. 
- **Timeouts:** Verificar el parámetro `timeout` en Gunicorn. Como se hacen llamadas síncronas a la API del LLM, un timeout muy corto (ej. 30s) causará reinicios constantes de los workers si la API responde lento. Se recomienda al menos 60-120 segundos.

---

## 6. Seguridad y Rate Limiting
- **Validación del Webhook:** Nunca desactivar la validación de firmas de Meta (SHA256). Solo acepta cargas útiles (payloads) que provengan genuinamente de WhatsApp.
- **Protección de Endpoints:** Los endpoints de administración (si los hay) y las métricas (`/metrics`) no deben estar expuestos al público. Configura tu proxy inverso para restringir el acceso a estas rutas mediante IP interna o autenticación básica.

---

## 7. Despliegue (Deploy)
- Dado que se ha retirado el flujo automático (`deploy.yml`), las actualizaciones de código en el VPS productivo deben seguir un proceso manual (o un script gestionado):
  1. Descargar (Pull) los últimos cambios de la rama principal (`main` o `develop`).
  2. Reconstruir la imagen sin usar caché para las carpetas estáticas: `docker compose -f docker-compose.prod.yml build --no-cache sysbot`.
  3. Reiniciar el servicio sin tiempos de inactividad extremos: `docker compose -f docker-compose.prod.yml up -d sysbot`.

---

## 8. Monitoreo y Mantenimiento
- **Circuit Breakers:** El bot implementa un fallback cuando el LLM falla o da error de cuota. Revisa regularmente tus logs para buscar instancias de `"Disculpa, no entendi tu mensaje. ¿Puedes reformular tu pregunta?"`, lo que indicaría caídas de Gemini.
- **Métricas:** Conecta Prometheus al endpoint de la aplicación para monitorear:
  - Latencia de respuesta del LLM.
  - Cantidad de conversaciones activas vs cerradas.
  - Errores de API de Meta o base de datos.
- **Limpieza de Sesiones:** Monitorea el tamaño de la tabla `mensajes` y `conversaciones` a largo plazo. En producción a gran escala, podrías necesitar una estrategia de archivado (data retention) para conversaciones de meses anteriores.
