---
id: ADR-001
titulo: Contenido del escenario versionado, híbrido y con claves estables
estado: Aceptada
fecha: 2026-11-01
decisores: PER-DEV-01, PER-DEV-02, PER-DEV-03
kg: [ADR-001, D1, D2, C2, PANEL-ADMIN, CONF-13]
---

# ADR-001 · Contenido del escenario versionado, híbrido y con claves estables

## Contexto

El contenido del escenario (objetivos, nodos, decisiones, alternativas, variables, condiciones, efectos, eventos, desenlaces, retroalimentación, referencias y conjuntos de preguntas) se separa del estado de cada sesión y de la lógica del motor (OR-01). Ahora el equipo lo edita desde el panel de administración (PANEL-ADMIN, CONF-13), y eso choca con dos requisitos:

- **RN-15:** las sesiones en curso conservan la versión con la que empezaron. Editar una versión publicada alteraría su recorrido.
- **RF-066 / RNF-11:** un escenario se valida antes de habilitarse. Una edición puntual podría dejar destinos inexistentes o ciclos sin salida.

Además, lo que registra la sesión debe poder reconstruir el recorrido y sus causas (RF-034, RF-039–RF-041, RF-065), y las estadísticas deben agrupar decisiones aunque existan varias versiones (PROC-10).

## Decisión

1. **Modelo híbrido.** La estructura del contenido va en tablas relacionales: versiones, nodos, decisiones, alternativas, variables, eventos, desenlaces, preguntas y referencias. Así, lo que registra la sesión apunta con llaves foráneas a filas reales. Solo las **expresiones** de condiciones y efectos se guardan como documento JSON dentro de su fila, porque siempre se leen completas y no se filtran.
2. **Versiones con ciclo de vida.** Cada versión pasa por `draft → published → retired`.
   - Solo un `draft` se puede editar.
   - Publicar ejecuta la validación de RF-066 (destinos existentes, nodos alcanzables, sin ciclos sin salida, referencias íntegras, toda decisión con alternativa válida). Si falla, la versión no se publica.
   - Una versión `published` es inmutable.
   - Hay **una sola versión publicada por escenario** a la vez; las sesiones nuevas usan esa.
   - Para editar se crea un `draft` copiando la versión publicada.
   - Las versiones publicadas o retiradas nunca se borran, porque hay sesiones que las referencian.
3. **Claves estables.** Cada elemento del contenido lleva una clave de negocio (`D03`, `D03-B`, `EV-02`, `OUT-1`) que se conserva entre versiones y es única dentro de cada versión. Las estadísticas y la comparación entre versiones agrupan por clave, no por la fila.
4. **Identificadores.** Las filas usan UUID (v7 si el stack lo genera, v4 si no). Las claves estables son texto legible para el equipo.
5. **Los conjuntos de preguntas** (pre-test, post-test, transferencia, causales) y los criterios de calificación de las justificaciones (RF-059) **pertenecen a la versión del escenario**. Así se cumple RN-13: cada intento queda ligado a una versión del conjunto de preguntas.

## Alternativas consideradas

| Opción | Por qué se descartó |
| --- | --- |
| Todo normalizado, incluidas condiciones y efectos | Las expresiones (`privacidad < 2 AND D03 = B`) quedan repartidas en muchas tablas pequeñas, difíciles de editar y validar. |
| Cada versión como un solo documento JSON | Sin llaves foráneas: decisiones y consecuencias apuntarían a textos y la trazabilidad dependería solo del código. El panel tendría que editar JSON. |
| Editar la versión publicada | Rompe RN-15 y RF-066. |

## Consecuencias

- **A favor:** la base protege la trazabilidad; el panel trabaja con formularios; las sesiones en curso nunca cambian de contenido; las estadísticas cruzan versiones por clave estable.
- **En contra:** publicar copia filas, irrelevante con un escenario y 8–12 decisiones. La validación de RF-066 y de las expresiones JSON vive en el código del motor y necesita pruebas.
- **Pendiente:** el motor de base de datos (DEC-STACK) define cómo se garantizan la inmutabilidad de lo publicado (permisos o trigger) y la unicidad de la versión publicada (índice único parcial o equivalente).

## Trazabilidad

OR-01, OR-03, OR-04, OR-05, RN-10, RN-13, RN-15, RF-015, RF-027, RF-031, RF-032, RF-034, RF-065, RF-066, RNF-01, RNF-11, RIS-02, CONF-13.
