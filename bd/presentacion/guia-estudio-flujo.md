# Guía de estudio · El flujo de datos de Nukyro

Esta guía acompaña a la presentación [flujo-bd.html](flujo-bd.html). Te recomiendo leerla en este orden:

1. **La idea en un minuto** (§1).
2. **Las 4 ideas clave** (§3): si entiendes estas, todo lo demás se deduce.
3. **El recorrido paso a paso** (§4), con la animación abierta al lado.
4. **Autoevaluación** (§7), para comprobar que lo entendiste.

> Fuente: modelo de datos v0.2 (`MODELO-DATOS` del KG), `bd/schema.sql` y `bd/modelo-datos.md`.

---

## 1. La idea en un minuto

Nukyro es un simulador: una persona juega un **escenario ético** (un caso con dilemas), toma decisiones y ve las consecuencias. La base de datos tiene que guardar tres cosas muy distintas:

| Qué se guarda | Quién lo escribe | Analogía |
| --- | --- | --- |
| **El escenario** (la historia, sus dilemas y las preguntas) | El administrador | El **libro** de un "elige tu propia aventura" |
| **La partida** de cada persona (qué eligió y qué le pasó) | El participante, mientras juega | La **libreta** donde anotas por qué páginas pasaste |
| **Las estadísticas** (cuánto aprendió la gente en general) | El sistema, al cerrar la partida | Una **encuesta anónima** en una urna |

Todo el diseño gira alrededor de una regla ética: **la libreta es personal y se puede borrar; la urna es anónima y nunca permite saber quién fue.**

---

## 2. El mapa: 5 dominios (35 tablas)

No memorices las 35 tablas. Memoriza los **5 cajones** y qué contiene cada uno:

| Dominio | Tablas | Pregunta que responde | Analogía |
| --- | --- | --- | --- |
| **Contenido versionado** | 15 | ¿Qué dice el escenario? | El libro (con ediciones) |
| **Administración** | 2 | ¿Quién lo editó y qué hizo? | El registro de la editorial |
| **Identidad** | 5 | ¿Quién está jugando y qué aceptó? | La credencial del jugador |
| **Simulación** | 10 | ¿Qué hizo en su partida? | La libreta de la partida |
| **Estadísticas anónimas** | 3 | ¿Cómo le fue a la gente en general? | La urna anónima |

### Las tablas que sí conviene ubicar

- **Contenido:** `scenarios` → `scenario_versions` → `nodes` (cada "página") → `decision_points` (las páginas donde se elige) → `options` (las alternativas). Además: `rules` (si pasa X, ocurre Y), `state_variables` (indicadores como "confianza del cliente"), `question_sets` → `questions` → `question_options` (los exámenes).
- **Identidad:** `participants` (el jugador), `accounts` (cuenta opcional), `document_acceptances` (aceptó el aviso y los términos), `consent_events`, `arco_requests`.
- **Simulación:** `sessions` (la partida) y todo lo que cuelga de ella: `session_steps`, `session_decisions`, `session_variables`, `session_effects`, `session_events`, `assessment_attempts`…
- **Estadísticas:** `session_facts`, `decision_facts` y `survey_responses`.
- **Administración:** `admin_users` y `admin_audit_log`.

**Truco para los nombres:** si empieza con `session_`, pertenece a una partida. Si termina en `_facts`, es estadística anónima.

---

## 3. Las 4 ideas clave

Cada una corresponde a una decisión de arquitectura (ADR). Si entiendes estas cuatro, el resto del flujo se deduce solo.

### Idea 1 · El escenario tiene "ediciones" que no se tocan (ADR-001)

- Un escenario (`scenarios`) tiene varias **versiones** (`scenario_versions`), como las ediciones de un libro.
- Cada versión pasa por tres estados: **borrador → publicada → retirada** (`draft → published → retired`).
- Solo el borrador se puede editar. Una vez publicada, un **trigger** (un vigilante automático dentro de la base) rechaza cualquier cambio.
- Solo puede haber **una versión publicada y un solo borrador** a la vez (RN-16).
- **¿Por qué?** Si alguien está a mitad de su partida y el administrador cambia el texto, la partida dejaría de tener sentido. Con esta regla, **cada partida queda "pegada" a la edición con la que empezó**.

### Idea 2 · El participante es la raíz de todo, con o sin cuenta (ADR-002)

- Se puede jugar **sin registrarse**. El navegador guarda un secreto y la base solo guarda su huella (`secret_hash`, un hash SHA-256), nunca el secreto.
- Todo lo personal cuelga de `participants`, como las ramas de un árbol.
- Por eso, **borrar al participante borra todo lo suyo de un solo golpe** (borrado en cascada).
- La cuenta (`accounts`) es opcional. Si la persona la crea después, su participante se **vincula** a la cuenta y no pierde el progreso.

