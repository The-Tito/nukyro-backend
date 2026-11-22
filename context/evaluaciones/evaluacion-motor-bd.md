# Evaluación del motor de base de datos · Nukyro

**Fecha:** 2026-11-01 · **Evidencia revisada:** `context/proyecto/kg.json` (v1.5.0), `context/adr/ADR-001` a `ADR-004`, `docs/*_NombreCompleto_RequerimientosSoftware_v1.1.docx`, `docs/entregables/plantillas/Reporte Técnico de la base de Datos.docx` · **Puntuación reejecutable:** `context/evaluaciones/evaluacion-motor-bd.json` con `python3 .claude/skills/skill-evaluar-motor-bd/scripts/score.py context/evaluaciones/evaluacion-motor-bd.json`

> El informe se guarda en `context/evaluaciones/` y no en `docs/`, porque el usuario indicó que `context/` reúne el contexto de decisiones.

## 1. Veredicto

- **Postura:** un solo motor **relacional**. Entre **PostgreSQL** y **MySQL 8** hay **empate técnico** (4.70 contra 4.60, margen 0.10 menor que el umbral de 0.15). La recomendación provisional es **PostgreSQL en Amazon RDS**, pendiente del dato que desempata (§12).
- **Patrón:**
  - **P5** (confirmar decisión, 600/día en el pico) escribe 8 tablas en una sola transacción y depende de la unicidad (sesión, nodo).
  - **P9, P10 y P14** (caducidad, migración a cuenta y ARCO) borran o trasladan datos de varias tablas y escriben `session_facts` en la misma transacción.
  - **P4** (leer nodo, 1000/día) lee contenido versionado con llaves foráneas.
- **Criterio:**
  - La pregunta "¿qué toca una escritura crítica?" responde "varias entidades a la vez", y las tres escrituras que cruzan dominios sin mecanismo de consistencia descartan cualquier híbrido.
  - El empate entre los dos relacionales lo decide la regla "lo más simple y lo que el equipo domina".
  - El único diferencial técnico favorece a PostgreSQL: índice único parcial y JSONB indexable (ADR-001, RN-16).
- **Costo:** se renuncia al costo casi nulo en reposo de DynamoDB bajo demanda y a modelar la versión de escenario como un solo documento (MongoDB). Una instancia de RDS cobra mientras está encendida, aunque no haya tráfico.
- **Lo que falta saber:** (1) qué motor relacional domina el equipo; (2) qué lenguaje y ORM usará el backend; (3) si la cuenta de AWS tiene capa gratuita vigente. Se pregunta al equipo (§12).
- **Confianza:**
  - **Alta** en la familia relacional: margen de 0.80 o más contra MongoDB y DynamoDB, y se mantiene en 16 de 17 escenarios de sensibilidad.
  - **Baja** en PostgreSQL frente a MySQL: hay empate técnico.

## 2. Evidencia recolectada

| Hallazgo | Ruta / fuente | Etiqueta |
|---|---|---|
| Máximo 50 participantes, un escenario | KG `DEC-VOLUMEN` | [DATO] |
| 8–12 decisiones, 3–5 variables, 2–4 eventos, al menos 3 desenlaces | KG `ESC-BECAS` | [DATO] |
| Pre-test y post-test de 5–10 reactivos, transferencia de 5 casos | KG `EVAL-DISENO` | [DATO] |
| Hosting en AWS us-east-1 con Amazon Cognito | KG `ARQ`, Aviso 2.1 §7.1 | [DATO] |
| Escritura atómica e idempotente de decisión, efectos y transición | RF-064, RN-14, ADR-003 | [DATO] |
| Hechos anónimos escritos en la misma transacción que el cierre o el borrado | ADR-004 | [DATO] |
| Contenido híbrido (tablas + JSON para reglas), una sola versión publicada | ADR-001, RN-16 | [DATO] |
| Cascada desde el participante y migración de una sesión anónima a una cuenta | ADR-002, RF-076, RF-080 | [DATO] |
| El reporte técnico pide motor y versión, ORM, hosting, diccionario de datos, roles, índices y triggers | `docs/entregables/plantillas/Reporte Técnico de la base de Datos.docx` | [DATO] |

