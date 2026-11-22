# Etapa 3 · Motor de simulación: análisis y plan

> Estado: delegado el 2026-11-22 (D-24), con revisión humana pendiente. Tareas: T-11, T-07, T-12, T-13. Decisiones: ADR-009. Supuestos: S-03, S-04.

## Objetivo

Consecuencias deterministas decididas por el servidor, contenido validado antes de publicar y un escenario ficticio
completo. **No incluye** calificar evaluaciones, reconstrucción ni resumen (E4).

## Reafirmación

| Pregunta | Evidencia | Resultado |
|---|---|---|
| ¿Sigue funcionando lo anterior? | `./scripts/verify` sobre develop en 705dd90 | sql=242, unit=14, integration=26, blackbox=40 |
| ¿El objetivo sigue siendo el del KG? | 31 RF con fase E3; validador | Sí |
| ¿Lo construido coincide con lo decidido? | Equivalencia migración y esquema; auditoría de E2 | Sí, con la excepción de CSRF declarada en ADR-008 |
| ¿Cuánto falta de verdad? | EV-02 | 6 demostrados, 2 con interfaz pendiente, 79 pendientes |
| ¿Qué aprendimos que cambie el plan? | Orden de bloqueo del archivo | P5 bloquea participante y luego sesión |

## Dictamen

**En camino.**

## Análisis

ADR-009 fija gramática, precedencia, causas, avance, reintento y ciclos, con cuatro recorridos calculados a mano
antes de programar. El motor es puro: se prueba sin base. P5 solo carga, llama al motor y persiste en una transacción.

## Criterios por RF

| RF | Caso positivo | Caso negativo | Prueba |
|---|---|---|---|
| RF-006 | Otra petición con la cookie retoma el último nodo confirmado | Otra cookie: 404; una decisión revertida no avanza | caja negra |
| RF-013 | La intro muestra título y contexto del escenario | No expone reglas ni variables | caja negra |
| RF-014, RF-015 | Se recorren los cuatro tipos por la ruta del motor | Un destino enviado por el cliente: 422 | unitarias, caja negra |
| RF-016 | Avanzar mueve un nodo y repetir no mueve otro | Pre-test pendiente: 409 | caja negra |
| RF-017, RF-024 | Con decisión y razones se continúa | Sin decisión: 409; sin razones exigidas: 422, sin cambios | caja negra, integración |
| RF-018, RF-038 | El desenlace se muestra y marca el fin | Avanzar desde él: 409 | caja negra |
| RF-019 | Se listan las alternativas del nodo actual | Sin efectos, destinos ni razones correctas | caja negra |
| RF-020, RF-021, RF-022 | Queda la alternativa con la hora del servidor | Alternativa de otro nodo o fecha del cliente: 422 | integración |
| RF-023, RF-025 | Las razones quedan ligadas a la decisión | Razón de otro nodo, repetida o no pedida: 422 | unitarias, integración |
| RF-026, RF-027 | Cada sesión parte de los valores iniciales | Una sesión no cambia la otra | integración |
| RF-028, RF-029 | Efectos en orden, con límites, tras registrar | Petición inválida: variables iguales | unitarias, integración |
| RF-030, RF-031 | La condición ve el estado ya actualizado | Condición falsa: sin evento | unitarias |
| RF-032 | Sin regla verdadera: alternativa y luego predeterminado | Una regla verdadera prevalece | unitarias |
| RF-033, RF-034, RF-065 | El evento posterior guarda regla y decisiones causantes | No atribuye una rama falsa ni otra sesión | unitarias, integración |
| RF-035 | Solo texto narrativo del contenido | Ninguna respuesta lleva valores de variables | caja negra |
| RF-036, RF-037 | Los cuatro ejemplos de ADR-009 dan su final | El mismo recorrido siempre da el mismo final | unitarias |
| RF-063 | Secreto, nodo, versión y alternativa válidos confirman | Cada inválido: rechazo y cero cambios | integración |
| RF-064 | 1 000 pares concurrentes: 0 duplicados; el reintento devuelve lo confirmado | Un fallo en cada escritura no deja cambios | integración |
| RF-066 | Un contenido válido se publica | Cada tipo de contenido inválido se rechaza, también uno sin pre-test válido (D-28) | unitarias, integración |

## Contrato y esquema

| Método y ruta | Entrada | Salida |
|---|---|---|
| `GET /api/v1/sessions/{id}` | | Sesión, nodo, alternativas, razones y eventos narrativos |
| `POST /api/v1/sessions/{id}/decisions` | `node_key`, `option_key`, `reason_keys` | 200: confirmada y estado actual; `replayed` si es reintento |
| `POST /api/v1/sessions/{id}/advance` | `from_node_key` | 200: estado actual |

No se prevén cambios al esquema.

## Riesgos

- El pre-test se califica en E4: en las pruebas de E3 se marca completado desde la preparación, no por la API.
- El mismo asistente dirige código y pruebas: los finales esperados están calculados a mano en ADR-009.

## Plan breve

| Paso | Qué | Entregable | Cómo se verifica |
|---|---|---|---|
| T-11 | Especificar | ADR-009 | Ejemplos a mano |
| T-07 | Motor y P5 | `src/nukyro/engine/`, módulo de simulación | Unitarias, integración, 1 000 pares |
| T-12 | Validar y publicar | Validador y P12 | Cada inválido, carrera con edición |
| T-13 | Demostración | Escenario ficticio | Pasa RF-066 y sus recorridos |

## Puerta A

**Delegada el 2026-11-22 (D-24).** Nadie revisó este documento ni ADR-009 antes de construir. Cubre los criterios
de arriba, commits y PR de la fase y Docker local. No agrega dependencias.

**Ampliada por el usuario el 2026-11-22 (D-28):** publicar exige pre-test. La fase se cierra sin esperar su revisión (D-32, que modifica D-27).

## Puerta B

Pendiente.