### Idea 3 · Cada decisión se guarda una sola vez y con su "por qué" (ADR-003)

- Si la persona da doble clic, o el internet falla y la petición se repite, la decisión **no se duplica**. A esto se le llama ser **idempotente**: repetir la operación da el mismo resultado que hacerla una vez.
- Se logra con la regla `UNIQUE (session_id, node_id)`: en una partida solo cabe **una decisión por dilema** (RN-14).
- Además de la decisión se guarda la **cadena de causas**:
  - qué variables cambió (`session_effects`, con valor anterior y nuevo);
  - qué eventos provocó (`session_events`);
  - qué decisiones causaron cada evento (`session_event_causes`).
- **¿Por qué?** Al final, Nukyro le explica a la persona "esto pasó **porque** decidiste aquello". Sin la cadena guardada no podría explicarlo.

### Idea 4 · Las estadísticas no saben quién eres (ADR-004)

- Las tablas `_facts` y `survey_responses` **no tienen ninguna columna que apunte a una persona**: ni participante, ni sesión, ni cuenta.
- Guardan la **semana** (no la fecha exacta) y la duración en **tramos de 5 minutos**, para que no se pueda reidentificar a nadie.
- **¿Por qué?** Si alguien pide borrar sus datos, se borra la libreta, pero la urna se conserva sin violar su privacidad, porque nunca supo quién era.

---

## 4. El recorrido paso a paso

Usaremos un ejemplo: **Ana** juega el escenario *"datos-de-salud"*. Cada paso coincide con un paso de la animación (el número entre corchetes, p. ej. `[#6]`, es el que puedes poner al final de la URL para abrir ese paso).

### Etapa A · Preparar el contenido (lo hace el administrador)

**Paso 1 · Abrir un escenario** `[#2]`
- El administrador entra al panel con Cognito.
- Crea el escenario y su **versión 1 en borrador**.
- Todo lo que hace queda en `admin_audit_log` (la bitácora).
- 💡 La bitácora **no tiene llaves foráneas** a propósito: si se borra al administrador, el registro de lo que hizo no se pierde.

**Paso 2 · Armar la versión** `[#3]`
- Se crean los **nodos** (páginas de la historia: introducción, información, decisión, evento, desenlace).
- En los nodos de decisión van las **opciones**, las **razones para justificar** (elegidas de una lista, sin texto libre), las **reglas** y la **retroalimentación**.
- 💡 Todo lleva `version_id`. Las llaves compuestas `(version_id, id)` impiden mezclar piezas de dos versiones distintas.

**Paso 3 · Las evaluaciones** `[#4]`
- Cada versión tiene hasta 4 exámenes: **pre-test, post-test, transferencia y causal**.
- Cada pregunta apunta a un objetivo de aprendizaje (RN-11).
- Una pregunta tiene como máximo una respuesta correcta (RF-009).

**Paso 4 · Publicar** `[#5]` *(proceso P12)*
- En una sola operación, la versión publicada anterior pasa a "retirada" y el borrador pasa a "publicado".
- Desde ese momento, el contenido queda **congelado**.

### Etapa B · Ana llega y juega

**Paso 5 · Llega sin cuenta** `[#6]`
- Se crea su fila en `participants` (solo con la huella del secreto).
- Se registran 3 aceptaciones en `document_acceptances`: que es mayor de 18 años, el Aviso de Privacidad y los Términos (RF-073).

**Paso 6 · Empieza la partida** `[#7]`
- Se crea la **sesión** (`sessions`), pegada a la versión publicada. Un trigger impide empezar con una versión que no esté publicada (RN-15).
- Las variables del escenario se copian con su valor inicial a `session_variables`. Por ejemplo, "confianza = 5".
- Se anota el primer paso del recorrido en `session_steps`.

**Paso 7 · Pre-test** `[#8]`
- Se crea un **intento** (`assessment_attempts`) y una respuesta por pregunta (`assessment_answers`).
- Solo hay un intento por examen en cada partida (RN-19).
- Al terminar se guarda la hora en `pretest_completed_at`.
- 💡 La **fase** de la partida (empezada, en el escenario, desenlace, terminada) no se guarda en ninguna columna: se **deduce** de qué fechas ya están llenas.

**Paso 8 · Lee el dilema** `[#9]`
- **Solo lecturas** (SELECT): el nodo, sus opciones, las razones y las referencias.
- 💡 El usuario de base de datos de la app de participantes (`nukyro_api`) **no puede modificar el contenido**, solo leerlo.

