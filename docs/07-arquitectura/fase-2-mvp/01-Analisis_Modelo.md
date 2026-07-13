# Plataforma Inteligente de Atención Omnicanal Basada en Agentes de IA
# Capítulo 2 - Análisis del Modelo de Datos Actual

**Construye sobre:** fase 1-demo (arquitectura ya construida)

**Versión:** 1.0

**Estado:** Borrador

**Documento relacionado:** Capítulo 1 - Visión General

---

# 1. Objetivo del análisis

Antes de comenzar el desarrollo de la plataforma es indispensable evaluar el modelo de datos actual.

El objetivo de este capítulo no es criticar el diseño existente.

Por el contrario, busca identificar:

- Fortalezas.
- Debilidades.
- Riesgos futuros.
- Cambios necesarios para soportar IA.
- Cambios necesarios para soportar múltiples canales.
- Cambios necesarios para soportar múltiples agentes.
- Cambios necesarios para soportar trazabilidad empresarial.

---

# 2. Evaluación General

## Estado actual

El modelo actual está orientado principalmente a administrar conversaciones.

Su eje principal está compuesto por:

```
Contacto

↓

Cliente

↓

Mensajes

↓

Área

↓

Agente
```

Es un modelo adecuado para un chatbot tradicional.

Sin embargo, presenta limitaciones importantes cuando se desea construir una plataforma empresarial basada en agentes inteligentes.

---

# 3. Fortalezas del Modelo Actual

## 3.1 Separación de Áreas

La existencia de una tabla de áreas es correcta.

Permite clasificar conversaciones según:

- Comercial
- Soporte
- Facturación
- Implementación

No requiere cambios estructurales.

Únicamente deberá ampliarse.

---

## 3.2 Agentes

La tabla de agentes también está correctamente planteada.

Permite:

- nombre
- correo
- teléfono
- horario
- área

Es una excelente base para integrar posteriormente agentes humanos e IA.

---

## 3.3 Clientes

Separar Cliente de Contacto fue una buena decisión.

Permite manejar información empresarial independiente del contacto.

Esta entidad permanecerá.

---

## 3.4 Parámetros

La tabla de parámetros permitirá administrar configuraciones sin modificar código.

Debe mantenerse.

---

## 3.5 Ofertas y módulos

No presentan problemas.

Pueden permanecer prácticamente iguales.

---

# 4. Debilidad Principal

El problema principal del modelo no es una tabla específica.

Es el concepto central del modelo.

Actualmente todo gira alrededor del teléfono.

```
Teléfono

↓

Mensajes

↓

Área
```

Pero una empresa realmente administra:

CASOS

No teléfonos.

No conversaciones.

No mensajes.

El verdadero objeto de negocio es el caso.

---

# 5. Nuevo Concepto Central

Se propone que el nuevo eje del sistema sea:

```
Cliente

↓

Radicado

↓

Conversación

↓

Mensaje
```

Toda acción deberá pertenecer a un radicado.

---

# 6. Análisis Tabla por Tabla

---

# Tabla: areas

## Estado

✔ Permanecer

## Razón

Está correctamente normalizada.

No depende del canal.

No depende del cliente.

Representa un dominio de negocio.

---

## Cambios propuestos

Agregar:

```
codigo

activo

descripcion

color

orden

sla_id
```

---

## Beneficios

Permitirá:

- configurar SLA por área
- ordenar prioridades
- personalizar dashboards

---

# Tabla: agentes

## Estado

✔ Permanecer

---

Actualmente representa únicamente agentes humanos.

Se propone convertirla en una entidad genérica.

---

## Nuevos campos

```
tipo

(HUMANO / IA)

modelo

activo

prompt_base

capacidad

concurrente_max

estado

ultima_actividad

version

configuracion_json
```

---

## Beneficios

La plataforma podrá manejar:

- personas
- agentes IA

Con la misma arquitectura.

---

# Tabla: contactos

## Estado

Modificar

---

Actualmente el teléfono es la llave principal.

Esto limita:

- WhatsApp
- Correo
- Teams
- Telegram

---

## Nueva estructura

```
Contacto

id

cliente_id

canal

identificador

nombre

correo

telefono

activo
```

---

Ejemplo

Cliente:

Empresa ABC

↓

WhatsApp

573001111111

↓

Correo

soporte@empresa.com

↓

Teams

usuario@empresa.com

---

## Beneficios

Un cliente podrá tener múltiples canales.

---

# Tabla: clientes

## Estado

Permanecer

---

Agregar

```
tipo_cliente

estado

fecha_ultimo_contacto

crm_id

owner

segmento

pais

ciudad

```

---

## Beneficios

Permitirá sincronizar con CRM.

---

# Tabla: mensajes

## Estado

REDISEÑO COMPLETO

---

Actualmente

```
mensaje

↓

telefono

↓

contenido
```

No representa una conversación empresarial.

---

## Problemas encontrados

No pertenece a un caso.

No registra:

- costo IA
- herramientas
- modelo utilizado
- tokens
- respuesta humana
- metadata

---

## Nueva estructura

