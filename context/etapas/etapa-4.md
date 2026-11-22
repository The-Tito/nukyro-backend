# Etapa 4 · Experiencia educativa: análisis y plan

> Estado: delegado el 2026-11-22 (D-24, D-32), con revisión humana pendiente. Tareas: T-14, T-15, T-16. Decisiones: D-19, D-28, D-29, A-05. Supuestos: S-03.

## Objetivo

Recorrido completo por API: pre-test, escenario, evaluaciones finales, reconstrucción, resumen y encuesta no vinculada.
**No incluye** cuentas (E5), oposición por API y reportes (E6) ni interfaz.

## Reafirmación

| Pregunta | Evidencia | Resultado |
|---|---|---|
| ¿Sigue funcionando lo anterior? | `./scripts/verify` sobre develop en b44b08b | sql=242, unit=188, integration=108, blackbox=61 |
| ¿El objetivo sigue siendo el del KG? | 31 RF con fase E4; validador | Sí |
| ¿Lo construido coincide con lo decidido? | Tres auditorías de E3 | Sí |
| ¿Cuánto falta de verdad? | EV-02 y EV-03 | 39 de 87: 30 demostrados y 9 con interfaz pendiente; 48 pendientes |
| ¿Qué aprendimos que cambie el plan? | E3 | Cantidades del instrumento como criterio; las pistas de forma se prueban; un INSERT de encuesta junto al UPDATE de la sesión los liga por xmin (defecto 2) |

## Dictamen

**Con ajuste.** Cambia el cómo: la encuesta entra por una función de la base y los hitos se escriben una sola vez.

## Análisis

| Paso | Opciones | Elegida y por qué |
|---|---|---|
| Responder | Envío único; guardar y enviar | **Guardar y enviar:** RF-011 habla de intentos incompletos y RN-19 deja un intento |
| Orden final | Libre; causal antes de reconstruir | **Post-test, transferencia y causal; luego resumen.** La reconstrucción y la retroalimentación revelan respuestas (defecto 11) |
| Respuestas correctas | Mostrarlas al final; nunca | **Nunca:** otra sesión del mismo contenido las reutilizaría. El resumen da puntuaciones por evaluación |
| Encuesta | INSERT de la API; función del owner | **Función:** valida, marca la sesión, inserta con la semana de inicio y reescribe la tabla, como ADR-007 |
| Hitos | Solo aplicación; base | **Base:** un trigger impide reescribir o borrar un hito |
| Preguntas de opción de EVAL-DISENO | Agregar columnas; las seis escalas del modelo aprobado | **Las seis escalas.** Recabar datos nuevos lo decide el usuario (A-05) |

Concepto: una puntuación educativa mide una evaluación. Nunca se suman en una nota de la persona (RF-049, RN-07).

## Criterios por RF

