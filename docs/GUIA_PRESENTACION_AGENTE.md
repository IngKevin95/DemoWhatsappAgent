# Guía de presentación — El Agente (DemoAgent)

> Los tableros muestran *qué pasó*. El agente **es lo que pasa**. Esta guía es para presentar el producto real: un empleado digital que atiende, resuelve y escala 24/7.

## La idea en una frase

> "Es un asesor de DemoCorp que vive en WhatsApp: atiende a cualquier hora, responde con información real de la empresa, agenda demos, gestiona licencias y, cuando el caso lo amerita, se lo pasa a una persona sin que el cliente tenga que repetir nada."

## Por qué es el valor real (no el dashboard)

El dashboard es el espejo retrovisor; el agente es el auto. Cuatro cosas que aporta:

1. **Disponibilidad total** — atiende de noche, fines de semana, picos de demanda, sin contratar más gente.
2. **Respuesta con datos reales** — no improvisa precios ni módulos: los lee de la base de la empresa.
3. **Escalamiento inteligente** — resuelve lo que puede solo; lo que no, lo pasa a la persona correcta del área correcta, con el contexto ya cargado.
4. **Todo queda registrado** — cada conversación, lead y caso se guarda y se sincroniza al CRM automáticamente. De ahí salen los tableros.

---

## Cómo funciona (para ambos públicos)

**Versión funcional (30 segundos):**
> "El cliente escribe por WhatsApp. El agente entiende qué necesita, busca la información en los sistemas de DemoCorp, responde, y ejecuta acciones concretas: cotizar, agendar una demo, abrir un ticket, verificar una licencia. Si se topa con algo que necesita criterio humano, escala."

**Versión técnica (para el ingeniero):**
> "El webhook recibe el mensaje (Meta o Telegram). El modelo — Gemini — hace **function-calling**: decide *qué* herramienta invocar, pero **no** inventa el resultado. Cada herramienta es código determinista que consulta PostgreSQL, Firebird, EspoCRM o Google Calendar y devuelve el dato real. El modelo solo orquesta; los datos críticos (precios, licencias, disponibilidad) nunca salen de la IA, salen de la base."

**Este es el punto que gana al ingeniero:** la frontera IA/determinista. La IA enruta; el código ejecuta. Por eso no alucina un precio.

---

## Lo que el agente sabe hacer (capacidades reales)

Son las funciones que el modelo puede invocar — cada una es una herramienta instrumentada (se miden en Prometheus):

### Comercial
- **Cotizar módulos** (`consultar_precio_modulo`) — precio real desde la base, con oferta vigente aplicada.
- **Consultar combos y ofertas** (`consultar_combos`, `consultar_ofertas_activas`).
- **Buscar en la base de conocimiento** (`buscar_en_knowledge`) — qué hace cada módulo.
- **Registrar leads en el CRM** (`registrar_lead_crm`) — el prospecto queda en EspoCRM.
- **Agendar demos** (`agendar_cita`) — crea el evento en Google Calendar del agente comercial.
- **Consultar disponibilidad** (`consultar_disponibilidad_agenda`).

### Licencias
- **Verificar licencia** (`consultar_licencia`) — consulta el sistema de licencias (Firebird).
- **Estado del cliente** (`consultar_estado_cliente`).
- **Reclasificar casos sin licencia** (`reclasificar_caso_sin_licencia`).

### Soporte
- **Abrir y consultar tickets** (`crear_ticket_soporte`, `consultar_ticket_soporte`).
- **Escalar a un humano** (`escalar_a_humano`) — crea un radicado y notifica al agente del área.
- **Crear tareas** (`crear_tarea`).

### Gestión de la conversación
- **Guardar datos del contacto y consentimiento** (`guardar_datos_contacto`, `registrar_cliente`).
- **Cerrar la conversación** (`finalizar_conversacion`).

---

## Recorrido de una conversación (para narrar o demostrar en vivo)

**Caso comercial feliz:**
> Cliente: "Hola, ¿cuánto vale el módulo de Facturación?"
> Agente: consulta el precio real → "$500.000/mes, y ahora tiene 20% de descuento vigente."
> Cliente: "Me interesa, ¿pueden mostrármelo?"
> Agente: agenda una demo → crea el evento en el calendario del comercial → registra el lead en el CRM.
> **Todo sin intervención humana, y el comercial ya tiene la reunión y el lead cargados.**