**Huecos:** no hay código, migraciones ni contrato de API. No se conoce la experiencia del equipo con ningún motor, ni el lenguaje o el ORM del backend (DEC-STACK). No hay presupuesto declarado.

## 3. Patrones de acceso

Frecuencias del **día pico del piloto**: los 50 participantes hacen una sesión el mismo día [SUPUESTO]. Por sesión hay unas 30 peticiones de estado y 20 lecturas de nodo [SUPUESTO], 12 decisiones [DATO: máximo de ESC-BECAS] y 4 intentos de evaluación (pre-test, post-test, transferencia y causal) [DATO].

| ID | Operación | Usuario | L/E | Datos que requiere | Busca por | Frecuencia/día | Criticidad | Evidencia |
|---|---|---|---|---|---|---|---|---|
| P1 | Crear participante y registrar aceptaciones | U01 | E | participante, 3 aceptaciones | — | 50 · Baja | Legal (alta) | RF-073 [DATO] |
| P2 | Iniciar sesión (con la pregunta de primera vez) | U01 | E | sesión, versión publicada | participant_id | 50 · Baja | Operativa | RF-001, RF-077 |
| P3 | Resolver el participante y el estado actual | U01 | L | participante, sesión, nodo, variables | hash del secreto o cognito_sub | 1500 · **Alta** (la más frecuente) | Operativa | RF-006, RF-063 |
| P4 | Leer el nodo autorizado con alternativas y retroalimentación | U01 | L | nodo, decisión, alternativas, razones | node_id (versión fijada) | 1000 · Alta | Operativa | RF-014, RF-019 |
| P5 | Confirmar la decisión | U01 | E | decisión, razones, efectos, variables, eventos, causas, paso, nodo actual, decision_facts | (session_id, node_id) | 600 · Media (**la que más escribe**) | **Alta** [INFERIDO] | RF-064, RN-14, ADR-003 |
| P6 | Enviar un intento de evaluación | U01 | E | intento, respuestas, puntuación | (session_id, set_id) | 200 · Media | Operativa | RF-010, RF-011 |
| P7 | Resumen y reconstrucción causal | U01 | L | decisiones ↔ efectos ↔ eventos ↔ contenido | session_id | 100 · Media | Operativa | RF-039–RF-041 |
| P8 | Cerrar la sesión y escribir session_facts | Sistema | E | sesión, session_facts | session_id | 50 · Baja | Alta | ADR-004 |
| P9 | Caducidad diaria de sesiones anónimas (hechos + borrado) | Tarea programada | E | participantes inactivos más de 30 días | last_activity_at | 1 · Baja | Legal (alta) | RF-080 |
| P10 | Crear cuenta y conservar el progreso | U01 | E | cuenta, participante, sesiones | cognito_sub, hash del secreto | 10 · Baja [SUPUESTO] | Alta | RF-076 |
| P11 | Editar un borrador de contenido | U02 | E | tablas de contenido | version_id | 50 · Baja [SUPUESTO] | Media | RF-082 |
| P12 | Publicar una versión (validación + cambio de estado) | U02 | E | versión, todo su contenido | scenario_id, status | 1 · Baja | Alta | RF-083, RN-16 |
| P13 | Gestionar solicitudes ARCO de cuentas | U02 | L/E | arco_requests, cuenta | status, plazos | 1 · Baja | Legal | RF-085 |
| P14 | Descargar o eliminar los datos propios (sin cuenta) | U01 | L/E | participante y sesiones | hash del secreto | 2 · Baja [SUPUESTO] | Legal | RF-078 |
| P15 | Escribir hechos anónimos y la encuesta | Sistema | E | session_facts, decision_facts, survey_responses | — | 690 · Media | Media | ADR-004 |
| P16 | Reportes de hipótesis H02–H07 | Equipo | L | tablas de hechos | semana, primera sesión | 2 · Baja | Media | §11 de requerimientos |
| P17 | Bitácora del panel y su purga | U02 / tarea | E | admin_audit_log | created_at | 60 · Baja | Baja | RF-087 |

