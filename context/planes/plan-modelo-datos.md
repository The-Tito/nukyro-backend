---
plan: Modelo de datos y base de datos de Nukyro
estado: Completado (2026-11-01)
inicio: 2026-11-01
skill: modelado-de-datos (fases 4 y 5)
insumos: context/proyecto/kg.json, context/adr/ADR-001..005, context/evaluaciones/evaluacion-motor-bd.md, docs/*_NombreCompleto_RequerimientosSoftware_v1.1.docx
---

# Plan · Modelo de datos y base de datos

El objetivo es un modelo **sólido pero ligero**: lo justo para que el esquema, la API (FastAPI) y el backend puedan arrancar. Cada paso se marca al cerrarse y sus hallazgos se anotan en la bitácora del final. Un hallazgo que cambie una decisión aprobada se detiene y se consulta con el usuario.

## Entregables

| Entregable | Ruta |
| --- | --- |
| Documento del modelo (plantilla de la skill) | `bd/modelo-datos.md` |
| DDL de referencia PostgreSQL 16 | `bd/schema.sql` |
| Datos mínimos de prueba | `bd/seed-prueba.sql` |
| Pruebas de reglas de la base | `bd/pruebas/pruebas-reglas.sql` |
| ADR-005 (motor y stack) | `context/adr/ADR-005-postgresql-fastapi.md` |
| Grafo actualizado | `context/proyecto/kg.json` |

## Pasos

| # | Paso | Salida | Estado |
| --- | --- | --- | --- |
| 0 | Registrar las decisiones de stack: PostgreSQL, FastAPI, créditos del laboratorio, ORM | ADR-005, KG | ☑ |
| 1 | Inventariar las entidades por dominio y trazarlas a RF, RN y ADR | Lista de tablas con su origen | ☑ |
| 2 | Fijar las convenciones: nombres, tipos, identificadores, catálogos y fechas | §0 del modelo | ☑ |
| 3 | Diseñar las columnas no obvias de cada entidad | §3 del modelo | ☑ |
| 4 | Diagramar entidad-relación (Mermaid `erDiagram`) | §2 del modelo | ☑ |
| 5 | Definir los estados (`stateDiagram-v2`): versión de escenario, sesión (calculado), cuenta y solicitud ARCO | §4 del modelo | ☑ |
| 6 | Separar las reglas que garantiza la base de las que garantiza la aplicación | §5 del modelo | ☑ |
| 7 | Definir acceso y privilegios: roles de base de datos por proceso | §6 del modelo | ☑ |
| 8 | Describir los procesos transaccionales: confirmar decisión, publicar, conservar progreso al crear cuenta y caducidad o borrado | §7 del modelo | ☑ |
| 9 | Definir borrado y retención por entidad | §8 del modelo | ☑ |
| 10 | Escribir el DDL de referencia y los datos de prueba | `bd/schema.sql`, `bd/seed-prueba.sql` | ☑ |
| 11 | Validar con herramientas: ejecutar el DDL en PostgreSQL 16 (Docker), probar las reglas (RN-14, RN-16, RN-19, cascada) y verificar la sintaxis Mermaid | `bd/pruebas/`, resultados en la bitácora | ☑ |
| 12 | Revisar como revisor exigente (`revision.md` de la skill) | §9 del modelo y resumen al usuario | ☑ |
| 13 | Propagar los cambios: KG, ADR, índice de ADR y documentos fuente si hace falta | KG v1.7.0 | ☑ |

## Criterios de terminado

- Toda tabla cita su origen (RF, RN, ADR o nodo del KG).
- El DDL se ejecuta sin errores en PostgreSQL 16 y las pruebas de reglas pasan, o se documenta por qué no se pudo ejecutar.
- La revisión entrega tres listas: qué puede fallar, qué casos no cubre bien y qué supuestos probar, con las pruebas técnicas pendientes.

## Bitácora de hallazgos

| # | Paso | Hallazgo | Impacto | Acción |
| --- | --- | --- | --- | --- |
| H-01 | 0 | PostgreSQL 16 no tiene `uuidv7()`; llega en PostgreSQL 18. `gen_random_uuid()` (v4) sí es nativo desde PostgreSQL 13. | D2 decía "v7 si el stack lo genera". | La base usa `DEFAULT gen_random_uuid()` y la aplicación puede enviar UUID v7 (por ejemplo con `uuid-utils`; Python 3.14 incluye `uuid.uuid7()`). Ambos caben en `uuid`. |
| H-02 | 0 | Los créditos del laboratorio escolar pueden limitar servicios, tamaño de instancia, extensiones (`pg_cron`) o duración de las sesiones. No se sabe qué programa de créditos es. | Puede impedir usar RDS o Cognito tal como están diseñados. | Prueba técnica pendiente: crear en la cuenta del laboratorio una instancia RDS PostgreSQL 16 y un user pool de Cognito antes de construir. El modelo no depende de `pg_cron`: las purgas las ejecuta un proceso de la aplicación. |
| H-03 | 1 | `references` es palabra reservada en SQL. | Nombre de la tabla de referencias educativas. | Se llama `educational_references`. |
| H-04 | 1 | Inventario: 34 tablas en 5 dominios. **Contenido y administración (16):** scenarios, scenario_versions, learning_objectives, state_variables, nodes, decision_points, options, justification_reasons, rules, educational_references, decision_references, feedback_items, question_sets, questions, question_options, admin_users. **Identidad (4):** accounts, participants, document_acceptances, arco_requests. **Simulación (10):** sessions, session_steps, session_decisions, session_decision_reasons, session_variables, session_effects, session_events, session_event_causes, assessment_attempts, assessment_answers. **Estadísticas (3):** session_facts, decision_facts, survey_responses. **Bitácora (1):** admin_audit_log. | — | Cada tabla cita su origen en el §3 del modelo. |
| H-05 | 1 | OR-05 pide ligar cada decisión con objetivo, personas afectadas, alternativas, fundamento y "qué pregunta comprueba el aprendizaje". Ningún ADR lo concretaba. | Columnas de `decision_points` y `questions`. | `decision_points.learning_objective_id` y `affected_parties` (obligatorios), `decision_references` (fundamento) y `questions.assesses_decision_node_id`. |
| H-06 | 1 | Los estados de ARCO de ADR-004 (`answered`) mezclan "respondida" con su resultado: una respuesta puede ser procedente o negada. Además falta un final para quien no subsana en 10 días. | Máquina de estados de `arco_requests`. | Se refina a `received → awaiting_info ⇄ in_review → accepted → executed`, más `denied` y `withdrawn` como finales. ADR-004 se actualiza en el paso 13. |
| H-07 | 1 | La conservación de `arco_requests` es "el tiempo necesario para atenderlos y acreditar su atención" (Aviso §10): no hay plazo. | La tabla guarda el correo del solicitante. | Pendiente para el usuario. Supuesto: 12 meses tras el cierre, como parámetro de la tarea de purga. |
| H-08 | 2 | Convenciones: inglés, `snake_case`, tablas en plural, llave `id uuid`, llaves foráneas `<entidad>_id`, `timestamptz` en UTC, catálogos `text` + `CHECK`, `jsonb` solo para reglas y detalle de bitácora, esquema `nukyro`. | — | Se aplican en todo el DDL. |
| H-09 | 2 | Para que la base garantice RN-03 y RN-15 (alternativa del nodo y nodo de la versión fijada) sin triggers, las tablas de contenido exponen `UNIQUE(version_id, id)` y las de sesión llevan `scenario_version_id` con **llaves foráneas compuestas**. | La base impide referencias entre versiones. | Patrón aplicado a nodos, opciones, razones, reglas, variables y preguntas. |
| H-10 | 2 | RN-16 dice que "solo una versión en borrador podrá editarse". Se interpreta como "solo los borradores se editan", y además se limita a **un borrador por escenario** para simplificar el panel. | Índice único parcial adicional. | Detalle menor decidido; se declara en el modelo. |
| H-11 | 11 | **Error real del esquema:** borrar un borrador fallaba. La cascada desde la versión borraba `learning_objectives` antes que `decision_points`, que lo referencia con una llave sin cascada. | Sin corrección, el panel no podría descartar borradores. | Las 9 referencias internas del contenido (siguiente nodo, objetivo, origen y destino de reglas, preguntas) pasan a `DEFERRABLE INITIALLY DEFERRED`: se verifican al `COMMIT`. T41 lo prueba y T10b confirma que una referencia rota sí falla al `COMMIT`. |
| H-12 | 11 | Consecuencia de H-11: con llaves diferidas, el error llega en el `COMMIT` y no en la sentencia. | El panel (SQLAlchemy) debe capturar `IntegrityError` al confirmar. | Registrado como F7 y prueba técnica S5 en el modelo. |
| H-13 | 11 | No se pudo validar el renderizado Mermaid: la descarga de `mermaid-cli` fue bloqueada por permisos. | Los 5 diagramas solo tienen revisión manual. | Pendiente: abrir `bd/modelo-datos.md` en un visor con Mermaid (VS Code o GitHub) o autorizar `mermaid-cli`. |
| H-14 | 11 | Resultado: `schema.sql` (34 tablas) y `seed-prueba.sql` se ejecutan sin errores en PostgreSQL 16.15; **45/45 pruebas** pasan. Se comprobó que la cascada la ejecuta `nukyro_jobs` sin permisos sobre las tablas hijas (S6). | — | Contenedor `postgres:16` detenido; se recrea con los comandos del README de pruebas. |
| H-15 | 12 | La revisión encontró 9 riesgos (F1–F9), 6 casos (N1–N6) y 6 supuestos (S1–S6). Lo más relevante: conservar el progreso puede duplicar "primeras sesiones" (N1, se corrige en P10), los consentimientos opcionales no guardan fecha (N4, pendiente) y la API y el panel comparten rol (F4, recomendación). | Ver §9 del modelo. | Pendientes para el usuario en §9.5 del modelo. |
| H-16 | Post | Decisiones del usuario sobre los pendientes del §9.5: retención ARCO de 12 meses (H-07), fechas de consentimientos (N4), roles separados (F4), ORM confirmado. | Modelo v0.1 → v0.2. | Nueva tabla `consent_events` (35 tablas); `nukyro_app` se divide en `nukyro_api` y `nukyro_admin`; índice de purga en `arco_requests`; ADR-005 actualizado. |
| H-17 | Post | Revalidación en PostgreSQL 16.15: **52/52 pruebas** pasan (7 nuevas de permisos y consentimientos: T34b–T34h). La cascada desde `accounts` también borra `consent_events`. | — | `bd/pruebas/README.md` actualizado. |
| H-18 | Post | El usuario confirma que los diagramas Mermaid se visualizan bien (cierra H-13) y que las pruebas S1–S5 ya están validadas porque la misma configuración funciona en otros proyectos con los mismos créditos (cierra H-02). | Sin pendientes técnicos abiertos. | Registrado en §9 del modelo y en el KG como validación reportada por el equipo. |