| RF | Caso positivo | Caso negativo | Prueba |
|---|---|---|---|
| RF-005, RF-061 | Cuatro fases derivadas de hitos con su hora; abandono calculado con una fecha de corte inyectada | Un hito no se reescribe ni se borra; con desenlace no hay abandono; abandonar no impide reanudar | unitarias, SQL, caja negra |
| RF-007, RF-008 | Con la sesión iniciada se ven las preguntas del pre-test | Sin correctas, tema ni objetivo; ajena: 404 | caja negra |
| RF-009, RF-010 | Una respuesta por pregunta, modificable antes de enviar, queda registrada | Opción de otra pregunta: 422; tras enviar: 409; cero cambios | integración |
| RF-011 | Porcentaje sobre respondidas válidas, igual al calculado a mano | Incompleto que exige todas: 409 y sin puntuación; enviar dos veces no recalifica | unitarias, integración |
| RF-012, RF-055 | Cada intento queda en su sesión | Otra sesión ni lo ve ni lo cambia | integración |
| RF-050, RF-051 | Post-test tras el desenlace, registrado y calificado | Antes del desenlace: 409 | caja negra, integración |
| RF-052, RF-053, RF-054 | 5 casos nuevos con temas del escenario, registrados y calificados | Antes de su turno: 409; ningún enunciado repite el escenario | unitarias, integración |
| RF-058 | Solo las causales de eventos o desenlaces ocurridos, antes de reconstruir | Una no ocurrida no se muestra ni se acepta: 422 | caja negra, integración |
| RF-059 | 4 justificaciones calificadas con la versión de rúbrica de la sesión | Marcar todas no aprueba (defecto 10, visto en rojo con la regla vieja) | unitarias, integración |
| RF-039 | Historial ordenado de decisiones, alternativas y razones elegidas | Sin alternativas no elegidas ni razones correctas | caja negra |
| RF-040, RF-041 | Cada consecuencia con sus decisiones causantes y si es causal o riesgo | No atribuye lo no guardado; un riesgo no sale como causa | integración |
| RF-042, RF-043 | Retroalimentación de la decisión y su alternativa, por categoría | No sale antes de terminar las evaluaciones: 409 | caja negra |
| RF-044, RF-045 | Referencias con tipo, título y fuente | Otra decisión no las hereda | integración |
| RF-046, RF-047, RF-048 | Legal con jurisdicción, versión, sección y vigencia | Lo no legal se marca como no ley; lo legal, limitado a su jurisdicción | integración, caja negra |
| RF-049 | Puntuaciones por evaluación | Ninguna respuesta trae nota global ni juicio de la persona | caja negra |
| RF-056 | Pre, post y su diferencia en puntos | Si falta uno, no hay diferencia | unitarias, caja negra |
| RF-057, RF-067 | Resumen al terminar, consultable después | Antes: 409; ajeno: 404 | caja negra |
| RF-060 | Tras terminar: nota, enlace al aviso, omitir y seis escalas; solo queda «respondida» | Opuesto: no se ofrece y se rechaza (D-29); segunda vez: 409; fuera de 1 a 5: 422; sin vínculo por id, fecha, xmin u orden | SQL, integración, caja negra |

Tres recorridos de punta a punta, con puntuaciones calculadas a mano, dan los resultados esperados.

## Contrato y esquema

| Método y ruta | Entrada | Salida |
|---|---|---|
| `GET /api/v1/sessions/{id}/assessments/{type}` | `pretest`, `posttest`, `transfer` o `causal` | Preguntas y opciones en orden de la sesión, respuestas propias, si está enviada |
| `PUT .../assessments/{type}/answers/{question_key}` | `option_key` | 200: avance |
| `POST .../assessments/{type}/submit` | | 200: enviada; repetir devuelve lo mismo |
| `GET /api/v1/sessions/{id}/summary` | | 200: historial, consecuencias, retroalimentación, referencias y resultados; 409 si falta algo |
| `GET /api/v1/sessions/{id}/survey` | | `available`; si lo está: nota, enlace, omitir y preguntas |
| `POST /api/v1/sessions/{id}/survey` | seis escalas, solo `usefulness` obligatoria | 201 |

Esquema: trigger de hitos de una sola escritura y función `submit_survey`; la API pierde el INSERT de encuestas. La
migración inicial se vuelve a congelar: no hay despliegue.

## Riesgos

- La encuesta de una sola persona es identificable por quien lea la base: residual de ADR-007; los reportes suprimen menos de 10.
- Los textos de la demostración no validan el instrumento pedagógico.

## Plan breve

| Paso | Qué | Entregable | Cómo se verifica |
|---|---|---|---|
| T-14 | Evaluaciones e hitos | módulo de evaluaciones, trigger | Cálculos a mano, defecto 10 |
| T-15 | Reconstrucción y resumen | módulo de resumen | Defecto 11, recorridos |
| T-16 | Encuesta | función y módulo | Sin vínculo, D-29 |

## Puerta A

**Delegada el 2026-11-22 (D-32).** Nadie revisó este documento antes de construir. Cubre los criterios, los cambios al
esquema de arriba, commits, PR y Docker local. No agrega dependencias ni datos a recabar.

## Puerta B

Pendiente.