- **Más frecuente:** P3. **El que más escribe:** P5 (con P15, que va dentro de la misma transacción).
- **Se lee junto:** sesión, nodo actual y variables (P3); nodo, alternativas y razones (P4); decisiones, efectos, eventos y contenido (P7).
- **Se escribe junto:** decisión, efectos, variables, eventos, paso y decision_facts (P5); borrado y session_facts (P8, P9, P14); cuenta, participante y sesiones (P10).
- **Aparece en patrones distintos:** las filas de contenido de la versión fijada (P4, P5 y P7) y el participante (P1, P3, P9, P10 y P14).

## 4. Volumetría y carga

- **Filas por sesión** [INFERIDO]: 12 decisiones × (1 decisión + 2 razones + 3 efectos) = 72, más 25 pasos, 5 variables, 4 eventos, 8 causas, 4 intentos y 30 respuestas, que suman **unas 148 filas**.
- **Sesiones en el piloto:** 50 participantes × 1.5 sesiones [SUPUESTO: algunos repiten] = **75 sesiones**, es decir, 75 × 148 ≈ **11 100 filas**.
- **Contenido por versión** [INFERIDO]: 12 × (1 decisión + 4 alternativas + 4 razones + 3 retroalimentaciones) = 144, más 30 nodos, 12 variables, eventos y desenlaces, 40 preguntas × 5 (pregunta y 4 opciones) = 200, y 15 referencias, que suman **unas 400 filas**. Con 10 versiones [SUPUESTO] son **4 000 filas**.
- **Tamaño:** unas 15 000 filas × 300 B [SUPUESTO] ≈ 4.5 MB, × 2.5 por índices y operación ≈ **11 MB**.
- **Carga pico:** el grupo completo en clase al mismo tiempo [SUPUESTO], 50 usuarios × 1 petición cada 10 s = **5 peticiones/s**. Escrituras de P5: 600 decisiones en 45 minutos = **0.22 escrituras/s**.
- **Caso extremo:** dos peticiones simultáneas sobre el mismo nodo de la misma sesión (doble clic o reintento) se resuelven con la restricción única (§9). Dos administradores que publican a la vez se resuelven con RN-16 (§9).
- **Triplicar los supuestos:** 150 participantes × 4.5 sesiones = 675 sesiones ≈ 100 000 filas, menos de 100 MB y 15 peticiones/s. Ninguna decisión cambia.

**¿Hay problema de escala? No.** El volumen cabe varias veces en la instancia más pequeña de cualquier motor evaluado, así que "escalar" no es argumento a favor de ninguno.

## 5. Dominios

Peso = Σ(frecuencia diaria × factor de criticidad: alta 3, media 2, baja 1), normalizado. Total = 12 289.

| Dominio | Patrones | Cuenta | Peso | Criticidad máxima | Escrituras que cruzan a otro dominio |
|---|---|---|---:|---|---|
| Sesión y simulación | P2, P3, P5, P6, P7, P8 | 2500 × 3 = 7500 | 0.610 | Alta | → estadísticas (P5, P8); ← identidad (P9, P10, P14) |
| Contenido versionado | P4, P11, P12 | 1051 × 3 = 3153 | 0.257 | Alta | ← simulación (lectura de validación, mitigado: lo publicado es inmutable) |
| Identidad, cuentas y ARCO | P1, P9, P10, P13, P14 | 64 × 3 = 192 | 0.016 | Alta (legal) | → simulación y estadísticas (cascada y hechos) |
| Estadísticas anónimas | P15, P16 | 692 × 2 = 1384 | 0.113 | Media | Ninguna propia |
| Bitácora | P17 | 60 × 1 = 60 | 0.005 | Baja | Ninguna crítica |

