# CLAUDE.md

<!-- BEGIN factory-build-harness v0.9.0 -->
## Arnés de construcción (Factory Build Harness)

Este proyecto instaló `@factory/factory-spec-build`, el arnés que toma el trabajo de discovery
(hecho con `@factory/spec-driven-product`) y lo lleva a producción épica por épica. Todo gira
alrededor de dos loops anidados:

```
Loop interno  (una épica EP-XXX): DoR -> change OpenSpec -> TDD -> smoke de journey -> api/data
              -> verificación adversarial de cableado -> DoD -> PR + archive
Loop externo  (una release):      Release Gate (seguridad, diseño, UX, coherencia triple,
              arquitectura, integración)
```

Reglas de nomenclatura que conviene memorizar:

- Una épica (`EP-XXX`) es la unidad atómica de construcción; un slice, un change de OpenSpec, una
  rama y un PR son la misma cosa vistos desde ángulos distintos.
- Todo el estado del pipeline vive en un único archivo: `.claude/state/build-state.json` (su forma
  y el protocolo de lectura/escritura están en `.claude/state/README.md`).
- El trabajo del día a día lo cubren las skills `building-a-slice` (loop interno) y
  `releasing-a-version` (loop externo); el ciclo de specs lo cubren las `openspec-*`.
- Los subagentes viven en `.claude/agents/build/`, los comandos bajo `/opsx:*`, y los hooks que
  hacen de gate automático están en `.claude/hooks/build/`.

### Comandos disponibles

| Comando | Para qué sirve |
|---|---|
| `/build:setup` | Completa el bloque de dominio de este archivo (ver más abajo) y deja memoria escrita |
| `/opsx:explore`, `/opsx:new`, `/opsx:continue`, `/opsx:apply` | Explorar -> abrir change -> generar artefactos -> implementar |
| `/opsx:verify`, `/opsx:archive`, `/opsx:sync`, `/opsx:ff`, `/opsx:bulk-archive` | Verificar, archivar y mantener sincronizadas las specs |

### Lo que no se negocia

1. **GitHub Flow sin atajos**: `main` siempre queda desplegable; toda integración pasa por PR. El
   hook `gitflow-guard.sh` corta cualquier commit o push directo a `main`.
2. El enlace entre un change y su épica se declara en la sección `## Trazabilidad` de
   `proposal.md` — jamás en el frontmatter YAML, porque eso rompe `openspec validate`.
3. Toda dependencia nueva se contrasta contra `.claude/config/stack-allowlist.json` (hook
   `stack-guard.sh`); ese archivo se deriva de los requisitos técnicos del PRD.
4. Las revisiones caras — seguridad, diseño, UX, coherencia triple, arquitectura, integración —
   corren una sola vez por release (loop externo), no en cada épica.
5. **Se construye el alcance acordado completo, no un recorte.** Diferir o cortar funcionalidad
   requiere acuerdo explícito del equipo; nunca es una decisión unilateral del modelo. Nada queda
   "para después" ni se empuja bajo la alfombra de la complejidad. Verificar significa ejecutar —
   correr la suite, cargar la página, mirar la consola — no leer el código y asumir que funciona.
6. **Un slice cierra por evidencia, no por declaración.** El gate `dod` exige que
   `wiring_verified` esté en `true`, y ese gate solo lo enciende un subagente adversarial
   independiente (`wiring-adversarial-verifier`, arrancado en contexto limpio) que intentó
   activamente encontrarle huecos al slice (stubs, rutas sin conectar, criterios de aceptación sin
   prueba). El progreso del cableado se persiste en disco (`wiring_checklist[]` +
   `progress_log[]`) justamente para que una sesión nueva no tenga que confiar en su memoria.
7. **La fidelidad visual se prueba mirando, no imaginando.** En slices con interfaz, el gate
   `fidelity` solo puede cerrarse tras comparar la app real contra el prototipo vía MCP de
   devtools del navegador. Si no hubo esa comparación, el gate queda en `false` — un resultado
   "inconcluso" no cuenta como aprobado.
8. **Primero cimientos, después negocio, y en trozos chicos.** Auth, modelo de datos, arquitectura
   base y design-system se construyen antes que las épicas de negocio. Una épica que exceda 3 HU o
   toque 3+ capas se parte en sub-slices que se construyen y verifican de a uno.
9. Ante cualquier choque entre una regla de este arnés y `METODOLOGIA.md`, gana la metodología.

### Bloque de dominio

`/build:setup` completa estos huecos leyendo el PRD; los consumen los subagentes
`security-reviewer`, `stack-guardian`, `data-consistency-checker`, `ux-krug-reviewer`,
`simple-design-reviewer` y `ux-fidelity-reviewer`:

- PRD técnico (de dónde sale el stack): {{PRD_TECH_PATH}}
- Frontera de servicios externos / IA: {{EXTERNAL_SERVICE_LAYER}}
- Qué lógica debe ser determinista (nada de IA ahí): {{DETERMINISTIC_LAYER}}
- Categorías de dato sensible / PII regulada: {{SENSITIVE_DATA_CATEGORIES}}
- Dónde viven los secretos server-side: {{SERVER_SIDE_SECRETS}}
- Decisiones de alto impacto que necesitan explicabilidad en la UX: {{HIGH_STAKES_DECISIONS}}
- Fuente de diseño / referencia visual del proyecto: {{DESIGN_SOURCE}}