**Paso 9 · Confirma su decisión** `[#10]` *(proceso P5, el más importante)*

Todo ocurre en **una sola transacción** (o se guarda todo, o nada):

1. Se **bloquea** la sesión (`FOR UPDATE`) para que dos peticiones simultáneas no se pisen.
2. Se guarda la decisión. Si ya existía, no se duplica (idempotencia).
3. Se guardan las razones elegidas y se calcula si la justificación fue correcta.
4. Se aplican los **efectos** de la opción. Por ejemplo, confianza 5 → 7, y queda anotado en `session_effects`.
5. Se evalúan las **reglas**. Si alguna se cumple, se crea un **evento** y se anota qué decisión lo causó.
6. Se calcula el **siguiente nodo** y se avanza.
7. Se escribe un hecho anónimo en `decision_facts` (solo si Ana no se opuso a las estadísticas).

**Paso 10 · Desenlace** `[#11]`
- Se guarda a qué final llegó.
- La retroalimentación se arma **leyendo la cadena de causas** guardada en el paso 9.
- 💡 No hay calificación de la persona ni rankings: son indicadores narrativos.

**Paso 11 · Evaluaciones finales y encuesta** `[#12]`
- Post-test, transferencia y causal, igual que el pre-test.
- La pregunta causal solo aparece si Ana pasó por el nodo que la condiciona (RF-058).
- La encuesta se guarda en `survey_responses` **sin ningún vínculo con Ana**. En su sesión solo queda la marca `survey_answered = true`, para no volver a preguntarle.

### Etapa C · Lo que pasa después

**Paso 12 · Hechos anónimos** `[#13]`
- Al cerrar la partida se escribe un resumen anónimo en `session_facts`.
- La marca `facts_written_at` evita escribirlo dos veces.
- El usuario de analítica (`nukyro_analytics`) **solo puede leer estas tablas**.

**Paso 13 · Ana crea una cuenta** `[#14]` *(proceso P10)*
- Cognito guarda la contraseña y la base guarda la cuenta (`accounts`).
- Su participante se **vincula** a la cuenta y se borra el secreto: Ana conserva su progreso.
- Si ya tenía cuenta en otro dispositivo, sus partidas se **trasladan** a ese participante.

**Paso 14 · Derechos ARCO** `[#15]`
- Ana puede pedir acceder a sus datos, corregirlos, cancelarlos u oponerse a su uso. La solicitud va a `arco_requests` con sus fechas límite.
- La solicitud **sobrevive aunque se borre la cuenta**, para demostrar que se atendió. Se conserva 12 meses tras el cierre.

**Paso 15 · Caducidad y borrado** `[#16]` *(proceso P9)*
- Si Ana no tiene cuenta y pasa **30 días sin actividad** (RF-080), una tarea automática:
  1. escribe primero los hechos anónimos pendientes;
  2. borra a su participante;
  3. y la **cascada** se lleva todo lo suyo: sesiones, decisiones, efectos, respuestas y aceptaciones.

**Paso 16 · Qué queda** `[#17]`
- Queda el contenido, las estadísticas anónimas, las solicitudes ARCO y la bitácora.
- **Nada de lo que queda identifica a Ana.**

---

## 5. Resumen en una línea (para memorizar)

> **Admin escribe el libro → lo publica y se congela → Ana llega (sin cuenta) → abre su libreta pegada a esa edición → examen inicial → lee, decide y se guarda el porqué → final → exámenes finales y encuesta anónima → resumen anónimo a la urna → (opcional) cuenta → al caducar, se borra la libreta y la urna se queda.**

---

## 6. Glosario mínimo

| Término | Explicación sencilla | Dónde aparece |
| --- | --- | --- |
| **Llave foránea (FK)** | Columna que apunta a una fila de otra tabla. La base no deja apuntar a algo que no existe. | Todas las líneas del diagrama |
| **Llave compuesta** | Llave formada por dos columnas, p. ej. `(version_id, id)`. Obliga a que ambas cosas coincidan. | Contenido y simulación |
| **Borrado en cascada** | Al borrar al "padre", se borran sus "hijos" automáticamente. | Borrar un participante |
| **SET NULL** | Al borrar al padre, el hijo se queda, pero sin el vínculo. | `arco_requests` al borrar la cuenta |
| **Trigger** | Vigilante automático que revisa una operación y puede rechazarla. | Contenido congelado; sesión solo con versión publicada |
| **Transacción** | Grupo de operaciones que se guardan todas o ninguna. | Confirmar una decisión (P5) |
| **Idempotente** | Repetir la operación no cambia el resultado. | Doble clic en "confirmar" |
| **`FOR UPDATE`** | Bloquea una fila mientras se trabaja con ella, para que nadie más la cambie al mismo tiempo. | P5 y P12 |
| **`UNIQUE`** | No puede haber dos filas con el mismo valor. | Una decisión por dilema |
| **Índice parcial único** | `UNIQUE` que solo aplica a ciertas filas, p. ej. solo a las versiones publicadas. | RN-16, RF-009 |
| **`DEFERRABLE`** | La regla se revisa al final de la transacción, no en cada paso. | Crear nodos que se apuntan entre sí |
| **`jsonb`** | Columna que guarda datos con estructura flexible (JSON). | Efectos de las opciones, condiciones de las reglas |
| **Hash (SHA-256)** | Huella de un dato: con ella se puede verificar el dato, pero no se puede recuperar. | `secret_hash` |
| **Rol de base de datos** | Usuario con permisos limitados. | `nukyro_api`, `nukyro_admin`, `nukyro_jobs`, `nukyro_analytics` |
| **SELECT / INSERT / UPDATE / DELETE** | Leer / crear / modificar / borrar filas. | Colores de la animación |