Las tres escrituras cruzadas **sin mitigar** (simulación→estadísticas, identidad→simulación e identidad→estadísticas) son el freno principal de un híbrido: ADR-003 y ADR-004 exigen que vayan en una sola transacción.

## 6. Cuatro preguntas y señales por dominio

| Dominio | ¿La forma cambia? | ¿Qué se lee más? | ¿Qué toca la escritura crítica? | ¿Patrones conocidos? | Señales de otras familias | Familia candidata |
|---|---|---|---|---|---|---|
| Simulación | Fija (ADR-003) | Estado actual (P3) y reconstrucción cruzada (P7) | Varias entidades (P5) | Sí | Ninguna | Relacional; documentos como contraste |
| Contenido | Fija, salvo las reglas (JSON) | Nodo con alternativas (P4) | Varias tablas al publicar (P12) | Sí, pero el panel agrega listados | Grafo de nodos: validación de alcance (RF-066), de pocos saltos y poco frecuente; se resuelve en el código o con CTE recursiva | Relacional + JSON; documentos (versión como documento) |
| Identidad | Fija | Por clave (P3) | Varias entidades (P9, P10, P14) | Sí | Expiración a 30 días, pero con efecto previo (escribir hechos), así que un TTL nativo no sirve | Relacional |
| Estadísticas | Fija | Reportes variables (P16) | Una fila | **No**: las preguntas del análisis pueden cambiar | Ninguna | Relacional |
| Bitácora | Detalle variable | Rara vez | Una fila | Sí | Expiración por antigüedad (TTL) | Cualquiera; clave-valor con TTL como contraste |

**Motores puntuados:** PostgreSQL y MySQL 8 (relacionales con servicio gestionado en AWS RDS), MongoDB (documentos; DocumentDB en AWS o Atlas) y DynamoDB (clave-valor, gestionado y nativo de AWS). La variante "un solo motor con modelo mixto" (R3) **coincide con R1**: ADR-001 ya usa JSON para condiciones y efectos dentro del relacional.

## 7. Matriz de puntuación

Pesos de criterio por omisión de la rúbrica, sin cambios. La justificación de cada celda está en el campo `por_que` del JSON. Lo decisivo es esto:

- **Integridad en simulación e identidad** (peso 0.25): los relacionales sacan 5 por P5, P9 y P10 multi-tabla con restricciones y CASCADE. MongoDB saca 3: P5 es atómico dentro del documento, pero decision_facts, la cascada y la migración exigen transacción multi-documento. DynamoDB saca 2–3: tiene un límite de 100 ítems por transacción y un participante con 2 sesiones ronda los 300 ítems.
- **Imprevistas** (peso 0.10): estadísticas (P16) tiene patrones abiertos. DynamoDB saca 1 porque los reportes exigen exportar los datos.
- **Contenido:** MySQL saca 4 en forma e integridad. No tiene índice único parcial (RN-16 se resuelve con una columna generada más UNIQUE) y su tipo JSON no tiene índice GIN. **Este es el único diferencial técnico entre PostgreSQL y MySQL.**
- **Bitácora:** MySQL saca 3 en `especial` por su Event Scheduler nativo. PostgreSQL saca 2 porque la purga depende de una tarea externa o de `pg_cron`, cuya disponibilidad en RDS falta verificar. El peso de este dominio es 0.005, irrelevante para el total.
- **Operación:** los relacionales sacan 4 y no 5, porque no se sabe qué domina el equipo.

