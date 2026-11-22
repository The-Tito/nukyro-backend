---
name: modelado-de-datos
description: Diseña el modelo de datos de un proyecto a partir de su documentación. Primero evalúa si los insumos (requerimientos, reglas de negocio, casos de uso, roles, no funcionales, stack) alcanzan para modelar bien y dice qué falta; después analiza contradicciones y decisiones de diseño con opciones y recomendación, espera la aprobación del usuario, escribe el modelo y lo revisa como un revisor exigente. Úsala cuando el usuario pida diseñar, planear o revisar el modelo de datos, el esquema de la base de datos o el diagrama entidad-relación de un proyecto.
---

# Modelado de datos

El objetivo es un modelo **sólido pero ligero**: lo justo para que el esquema, la API y el backend puedan arrancar. El detalle fino de columnas vive después en las migraciones.

El trabajo tiene cinco fases. **Nunca escribas el modelo antes de terminar la fase 3 y tener la respuesta del usuario.** Al final de las fases 1 y 3 te detienes y esperas.

## Reglas que aplican en todas las fases

- **Lo decidido se respeta.** Stack, decisiones de arquitectura (ADR), reglas de negocio y requerimientos aprobados no se cambian por tu cuenta. Si uno te parece un error o contradice a otro documento, dilo y propón la corrección; el usuario decide.
- **Recomienda, no enumeres.** Cada decisión lleva opciones con pros y contras y **una** recomendación marcada. Los detalles menores los decides tú y los declaras como tales.
- **Justifica solo lo no obvio.** Una tabla `users` no necesita justificación; guardar o calcular un estado sí.
- **No copies patrones de otros proyectos por costumbre.** Aislamiento con RLS, cifrado de campos, bitácora inmutable o versionado de datos importados entran solo si los insumos lo piden. Cada pregunta de diseño de [preguntas-de-diseno.md](references/preguntas-de-diseno.md) tiene su condición «Aplica si».
- **Trazabilidad.** Cita los identificadores del proyecto (RF-nn, RN-nn, CU-nn o los que use) en cada decisión, entidad y regla.
- **Idioma.** Escribe en el idioma de la documentación del proyecto. Los identificadores técnicos siguen la convención que se fije en la fase 2.

## Fase 1. Evaluar los insumos

Antes de diseñar, determina si la información alcanza. Un modelo hecho sobre requerimientos incompletos falla en los bordes: estados que nadie definió, borrados que nadie pensó, permisos implícitos.

1. Lee las instrucciones del proyecto (CLAUDE.md, README) y localiza toda la documentación: requerimientos, casos de uso, arquitectura, ADR, diagramas, wireframes, contratos de API.
2. Evalúa cada insumo con [evaluacion-insumos.md](references/evaluacion-insumos.md): si existe, si tiene la calidad que el modelado necesita y qué decisión del modelo queda bloqueada sin él.
3. Entrega un **informe de suficiencia** con este formato y **detente**:

```
## Evaluación de insumos

**Veredicto:** Suficiente | Suficiente con supuestos | Insuficiente

| Insumo | Estado | Qué falta | Qué decisión del modelo afecta |
| --- | --- | --- | --- |
| Requerimientos funcionales | Completo / Parcial / Ausente | … | … |
| … | | | |

### Qué necesito para continuar
(Solo si el veredicto no es «Suficiente».) Para cada hueco, una de tres salidas:
- **Lo aportas tú:** qué documento o sección conviene escribir y qué debe contener.
- **Te pregunto:** preguntas concretas y cerradas (máximo 10 en total), agrupadas por tema.
- **Supongo:** el supuesto que tomaría y su riesgo si es falso.
```

Criterios del veredicto:
- **Insuficiente:** falta un insumo imprescindible, o los requerimientos no permiten listar las entidades principales y sus relaciones. No sigas hasta que se resuelva.
- **Suficiente con supuestos:** faltan insumos recomendables. Puedes seguir si el usuario acepta los supuestos; quedan en la sección de supuestos del modelo.
- **Suficiente:** sigue a la fase 2 en el mismo turno si el usuario ya pidió el modelo completo; si no, pregunta.

Las respuestas del usuario a tus preguntas son insumo: regístralas (en el documento de requerimientos si el usuario lo aprueba, o en la sección de supuestos del modelo).

