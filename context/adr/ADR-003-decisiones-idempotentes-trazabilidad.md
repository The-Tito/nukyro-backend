---
id: ADR-003
titulo: Registro idempotente de decisiones y trazabilidad causal
estado: Aceptada
fecha: 2026-11-01
decisores: PER-DEV-01, PER-DEV-02, PER-DEV-03
kg: [ADR-003, D4, D5, C3, C6]
---

# ADR-003 · Registro idempotente de decisiones y trazabilidad causal

## Contexto

El motor de estado es la funcionalidad crítica (FUN-05):

- Una decisión válida se registra junto con sus efectos y la transición, todo o nada (RF-064).
- La primera confirmación fija la alternativa; un reintento devuelve lo confirmado sin repetir efectos (RN-14).
- Cada consecuencia diferida guarda las reglas y decisiones que la activaron (RF-034, RF-065, RN-06).
- El resumen final relaciona decisiones con consecuencias y distingue causalidad de riesgo (RF-040, RF-041).
- El avance de la sesión (RF-005, RF-061) mezclaba fases con abandono (C3).
- Las preguntas causales dependen del recorrido de cada persona (C6).

## Decisión

1. **Decisión + efectos aplicados + valor actual + eventos con causa (D4):**
   - `session_decisions`: una fila por nodo de decisión en cada sesión, con **restricción única (sesión, nodo)**. Un reintento choca con ella y el servidor devuelve la fila ya confirmada (RN-14).
   - `session_decision_reasons`: las razones estructuradas que la persona eligió como justificación (CONF-03), calificadas con los criterios de la versión (RF-059).
   - `session_effects`: cada efecto aplicado (decisión, variable, valor anterior y nuevo, regla que lo produjo).
   - `session_variables`: valor actual de cada variable de la sesión, que se actualiza en la misma transacción.
   - `session_events`: eventos o consecuencias activados, con la regla que los activó, el tipo de relación (`causal` o `risk`, RF-041) y las decisiones que contribuyeron (`session_event_causes`).
   - `session_steps`: cada cambio de nodo con su fecha, para la reanudación (RF-006) y el análisis de tiempos.
   - Decisión, razones, efectos, variables, eventos, paso y nodo actual se escriben en **una transacción**. Si una parte falla, no se confirma nada (RF-064, RNF-09).
2. **El avance se calcula, no se guarda (C3).** La sesión guarda las fechas de cada hito (`started_at`, `pretest_completed_at`, `outcome_reached_at`, `completed_at`) y el nodo actual. La fase (`started`, `in_scenario`, `outcome_reached`, `completed`) se deriva de esas fechas. El **abandono** (RF-005) se calcula al cerrar el periodo de observación: iniciada y sin desenlace. Caducidad y bloqueo son reglas de conservación, no estados de la sesión.
3. **Evaluaciones con un solo modelo (D5).**
   - `question_sets` (tipo: `pretest`, `posttest`, `transfer`, `causal`) → `questions` → `question_options` con la respuesta correcta.
   - Un intento por conjunto en cada sesión (`assessment_attempts`, restricción única (sesión, conjunto)), con sus respuestas (`assessment_answers`).
   - La puntuación (% de aciertos sobre reactivos válidos, RF-011) se guarda al enviar; un intento incompleto queda sin puntuación.
4. **Preguntas causales condicionadas (C6).** Cada pregunta del conjunto `causal` se liga al evento o desenlace que la habilita. Se muestra, y cuenta para la puntuación, solo si ese evento ocurrió en la sesión (RF-058).

## Alternativas consideradas

| Opción | Por qué se descartó |
| --- | --- |
| Guardar solo las decisiones y recalcular el estado | RNF-12 lo permitiría, pero explicar causas y efectos (RF-040, RF-065) exigiría volver a ejecutar el motor en cada consulta. |
| Guardar el estado de la sesión como un solo campo de fase | Mezcla avance, abandono y caducidad (C3); se desincroniza con los hitos de RF-061. |
| Una tabla por tipo de evaluación | Cinco estructuras casi iguales y cinco flujos de envío. |

## Consecuencias

- **A favor:** la reconstrucción causal es una consulta; la base garantiza la idempotencia; las evaluaciones comparten un solo flujo.
- **En contra:** `session_variables` repite información que también está en `session_effects`. La consistencia depende de escribir todo en la misma transacción, y se verifica con pruebas de reintento y de fallo a medias (RNF-17).
- **Pendiente:** el nivel de aislamiento de la transacción y el manejo del choque con la restricción única dependen del motor elegido (DEC-STACK).

## Trazabilidad

RF-005, RF-006, RF-007–RF-012, RF-019–RF-041, RF-050–RF-059, RF-061, RF-063–RF-065, RN-02–RN-06, RN-13, RN-14, RNF-09, RNF-10, RNF-12, CONF-03.
