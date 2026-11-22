# Registro de decisiones

Vista del KG (`context/proyecto/kg.json`): si difieren, manda el KG y se corrige esta tabla. No se borran.
**Quién:** `usuario`, `usuario (plan)`, `asistente (declarada)` o `heredada` (anterior a la adopción).

## Tomadas

| ID | Fecha | Decisión | Quién | Estado | ADR / evidencia |
|---|---|---|---|---|---|
| D-01 | 2026-11-22 | **Adopción de la metodología.** Gitflow (main, develop), ritmo por paso, módulos aprendizaje e ia, hooks con pre-commit. | usuario | tomada | KG |
| D-02 | 2026-11-22 | **Un solo Knowledge Graph.** context/proyecto/kg.json sigue siendo la única fuente de verdad. Los documentos de seguimiento de context/ son vistas: si difieren, manda el KG. | usuario | tomada | KG |
| D-03 | 2026-11-22 | **Handoff local.** HANDOFF.md e HISTORIAL.md en la raíz, sin versionar. context/HANDOFF.md se retiró el 2026-11-22 con aprobación del usuario. | usuario | tomada | KG |
| D-04 | 2026-11-22 | **Un repositorio para backend y base de datos.** La base no tiene repositorio propio: esquema, migraciones de Alembic y pruebas viven con el backend en The-Tito/nukyro-backend. | usuario | tomada | KG |
| D-05 | 2026-11-22 | **Contenido versionado y datos personales.** docs/ se versiona y queda exento del límite de tamaño. versiones/ queda fuera de git. Los datos personales que ya están en los documentos y el KG solo se admiten en un remoto privado. | usuario | reemplazada | por D-09 |
| D-06 | 2026-11-22 | **Reglas no negociables y decisiones reservadas.** No negociables: Reglas 1 y 2, el servidor decide las consecuencias, no se califica la moralidad, sin IA generativa, justificaciones sin texto libre, solo 18+, ningún código ético se presenta como ley, todo cambio al esquema pasa las pruebas SQL. Del usuario: conflictos, alcance, stack, textos legales, datos personales y su conservación, gasto en AWS y toda publicación o entrega. | usuario | tomada | KG |
| D-07 | 2026-11-22 | **Detalles de la adaptación.** El validador comprueba también rutas, hashes y estados de ADR. La plantilla de ADR sigue el formato existente. Los hooks que reescriben archivos no tocan docs/. | asistente (declarada) | tomada | KG |
| D-08 | 2026-11-22 | **Repositorio público y correo noreply.** El repositorio no se hará privado. Los commits de este repositorio usan el correo noreply de GitHub. | usuario | tomada | cierra A-02 |
| D-09 | 2026-11-22 | **Publicación seudonimizada.** El KG y los ADR no llevan nombres de personas del proyecto, matrículas ni correos. docs/, versiones/ y los .docx de bd/presentacion/ son solo locales y se respaldan por otro medio. Ningún dato personal entra al repositorio público. | usuario | tomada | reemplaza D-05, cierra A-03 (ADR-006) |
| D-10 | 2026-11-22 | **Firma de los commits.** Los commits de este repositorio se firman como The-Tito con el correo noreply de GitHub (D-08), como autor y como committer. | usuario | tomada | KG |
| D-11 | 2026-11-22 | **PR y fusión delegados.** Hasta que el usuario diga que se regresa a «el usuario revisa y fusiona», el asistente crea y fusiona los PR. La fusión es local (git merge --no-ff) y se sube a develop: única excepción al push directo, solo con un PR ya abierto, además del push inicial de main y develop. Releases, etiquetas y entregas se siguen preguntando (D-06). | usuario | tomada | KG |
| D-12 | 2026-11-22 | **Plan y análisis de E1 aprobados.** Se aprueban el plan E0 a E3 y las recomendaciones de E1: Términos v1.1 completos, confirmar las prácticas con el equipo y regenerar solo el índice de requerimientos. T-01 se cierra tras A-03 y la auditoría. El texto legal se aprueba aparte (CONF-14). | usuario | tomada | KG |
| D-13 | 2026-11-22 | **Validación de archivos solo locales.** En las rutas del KG, * sustituye al dato personal y debe dar con un solo archivo. En un clon sin docs/ el validador omite los archivos solo locales y lo avisa. | asistente (declarada) | tomada | KG |
| D-14 | 2026-11-22 | **Cuasi identificadores.** Al aplicar D-09 se omiten también el grupo escolar y el prefijo de matrícula de las rutas, porque combinados con la asignatura y la universidad acotan a las personas. | asistente (declarada) | tomada | KG |
| D-15 | 2026-11-22 | **Backend funcional solo local.** El backend se da por terminado funcionando completo en Docker local, con un emisor de tokens simulado. Sin AWS, sin Cognito real y sin gasto en este plan. | usuario | tomada | KG |
| D-16 | 2026-11-22 | **Sin fechas por ahora.** El plan del backend no lleva fechas ni estimaciones hasta que el usuario las indique. | usuario | tomada | KG |
| D-17 | 2026-11-22 | **Contenido solo de demostración.** El plan usa un escenario y documentos legales ficticios, marcados como demostración. El contenido real queda fuera. | usuario | tomada | KG |
| D-18 | 2026-11-22 | **Correos como funcionalidad futura.** Los correos no bloquean el backend: no hay envío propio en este plan y se pueden agregar después. CONF-18 sigue pendiente. | usuario | tomada | KG |
| D-19 | 2026-11-22 | **Copia anónima al cerrar los datos.** Mientras los datos existen, los reportes se calculan sobre ellos y excluyen a quien se opuso. La copia anónima se crea solo antes de borrar o bloquear. ADR-007 reemplazará a ADR-004. | usuario | tomada | KG |
| D-20 | 2026-11-22 | **Agregar antes de bloquear.** El resultado anónimo se genera antes de bloquear una cuenta, salvo oposición o minoría de edad. Durante el bloqueo los datos no se usan y al purgar solo se borra. | usuario | tomada | KG |
| D-21 | 2026-11-22 | **Métricas por tema y de abandono.** El backend soporta aciertos por tema y punto de abandono como resultados anónimos, con umbral de 10 participantes. | usuario | tomada | KG |
| D-22 | 2026-11-22 | **Dos puertas por fase.** De E2 a E8 cada fase se reafirma y planea, el usuario la aprueba (Puerta A), se construye y comprueba, y el usuario la cierra con evidencia (Puerta B). Sustituye «un paso a la vez» dentro de esas fases. Entre puertas solo se detiene por conflicto, desvío, permiso o bloqueo. | usuario | tomada | KG |
| D-23 | 2026-11-22 | **Plan del backend aprobado.** Se aprueba el plan E2 a E8, que sustituye la parte E2 y E3 de D-12. La aprobación autoriza solo T-08 en local, sin commit ni push. Construir cada fase requiere su Puerta A. | usuario | tomada | KG |
| D-24 | 2026-11-22 | **Ejecución delegada del plan.** En ausencia del usuario, el asistente trabaja hasta terminar el plan: pasa las Puertas A y B y cierra tareas con auditor y evidencia, instala las dependencias del plan, usa Docker local, hace commits, push de ramas, PR y fusiones según D-11. Toda puerta así pasada queda como «delegada», con revisión humana pendiente. No delega conflictos, textos legales, datos personales o su conservación, alcance, gasto, releases a main ni acciones irreversibles: eso queda bloqueado y se reporta. Al 96% del límite de 5 horas se ejecuta /cerrar. La frase literal está en `cita` del KG; Docker, las dependencias, la marca «delegada» y lo no delegado son interpretación del asistente. | usuario | tomada | KG |
| D-25 | 2026-11-22 | **Reparto de modelos.** Opus dirige, decide el diseño y hace la auditoría de cada fase; Sonnet programa y prueba; Haiku lee y resume. Ningún agente fusiona ni hace push: lo hace el director tras repetir la verificación. | asistente (declarada) | tomada | KG |
| ADR-006 | 2026-11-22 | **Repositorio público con contexto seudonimizado.** Concreta D-09. | usuario | Aceptada | context/adr/ADR-006-repositorio-publico-seudonimizado.md |