Si algún punto sigue mostrando `{{...}}`, todavía no corriste `/build:setup`.

### Antes de usarlo

- CLI de `openspec` instalado globalmente (`npm i -g @fission-ai/openspec`) — lo necesitan los
  comandos `/opsx:*` y las skills `openspec-*`.
- `python3` y `git` disponibles en PATH — los usan los hooks de `.claude/hooks/build/`.
- Corre `factory-build doctor` si algo no engancha.

<!-- END factory-build-harness -->

<!-- BEGIN factory-build-learnings -->
## Convenciones aprendidas (las mantiene /build:reflect)

<!-- Después de cerrar un slice, /build:reflect propone aquí una convención nueva detectada o un
error que se repitió. Solo se agregan con tu aprobación explícita, y quedan sujetas a revisión de
PR como cualquier otro cambio del equipo. -->
<!-- END factory-build-learnings -->

<!-- De aquí en adelante, espacio libre para instrucciones propias del proyecto/cliente. -->

<!-- BEGIN factory-vertical v0.4.0 -->
## Vertical documentaria Factory

Este proyecto usa la vertical Factory (`@factory/spec-driven-product`) para producir y mantener artefactos de discovery / producto:

```
PRD → User Story Map → Backlog → Historias (AC G/W/T) → Priorización → Flows
```

### Estructura

```
docs/
├── 01-prd/                 PRD (12 componentes obligatorios)
├── 02-user-story-map/      Mapa estilo Jeff Patton (backbone + ranking + releases)
├── 03-backlog/             epicas.md + backlog.md (tabla ordenada)
├── 04-historias/           HU-XXX.md con frontmatter YAML obligatorio + AC en G/W/T
├── 05-priorizacion/        Aplicación de framework (MoSCoW/RICE/Valor-Esfuerzo/Eisenhower)
└── 06-flows/               Flujos de navegación en Mermaid, un archivo por épica
```

### Reglas duras (no negociables)

1. Toda Historia de Usuario vive en `docs/04-historias/HU-XXX.md` con frontmatter YAML obligatorio (`id, titulo, epica, prioridad, complejidad, estado`).
2. Todo Acceptance Criterion se escribe en **Given/When/Then**; nada de prosa libre. 3-5 escenarios incluyendo happy / error / edge.
3. Toda Historia pasa los 6 criterios **INVEST** antes de marcarse `estado: lista`.
4. La metodología canónica vive en el `METODOLOGIA.md` del paquete `@factory/spec-driven-product` (ruta exacta depende de dónde npm haya instalado el paquete global; típicamente `$(npm root -g)/@factory/spec-driven-product/METODOLOGIA.md`). Si una skill contradice la metodología, **gana la metodología**.
5. Ningún artefacto se marca como "final" sin pasar por su agente revisor (manual con `/factory:revisar` o automático si `FACTORY_AUTO_AUDIT=true`).

### Slash commands disponibles

| Operativos | Por artefacto |
|---|---|
| `/factory:onboard` — parametriza el proyecto | `/factory:prd` — escribe PRD |
| `/factory:flujo` — pipeline completo | `/factory:epicas` — descompone PRD |
| `/factory:revisar` — auditoría global | `/factory:mapa` — User Story Map |
|  | `/factory:historia` — historia de usuario |
|  | `/factory:ac` — criterios de aceptación BDD |
|  | `/factory:invest` — valida INVEST |
|  | `/factory:backlog` — backlog consolidado |
|  | `/factory:priorizar` — priorización |
|  | `/factory:flows` — flujos de navegación (Mermaid, por épica) |

### Contexto del proyecto

- **Nombre**: DemoWhatsappAgent
- **Dominio**: Bot de WhatsApp conversacional para asesoría comercial, soporte técnico y gestión de licencias
- **Stakeholders**: Product Manager (TBD), Tech Lead (IngKevin95), Equipo Comercial, Equipo Soporte
- **Framework de priorización**: Valor / Esfuerzo

### Convenciones de naming

- Épicas: `EP-001`, `EP-002`, … (3 dígitos)
- Historias: `HU-001`, `HU-002`, … (3 dígitos)
- Slugs en kebab-case-sin-acentos

### Hooks de calidad (opt-in)

Dos flags opcionales en `.claude/settings.local.json`:

```json
{
  "env": {
    "FACTORY_AUTO_AUDIT": "true",
    "FACTORY_REFLECT_SESSION": "true"
  }
}
```

- `FACTORY_AUTO_AUDIT=true` → tras cada Write/Edit en `docs/`, dispara el agente revisor correspondiente. Cuando esté off (default), usar `/factory:revisar` manualmente.
- `FACTORY_REFLECT_SESSION=true` → al cerrar sesión, escanea heurísticas (campos no canónicos en frontmatter, AC fuera de G/W/T, secciones inesperadas en PRD) y escribe propuestas en `docs/.factory-suggestions.md` sin auto-editar nada. Útil para capturar convenciones emergentes del cliente.

<!-- END factory-vertical -->