## Fase 2. Fijar las convenciones transversales

Hay decisiones que, si llegan tarde, obligan a rehacer el modelo. Confírmalas antes del análisis; si ya están en la documentación, solo cítalas:

- **Motor de base de datos y versión**, ORM y herramienta de migraciones.
- **Idioma de los identificadores** (tablas, columnas, valores de catálogo) y si coincide con el de la API y el código.
- **Convención de nombres:** singular o plural, `snake_case`, palabras reservadas del motor (en PostgreSQL, `user`, `order`, `group` obligan a pluralizar o a citar).
- **Quién es la fuente de verdad de la identidad** (la propia base o un proveedor externo como Cognito, Auth0 o Firebase).

Puedes presentarlas junto con el informe de la fase 1 si son pocas.

## Fase 3. Analizar y preguntar

Con los insumos completos, produce el análisis **sin escribir archivos**. Tiene cuatro partes, en este orden:

**1. Contradicciones y huecos entre documentos (C1, C2, …).** Cruza requerimientos, casos de uso, diagramas y arquitectura. Busca en especial:
- un mismo estado que mezcla dos dimensiones independientes;
- requisitos ambiguos («editar nombre y descripción… si cambia el dominio»);
- funcionalidades mencionadas que nadie define (por ejemplo, una baja de cuenta que se cita pero no tiene RF ni caso de uso);
- comparaciones o transiciones que fallan en casos borde (cancelaciones, ejecuciones parciales, borrados);
- permisos declarados que no alcanzan para lo que el proceso tiene que escribir;
- estados finales que no están definidos.

Para cada una: qué dice cada documento, por qué falla con un ejemplo concreto, y tu propuesta. Las que son decisiones de alcance se marcan como «decisión tuya».

**2. Decisiones de diseño (D1, D2, …).** Recorre [preguntas-de-diseno.md](references/preguntas-de-diseno.md) y desarrolla solo las que aplican. Formato de cada una:

```
### Dn. <Tema>
| Opción | A favor | En contra |
| --- | --- | --- |
| A. … | | |
| **B. …** ✅ | | |

<Por qué B, en una o dos frases, citando los requerimientos.>
```

Señala cuál es la **decisión central**, la que más condiciona el resto. Al final, un apartado «Detalles menores (los decido yo salvo que digas otra cosa)».

**3. ADR propuestos.** Una decisión merece ADR si es difícil de revertir, si se descartaron alternativas razonables o si otra persona la va a cuestionar después. Lista título y qué decisiones agrupa.

**4. Lo que necesito de ti.** Lista numerada: qué hacer con cada C, si aceptas las D o cuáles cambias, si quieres los ADR, y qué documentos fuente corregirías como consecuencia.

**Detente y espera la respuesta.** El usuario puede aceptar, cambiar una recomendación o pedir que analices una alternativa nueva. Si su respuesta abre un tema que cambia el modelo (por ejemplo, una obligación legal), investígalo antes de escribir y dile cómo lo resolviste.

## Fase 4. Escribir

1. Escribe el documento del modelo con la estructura de [plantilla-modelo.md](references/plantilla-modelo.md).
2. Escribe los ADR aprobados con el formato que ya use el proyecto.
3. **Propaga las correcciones** que el usuario aprobó a los documentos fuente (requerimientos, casos de uso, diagramas, arquitectura) y súbeles la versión. Lístalas aparte en tu resumen: el usuario tiene que saber qué cambió fuera del modelo.
4. Valida lo que se pueda validar con herramientas (por ejemplo, que los diagramas Mermaid rendericen). Di qué no pudiste validar.

## Fase 5. Revisar como un revisor exigente

Al entregar, revisa tu propio modelo con [revision.md](references/revision.md) y reporta tres listas: **qué puede fallar**, **qué casos no cubre bien** y **qué supuestos hay que probar**. Cada supuesto técnico riesgoso (una capacidad del motor, del ORM o del proveedor que el diseño da por hecha) se convierte en una **prueba técnica** que debe correr antes de construir encima, con su plan B.

Termina con lo que necesitas que el usuario confirme: las decisiones que tomaste tú sin preguntar y los documentos derivados que quedaron desactualizados (por ejemplo, exportaciones .docx).