**Caso que escala:**
> Cliente: "Mi sistema no genera los reportes, urgente."
> Agente: intenta resolver, ve que necesita soporte técnico → **escala**: crea el radicado, lo asigna al área de soporte, notifica al agente disponible con el resumen del caso.
> **El cliente no repite nada; la persona recibe el contexto completo.**

---

## Diferenciadores técnicos (munición para el ingeniero)

- **Frontera IA/determinista** — la IA decide, el código ejecuta. Cero alucinaciones en datos críticos.
- **Resiliencia** — circuit breaker, reintentos, rate limiting y mensajes de *fallback*: si una dependencia falla, el agente degrada con gracia en vez de romperse.
- **Multi-canal** — misma lógica sobre WhatsApp (Meta) y Telegram.
- **Escalamiento A/B** — puede notificar al agente en su propio WhatsApp (opción A) o hacer que responda dentro del mismo hilo del cliente (opción B).
- **Auditoría e instrumentación** — cada herramienta y cada request se registran y se miden (de ahí salen los tableros).
- **Entrega de documentos** — puede enviar PDFs de los módulos por WhatsApp.
- **Consentimiento de datos** — pide y registra autorización antes de tratar datos personales.

---

## Preguntas probables

### Del ingeniero de sistemas

**"¿No alucina? ¿Qué pasa si el modelo se inventa un precio?"**
> No puede: el modelo no genera el precio, invoca una función que lo lee de la base. Lo único que hace la IA es entender la intención y elegir la herramienta. El dato siempre es real.

**"¿Qué pasa si Gemini se cae?"**
> Hay circuit breaker y mensajes de fallback. El agente responde que no está disponible momentáneamente en vez de colgarse. Las dependencias se ven en el tablero de Monitoreo.

**"¿Cómo manejan datos personales?"**
> El agente pide consentimiento explícito y lo registra (hoy 66% de los contactos lo dieron). Los secretos (tokens, credenciales) viven server-side, nunca en el modelo.

**"¿Es determinista o probabilístico?"**
> Híbrido a propósito: la comprensión del lenguaje es probabilística (IA), pero el enrutamiento a funciones y toda la ejecución de negocio es determinista (código + SQL). Lo crítico no depende del azar del modelo.

**"¿Cómo evitan inyección de prompts / abuso?"**
> Validación de entrada, rate limiting por usuario, y la IA no ejecuta SQL libre: solo puede llamar a un catálogo cerrado de funciones predefinidas.

**"¿Multi-canal significa duplicar lógica?"**
> No. El canal (Meta/Telegram) es solo la capa de transporte; la lógica del agente es única.

### De las áreas funcionales

**"¿Esto reemplaza a mi equipo?"**
> No: absorbe lo repetitivo (precios, dudas frecuentes, agendar) para que el equipo se concentre en lo que necesita criterio humano. Los 841 casos escalados son exactamente donde ustedes agregan valor.

**"¿Y si el cliente pregunta algo que el bot no sabe?"**
> Escala a una persona con el contexto cargado. No deja al cliente en un callejón sin salida.

**"¿Se equivoca?"**
> En datos, no (los lee de la base). En interpretación puede pedir aclaración o escalar. Por eso el escalamiento es parte del diseño, no una falla.

**"¿Aprende de las conversaciones?"**
> Guarda el historial para dar contexto dentro de la conversación. No reentrena solo; las mejoras son controladas.

---

## Cierre

> "El tablero les mostró los resultados. El agente es lo que los produce: un asesor que no duerme, que responde con datos reales, que ejecuta acciones — cotiza, agenda, escala — y que deja todo registrado. La IA aporta la conversación natural; la ingeniería garantiza que cada número y cada acción sean confiables. Eso es lo que están viendo funcionar."

---

### Cómo encadenar las dos presentaciones

1. **Empezá por el agente** (esta guía): mostralo funcionando o narrá una conversación. Es lo que emociona.
2. **Después los tableros** (`GUIA_PRESENTACION.md`): "y todo esto que hizo el agente, se mide así".
3. El agente responde *"¿qué hace por mí?"*; el tablero responde *"¿cómo sé que funciona?"*. Juntos cierran la venta.
