# Criterios, pesos, anclas y vetos

Este archivo es lo que vuelve objetiva la puntuación. Dos personas que lean las mismas anclas y
los mismos patrones deberían llegar al mismo puntaje ±1. Si no, el ancla está mal escrita o la
evidencia es ambigua: anótalo como hueco.

---

## Los siete criterios (se puntúan por dominio y por motor)

| ID | Criterio | Pregunta que responde | Peso por omisión |
|---|---|---|---:|
| `forma` | Ajuste a la forma de los datos | ¿El modelo del motor representa la estructura real sin forzarla? | 0.15 |
| `lectura` | Ajuste a la lectura dominante | ¿El patrón más frecuente se resuelve en pocas lecturas y sin cruces caros? | 0.20 |
| `integridad` | Garantías para la escritura crítica | ¿El motor garantiza lo que la escritura crítica necesita (atomicidad, unicidad, referencias)? | 0.25 |
| `imprevistas` | Consultas no planeadas y reportes | ¿Responde bien a preguntas que hoy no están en la tabla de patrones? | 0.10 |
| `escala` | Adecuación al volumen y la carga calculados | ¿Cubre el volumen de la fase 2 sin sobredimensionar ni quedarse corto? | 0.10 |
| `especial` | Necesidad especializada | ¿Resuelve de forma nativa grafo, series de tiempo, vectores, texto o clave-valor, si el dominio lo pide? | 0.10 |
| `operacion` | Costo y madurez operativa | Servicio gestionado, respaldos y recuperación puntual, costo, experiencia del equipo | 0.10 |

**Cambiar pesos está permitido solo si se justifica con el caso** (p. ej. «el equipo no tiene
quien administre servidores → `operacion` sube a 0.20») y se anota en el informe. El análisis de
sensibilidad del script dirá si ese cambio altera al ganador.

---

## Anclas (1 a 5)

Regla general: **5** = encaja de forma nativa y con margen; **3** = funciona con trabajo o
convenciones de la aplicación; **1** = va contra el modelo del motor o no lo garantiza.
Los niveles 2 y 4 son intermedios: úsalos cuando la evidencia queda entre dos anclas y di por qué.

### `forma`
| Nivel | Se observa |
|---|---|
| 5 | La estructura del dominio coincide con el modelo del motor: columnas fijas en relacional, o documentos de forma variable/anidada en documentos |
| 3 | Hay que adaptar: columnas opcionales numerosas, tablas EAV, o en documentos un esquema rígido que no aprovecha la flexibilidad |
| 1 | El modelo pelea con los datos: atributos variables metidos en decenas de columnas nulas, o entidades muy normalizadas partidas en documentos que siempre hay que juntar |

### `lectura`
| Nivel | Se observa |
|---|---|
| 5 | El patrón dominante (frecuencia Alta) se resuelve en 1–2 lecturas indexadas, sin cruces o con JOIN simples sobre índices |
| 3 | Requiere 3–4 lecturas o cruces moderados (`$lookup`, JOIN de varias tablas) en un patrón frecuente, tolerables al volumen calculado |
| 1 | El patrón dominante exige cruces caros y frecuentes (`$lookup` en cada petición, reconstruir un objeto de muchas tablas grandes) o leer volumen sin tope |

### `integridad` (con veto)
| Nivel | Se observa |
|---|---|
| 5 | La escritura crítica es atómica de forma nativa: transacción ACID multi-entidad, llaves foráneas, `CHECK`, unicidad. O bien toca un solo documento y el motor la garantiza ahí |
| 3 | Se garantiza con mecanismos que hay que diseñar con cuidado: transacciones multi-documento (requieren replica set y cuestan más), actualizaciones condicionadas, comprobaciones en la aplicación |
| 1 | El motor no puede garantizarla: consistencia eventual en un dato de dinero, inventario o cupo; o la regla depende de que la aplicación nunca falle a mitad de dos escrituras |

**Veto:** si el dominio tiene criticidad **alta** (dinero, inventario, cupo, legal) y un motor
puntúa **1** en `integridad`, ese motor queda **descartado para ese dominio** sin importar su total.