| # | Arquitectura | Base | − Motores extra | − Cruces | **Final** |
|---|---|---:|---:|---:|---:|
| 1 | Solo PostgreSQL | 4.70 | 0.00 | 0.00 | **4.70** |
| 2 | Solo MySQL | 4.60 | 0.00 | 0.00 | **4.60** |
| 3 | Híbrido "mejor por dominio" (MySQL solo en bitácora) | 4.70 | 0.30 | 0.15 | 4.25 |
| 4 | Solo MongoDB | 3.90 | 0.00 | 0.00 | 3.90 |
| 5 | Solo DynamoDB | 3.18 | 0.00 | 0.00 | 3.18 |

- **Resultado del script:** empate técnico entre R1 y R2 (margen 0.10, menor que 0.15). Ningún motor queda vetado.
- **Sensibilidad:** el ganador se mantiene en 16 de 17 escenarios. Solo con castigo cero al híbrido aparece un empate con el híbrido, que no tiene sentido práctico porque mete un segundo motor solo para la bitácora.

## 8. ¿Un motor o un híbrido?

1. **¿Gana después del castigo?** No: queda en 4.25, por debajo de 4.70.
2. **¿Hay una variante en un solo motor que cubra lo mismo?** Sí. La única ventaja del híbrido es la purga de la bitácora, y PostgreSQL la cubre con una tarea programada.
3. **¿Las escrituras críticas cruzan motores?** Sí, tres sin mitigar (§5).

**Veredicto: un solo motor.** El híbrido solo se reconsideraría si apareciera un requisito con disparador concreto, por ejemplo búsqueda semántica sobre retroalimentación (`pgvector` resolvería primero) o miles de participantes con tráfico muy intermitente (DynamoDB por costo). Hoy ninguno existe.

## 9. Ronda adversaria

| # | Objetivo | Ataque | Efecto | Qué quedó |
|---|---|---|---|---|
| 1 | Supuesto de operación | ¿Y si el equipo solo conoce MongoDB? Con `operacion` = 5 para MongoDB y 3 para los relacionales, simulación queda MongoDB 4.10 contra PostgreSQL 4.60 | **Confirmó** | La familia relacional no depende de la experiencia del equipo; la integridad pesa más |
| 2 | Escala | Triplicar participantes y sesiones (§4) | **Confirmó** | Menos de 100 MB y 15 peticiones/s |
| 3 | Costo posterior | RDS cobra por hora con la instancia encendida, aunque el piloto dure semanas; DynamoDB bajo demanda casi no cobra en reposo | **Refinó** | Usar la instancia más pequeña en una sola zona de disponibilidad, apagarla fuera del piloto y verificar la capa gratuita de la cuenta. El precio exacto se verifica en la calculadora de AWS (evidencia externa pendiente) |
| 4 | Sabotaje: doble confirmación | Dos peticiones simultáneas confirman la alternativa A y la B del mismo nodo | **Confirmó** | `UNIQUE(session_id, node_id)` deja pasar solo una; la otra recibe un conflicto y el servidor devuelve la confirmada. Funciona igual en PostgreSQL (`ON CONFLICT DO NOTHING RETURNING`) y en MySQL (error 1062 capturado) |
| 5 | Sabotaje: doble publicación | Dos administradores publican borradores distintos al mismo tiempo, y quedan dos versiones publicadas (viola RN-16) | **Refinó** | PostgreSQL lo impide con un índice único parcial `(scenario_id) WHERE status = 'published'`. MySQL necesita una columna generada (`published_scenario_id`, NULL si no está publicada) más UNIQUE. Ambos lo garantizan; MySQL con un truco. Es el desempate técnico |
| 6 | Cascada parcial | Falla la conexión a mitad del borrado por caducidad: se borraron las sesiones, pero no se escribió `session_facts` | **Confirmó** | Si todo va en una transacción, se revierte. Es justo lo que DynamoDB no garantiza con más de 100 ítems |
| 7 | Segunda opinión | ¿Qué dato haría ganar a MongoDB? Que el contenido se modele como un solo documento **y** que las estadísticas no exijan escribir en la misma transacción | **Confirmó** | Contradice ADR-001 y ADR-004 (aceptados). No es plausible sin revertirlos |