---

## 7. Autoevaluación

Intenta responder sin mirar. Las respuestas están abajo.

1. ¿Por qué una sesión guarda `scenario_version_id` y no solo el escenario?
2. Ana da doble clic en "Confirmar". ¿Qué evita que se guarden dos decisiones?
3. ¿Qué tabla permite explicar "este evento ocurrió por tu decisión"?
4. Si se borra a Ana, ¿por qué no hay que borrar también sus estadísticas?
5. ¿Qué pasa con su solicitud ARCO si se borra su cuenta?
6. ¿Por qué la base guarda un hash del secreto y no el secreto?
7. El administrador quiere corregir un error en una versión publicada. ¿Qué tiene que hacer?
8. ¿Dónde se guarda la "fase" de la sesión?
9. ¿Por qué se escriben los hechos anónimos **antes** de borrar al participante caducado?
10. ¿Qué rol puede leer las estadísticas y qué rol no puede modificar el contenido?

<details>
<summary><b>Respuestas</b></summary>

1. Para que la partida quede **pegada a la edición** con que empezó. Si se publica otra versión, la partida no cambia (RN-15, ADR-001).
2. La regla `UNIQUE (session_id, node_id)` con `ON CONFLICT DO NOTHING`: el segundo intento no inserta nada y se responde con la decisión ya guardada (RN-14).
3. `session_event_causes`, que une cada evento (`session_events`) con las decisiones (`session_decisions`) que lo causaron.
4. Porque las tablas `_facts` no tienen ninguna columna que apunte a ella. Son anónimas desde el diseño (ADR-004).
5. Se conserva: `account_id` pasa a nulo (`SET NULL`), y la solicitud se guarda 12 meses tras su cierre para acreditar que se atendió.
6. Si alguien roba la base, el hash no sirve para hacerse pasar por Ana: no se puede obtener el secreto a partir de él (RF-062).
7. Crear un **borrador nuevo** basado en esa versión (`based_on_version_id`), corregirlo y publicarlo. La versión publicada no se puede editar (trigger, RN-17).
8. En ningún lado: se **calcula** según qué fechas están llenas (`pretest_completed_at`, `outcome_reached_at`, `completed_at`).
9. Porque la cascada se lleva la sesión. Si no se escribe antes, ese dato estadístico se perdería.
10. Lee las estadísticas `nukyro_analytics`, y solo esas tablas. `nukyro_api` (la app de participantes) solo puede leer el contenido, no modificarlo.

</details>

---

## 8. Preguntas que te pueden hacer al presentar

- **"¿Por qué PostgreSQL y no MongoDB?"** Porque el modelo depende de integridad fuerte: llaves compuestas, cascadas, triggers, transacciones e índices parciales. La evaluación del motor la ganó la familia relacional (ADR-005).
- **"¿Por qué tantas tablas `session_*`?"** Porque cada una guarda una pieza distinta de la trazabilidad, y juntas permiten reconstruir la explicación causal del final.
- **"¿Y si dos administradores publican a la vez?"** `FOR UPDATE` sobre el escenario los pone en fila. Además, el índice parcial único impide que haya dos versiones publicadas.
- **"¿Cómo garantizan la privacidad?"** De cuatro formas:
  1. se juega sin cuenta;
  2. el secreto se guarda como hash;
  3. el borrado es en cascada;
  4. las estadísticas no tienen columnas de identidad y usan semana y tramos de tiempo.
- **"¿Qué pasa si se cae la conexión a mitad de una decisión?"** La transacción guarda todo o nada. Si el navegador reintenta, la idempotencia evita duplicar la decisión.