## Abiertas

Al resolverse, la fila queda `cerrada` y se crea un D-xx que la cierra.

| ID | Decisión | Se analiza en | Depende de | Estado |
|---|---|---|---|---|
| A-01 | **Framework de frontend.** El KG no define el framework ni el repositorio de la interfaz y el panel. | por definir | | abierta |
| A-02 | **Privacidad antes del primer push.** El remoto es público y contradice D-05; además, el correo real de los commits quedaría visible. Falta decidir visibilidad y correo. | adopción | | cerrada |
| A-03 | **Datos personales en repositorio público.** D-05 solo admite datos personales en un remoto privado y D-08 lo mantiene público: falta decidir qué se versiona. Hasta entonces esos archivos no entran a un commit. Recomendación: seudonimizar el KG y los ADR, y dejar fuera de git docs/ y la guía .docx. | E0 | D-08 | cerrada |

## Heredadas

El contenido y los motivos están en el nodo del KG o en su ADR.

| ID | Fecha | Decisión | Quién | Evidencia |
|---|---|---|---|---|
| ACCESO-HIBRIDO | 2026-11-01 | Acceso híbrido: sesión anónima + cuenta opcional | heredada | KG |
| ENCUESTA-APP | 2026-11-01 | Encuesta de satisfacción dentro de la app (H07) | heredada | KG |
| MIGRACION-SESION | 2026-11-01 | Conservar el progreso anónimo al crear cuenta | heredada | KG |
| MODO-ANONIMO | 2026-11-01 | Reglas del modo anónimo (opción B: anónimo efímero) | heredada | KG |
| DEC-STACK | 2026-11-01 | Stack técnico | heredada | KG |
| DEC-IDIOMA-ID | 2026-11-01 | Identificadores técnicos en inglés | heredada | KG |
| DEC-PRIMERA-SESION | 2026-11-01 | Solo la primera sesión cuenta para las hipótesis | heredada | KG |
| DEC-EVAL-SESION | 2026-11-01 | Evaluaciones por sesión | heredada | KG |
| DEC-NICKNAME | 2026-11-01 | Nickname no único | heredada | KG |
| PANEL-ADMIN | 2026-11-01 | Panel de administración | heredada | KG |
| DEC-BLOQUEO | 2026-11-01 | Bloqueo previo a eliminar una cuenta | heredada | KG |
| DEC-VOLUMEN | 2026-11-01 | Volumen del piloto | heredada | KG |
| DEC-SUPUESTOS-MODELO | 2026-11-01 | Supuestos aceptados para el modelo de datos | heredada | KG |
| ADR-001 | 2026-11-01 | Contenido del escenario versionado, híbrido y con claves estables | heredada | context/adr/ADR-001-contenido-versionado-hibrido.md |
| ADR-002 | 2026-11-01 | El participante como raíz de identidad, con o sin cuenta | heredada | context/adr/ADR-002-participante-raiz-identidad.md |
| ADR-003 | 2026-11-01 | Registro idempotente de decisiones y trazabilidad causal | heredada | context/adr/ADR-003-decisiones-idempotentes-trazabilidad.md |
| ADR-004 | 2026-11-01 | Estadísticas anónimas desde el diseño | heredada | context/adr/ADR-004-estadisticas-anonimas.md |
| ADR-005 | 2026-11-01 | PostgreSQL 16 en Amazon RDS con backend FastAPI | heredada | context/adr/ADR-005-postgresql-fastapi.md |
| DEC-MODELO-FASE3 | 2026-11-01 | Análisis del modelo de datos aprobado (fase 3) | heredada | KG |
| DEC-MODELO-V02 | 2026-11-01 | Pendientes del modelo de datos resueltos | heredada | KG |