### `imprevistas`
| Nivel | Se observa |
|---|---|
| 5 | Lenguaje de consulta declarativo y general (SQL, agregaciones ricas); los reportes nuevos se escriben sin cambiar el modelo |
| 3 | Se pueden responder, pero algunas requieren índices nuevos, `$lookup` o reestructurar documentos |
| 1 | Solo responde a los accesos para los que se diseñó (clave-valor puro, tablas de una sola partición); otra pregunta exige copiar los datos a otro lado |

> Si los patrones **no se conocen o cambian seguido** (cuarta pregunta), este criterio pesa más:
> sin patrones estables no se puede diseñar un buen modelo de documentos.

### `escala`
| Nivel | Se observa |
|---|---|
| 5 | El volumen y la carga de la fase 2, incluido el caso extremo y la prueba de triplicar supuestos, caben con margen amplio en la configuración más sencilla del motor |
| 3 | Caben, pero con ajustes (particionado, réplicas de lectura, índices cuidadosos) o con margen estrecho en el caso extremo |
| 1 | El volumen o la carga calculados exceden lo razonable para el motor sin una arquitectura distribuida que el proyecto no puede operar |

> Ojo: si **no hay problema de escala**, casi todos los motores sacan 5. Es correcto: este
> criterio no debe premiar «escalabilidad» que el proyecto no necesita.

### `especial`
| Nivel | Se observa |
|---|---|
| 5 | El dominio tiene una necesidad especializada y el motor la cubre de forma nativa (Neo4j para recorridos de varios saltos, colección de series de tiempo, índice vectorial, TTL en clave-valor) |
| 3 | La cubre con extensión o funcionalidad secundaria (`pgvector`, TimescaleDB, CTE recursivas, índices TTL de Mongo, texto completo de PostgreSQL) |
| 1 | No la cubre: habría que simularla en la aplicación |

> **Si el dominio no tiene necesidad especializada, todos los motores puntúan 3** en este
> criterio (neutral). No se premia una capacidad que nadie usa.

### `operacion`
| Nivel | Se observa |
|---|---|
| 5 | Existe servicio gestionado en la nube elegida, con respaldo automático y recuperación puntual; el equipo ya lo domina; costo dentro del presupuesto |
| 3 | Gestionado disponible pero el equipo no lo conoce, o el costo es notable frente al presupuesto, o requiere configuración no trivial (replica set para transacciones) |
| 1 | Habría que autoadministrarlo sin personal para hacerlo, o el costo mínimo excede el presupuesto |

---

## Parámetros de arquitectura (los usa `score.py`)

| Parámetro | Valor por omisión | Por qué |
|---|---:|---|
| Castigo por cada motor adicional | 0.30 | Segundo respaldo, segundo monitoreo, segunda curva de aprendizaje, segundo costo fijo |
| Castigo por escritura crítica que cruza motores | 0.40 | Sin transacción común, una falla a mitad deja estados inválidos |
| … si la escritura cruzada está mitigada (outbox, CDC, fuente de verdad única) | 0.15 | El mecanismo existe, pero hay que construirlo y operarlo |
| Umbral de empate técnico | 0.15 | Por debajo, la diferencia es menor que el error de las propias anclas |

Los puntajes están en escala 1–5. Un castigo de 0.30 equivale a bajar un nivel completo en un
criterio de peso 0.30: es costoso a propósito. Un híbrido tiene que ganarse su lugar.

---

## Cómo se calcula

1. **Puntaje de un motor en un dominio** = Σ (peso del criterio × puntaje 1–5).
2. **Puntaje de una arquitectura** = Σ (peso del dominio × puntaje del motor asignado a ese
   dominio) − castigo por motores adicionales − castigo por escrituras cruzadas.
3. **Veto:** una arquitectura que asigna a un dominio de criticidad alta un motor vetado queda
   descartada.
4. **Sensibilidad:** se mueve cada peso de criterio ±50 % (renormalizando) y el castigo de motor
   de 0× a 2×; se reporta si el ganador cambia en algún escenario.
5. **Empate técnico:** si el primero y el segundo quedan a menos del umbral, no hay ganador por
   puntaje. Se elige la opción **más simple** (menos motores, lo que el equipo ya domina) y se dice
   qué dato desempataría.
