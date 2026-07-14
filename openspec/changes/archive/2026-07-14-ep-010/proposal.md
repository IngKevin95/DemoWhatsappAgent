# Proposal: Cierre Explícito de Conversación (EP-010)

## Problem

Actualmente, el sistema no gestiona un cierre explícito y formal en la base de datos:
1. El modelo puede despedirse del usuario amablemente, pero la conversación permanece con estado `abierta` en la base de datos hasta que caduca brutalmente por inactividad.
2. El mecanismo de inactividad (`_revisar_inactividad` en `main.py`) hace solo un check-in y luego corta la sesión, cuando el negocio requiere 2 check-ins de reactivación antes del cierre definitivo.
3. No hay un registro de *por qué* se cerró la conversación (por voluntad explícita del usuario, o por inactividad), lo cual limita el análisis de abandono.

## Why

- **Mejora Analítica:** Saber qué porcentaje de conversaciones terminan por abandono (inactividad) versus cierre normal es vital para medir la calidad de atención.
- **Protocolo de Negocio:** Dar al usuario más de un intento (2 check-ins) reduce las desconexiones accidentales si el usuario tardó un poco más en responder.
- **Estados Lógicos Precisos:** Mantener el estado `cerrada` en sincronía con el LLM evita que el bot reanude conversaciones muertas con un contexto obsoleto si el usuario vuelve días después.

## What Changes

1. **DB Updates:** Agregar `motivo_cierre` (String, nullable) a la tabla `Conversacion` en `agent/db.py`.
2. **2 Check-ins de Inactividad:** En `agent/main.py` (`_revisar_inactividad`), la lógica pasará de 1 check-in a 2 check-ins progresivos (`MENSAJE_CHECKIN_1` y `MENSAJE_CHECKIN_2`) antes de emitir el `MENSAJE_CIERRE`.
3. **Cierre por LLM:** Proveer a Gemini de una Tool (`cerrar_conversacion_explicita`) en `agent/tools.py` (o similar), para que cuando el usuario diga "gracias eso es todo" o se despida, Gemini cierre formalmente la conversación con `motivo_cierre="usuario"`.
4. **Cierre en BD:** Al llegar el timeout o al invocar el cierre explícito, además de vaciar la memoria del LLM (que ya se hace), actualizar la `Conversacion` activa pasando `estado="cerrada"` y fijando el `motivo_cierre` correspondiente.

## Value

- Análisis robusto de tasa de abandono.
- UX mejorada gracias a los 2 check-ins de inactividad.
- Ciclo de vida estricto para la entidad Conversación.