```
Mensaje

id

radicado_id

conversation_id

autor

tipo

contenido

modelo

tokens_input

tokens_output

costo

timestamp

metadata
```

---

## Beneficios

Será posible calcular:

Costo por cliente.

Costo por área.

Costo por agente.

---

# Tabla: cola_espera

## Estado

Modificar

---

Actualmente representa únicamente una cola.

Pero realmente debería representar:

Cola de asignación.

---

Agregar

```
prioridad

estado

motivo

intentos

asignado_por

```

---

# Tabla: parámetros

## Estado

Permanecer

---

Sin cambios importantes.

---

# Tabla: módulos

## Estado

Permanecer

---

Sin cambios.

---

# Tabla: ofertas

## Estado

Permanecer

---

Sin cambios.

---

# 7. Tablas Nuevas

Aquí aparece la transformación más importante.

---

## Nueva Tabla

RADICADOS

Esta será la entidad principal del sistema.

Todo deberá pertenecer a un radicado.

```
Cliente

↓

Radicado

↓

Conversación

↓

Mensajes

↓

Eventos

↓

Herramientas
```

---

Campos principales

```
id

numero

cliente

area

estado

prioridad

canal

tipo

agente

fecha

ultimo_movimiento

sla

resumen
```

---

# Nueva Tabla

CONVERSACIONES

Un radicado puede tener muchas conversaciones.

Ejemplo

Lunes

↓

Cliente escribe

↓

Martes

↓

Cliente vuelve

↓

Miércoles

↓

Cliente responde

Todo pertenece al mismo radicado.

---

# Nueva Tabla

EVENTOS

Todo cambio deberá generar un evento.

Ejemplos

```
Radicado creado

↓

Asignado

↓

Escalado

↓

Transferido

↓

Cliente respondió

↓

IA respondió

↓

Humano respondió

↓

Cerrado
```

Esto facilitará auditorías.

---

# Nueva Tabla

TOOL CALLS

Registrará todas las herramientas utilizadas.

Ejemplo

```
Consultar CRM

Buscar Ticket

Enviar Correo

Consultar ERP

Consultar Factura
```

---

Campos

```
entrada

salida

duracion

exitosa

error
```

---

# Nueva Tabla

AGENT EXECUTIONS

Registrará el trabajo de la IA.

```
modelo

prompt

respuesta

duracion

tokens

costo

resultado
```

---

# Nueva Tabla

KNOWLEDGE SOURCES

Permitirá saber exactamente qué documentos utilizó el RAG.

```
Manual

Wiki

PDF

Video

FAQ

URL

Versión
```

---

# Nueva Tabla

EMBEDDINGS

Permitirá administrar múltiples colecciones.

```
Ventas

Soporte

Facturación

Implementación
```

Cada área tendrá su propio conocimiento.

---

# Nueva Tabla

INTEGRACIONES

No se debe acoplar la plataforma a un CRM.

Las integraciones serán configurables.

Ejemplo

```
CRM

Help Desk

ERP

SMTP

Google Calendar

Teams

Meta

Telegram
```

---

# Nueva Tabla

SLA

Permitirá configurar tiempos máximos.

```
Respuesta inicial

Respuesta humana

Resolución

Escalamiento
```

---

# Nueva Tabla

AUDITORÍA

Todo cambio importante deberá quedar registrado.

Ejemplo

```
Usuario modificó

↓

Prompt

↓

Configuración

↓

Estado

↓

Herramienta
```

---

# 8. Nuevo Modelo Conceptual

```
                 Cliente

                     │

               Contactos

                     │

               Radicados

         ┌──────────┼──────────┐

         │          │          │

 Conversaciones  Eventos  Asignaciones

         │

     Mensajes

         │

 Tool Calls

         │

 Agent Executions

         │

 Knowledge Sources

         │

 Integraciones

         │

 Sistemas Externos
```

---

# 9. Riesgos del Modelo Actual

Si el modelo permanece como está:

- Las conversaciones crecerán sin contexto.
- No será posible calcular costos de IA.
- No existirá trazabilidad completa.
- El RAG será difícil de auditar.
- No será posible escalar entre áreas.
- No será posible integrar múltiples canales correctamente.
- Se dificultará la evolución hacia múltiples agentes especializados.

---

# 10. Conclusión

El modelo actual constituye una buena base para un chatbot de atención.

Sin embargo, la visión de la plataforma requiere evolucionar hacia un modelo orientado a **Casos (Radicados)** y **Eventos**, donde los mensajes sean únicamente una parte del ciclo de vida de la atención.

La incorporación de nuevas entidades como **Radicados**, **Conversaciones**, **Eventos**, **Tool Calls**, **Agent Executions** e **Integraciones** permitirá construir una plataforma empresarial preparada para agentes inteligentes, múltiples canales y múltiples sistemas corporativos.

---

# Próximo Capítulo

## Capítulo 3 — Modelo de Dominio Propuesto

En este capítulo se diseñará el modelo definitivo de la plataforma, definiendo todas las entidades, relaciones, cardinalidades y responsabilidades de cada componente, siguiendo principios de Domain Driven Design (DDD) y arquitectura orientada a agentes.