**Contraejemplo mínimo de la regla más crítica (RN-14 / RF-064):** sesión S en el nodo N, variable `privacidad` = 3. Llegan dos peticiones idénticas (reintento): `confirmar(S, N, alternativa B, efecto privacidad −1)`. Sin unicidad, ambas insertan y `privacidad` queda en 1 en lugar de 2, y además se cuenta una decisión doble en `decision_facts`. Lo impide `UNIQUE(session_id, node_id)` en `session_decisions`, dentro de la misma transacción que aplica los efectos: la segunda inserción falla y no aplica nada. PostgreSQL y MySQL lo garantizan; MongoDB solo dentro del documento de la sesión.

## 10. Recomendaciones de implementación (provisionales, PostgreSQL)

- **Servicio:** Amazon RDS for PostgreSQL 16, en una sola zona de disponibilidad, con la instancia más pequeña de la familia `t4g`, respaldo automático y recuperación puntual (RNF-14), cifrado en reposo y TLS obligatorio (RNF-13). Hay que verificar en la cuenta de AWS la capa gratuita y la disponibilidad de `pg_cron`.
- **Tipos:** `uuid` para las llaves (ADR-002, D2); `timestamptz` en UTC; `jsonb` solo para las reglas (ADR-001); `numeric(5,2)` para las puntuaciones; catálogos como `text` con `CHECK`.
- **Lo que garantiza el motor:**
  - unicidad de la decisión por nodo en cada sesión (RN-14);
  - una sola versión publicada por escenario, con índice único parcial (RN-16);
  - un intento por conjunto en cada sesión (RN-19);
  - `cognito_sub` y `secret_hash` únicos;
  - llaves foráneas con `ON DELETE CASCADE` desde `participants` (RF-080);
  - inmutabilidad de lo publicado, por trigger o por permisos (ADR-001).
- **Lo que garantiza la aplicación:** la validación de RF-066 (alcance de nodos y ciclos), la evaluación de las expresiones JSON, el orden "escribir los hechos y después borrar" dentro de la transacción, y el umbral de 10 en los reportes.
- **Índices de los patrones dominantes:**
  - P3: `participants(secret_hash)` único y `sessions(participant_id, scenario_id, started_at)`.
  - P4: `nodes(version_id, key)` único.
  - P9: `participants(last_activity_at) WHERE account_id IS NULL`, índice parcial.

## 11. Plan de validación medible

- **Consultas:** P5 completa (la transacción de 8 tablas, con y sin reintento concurrente), P3, P7 (la reconstrucción) y P9 (caducidad de 50 participantes).
- **Volumen:** el caso triplicado: 675 sesiones, unas 100 000 filas y 10 versiones de contenido.
- **Recursos:** la instancia RDS más pequeña prevista, o un contenedor local limitado a 2 vCPU y 1 GB.
- **Métricas:** P50, P95 y P99 de P5 y P3 con 50 y 150 usuarios virtuales (por ejemplo con k6); errores por conflicto; CPU y memoria; y que la doble confirmación concurrente (ataque 4) nunca duplique efectos (0 casos en 1 000 intentos).
- **Criterio:** se confirma si P95 es menor que 200 ms en P5 y menor que 100 ms en P3 con 150 usuarios, sin efectos duplicados. Si P5 lo excede, se revisan índices antes de cuestionar el motor.

## 12. Preguntas para el equipo

1. **¿Qué motor relacional domina el equipo: PostgreSQL, MySQL o ambos por igual?** Es el dato que desempata. Si dominan MySQL, MySQL 8 es igual de válido, con la columna generada para RN-16.
2. **¿Qué lenguaje, framework y ORM usará el backend?** Lo pide el reporte técnico. Algunos ORM manejan mejor que otros los índices parciales y `jsonb`.
3. **¿La cuenta de AWS tiene capa gratuita vigente?** ¿Hay presupuesto mensual para RDS después del piloto?
