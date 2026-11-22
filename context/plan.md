# Plan: Nukyro

Vista del KG: si difieren, manda el KG. E0 y E1 aprobadas con D-12; E2 a E8, con D-23 y ejecución delegada por D-24 (2026-11-22).

## Objetivo y límites

- **Se entrega:** el backend y la base de datos del MVP 1.0 (FUN-01 a FUN-11), funcionales en Docker local (D-15), y su documentación.
- **Para quién:** estudiantes de TI mayores de 18 años; piloto de hasta 50 participantes y un escenario (DEC-VOLUMEN).
- **Fuera de este plan:** FA-01 a FA-23, interfaz y panel visual (A-01), AWS y Cognito real (CA-01), correos (CA-02), contenido real (CA-03) y piloto.
- **Sin fechas** por ahora (D-16).

## Etapas

E1 va aparte y no bloquea el backend local. Cada RF tiene una sola fase principal.

| ID | Etapa | Resultado | RF principales | Depende de | Estado |
|---|---|---|---|---|---|
| E0 | Adopción de la metodología | Método instalado, validado y confirmado | | | cerrada |
| E1 | Cierre documental | Documentos coherentes con el KG | | | pendiente |
| E2 | Base ejecutable y entrada | Esquema corregido y primer recorrido HTTPS hasta la base | 001-004, 062, 068, 071, 073 | E0 | cerrada |
| E3 | Motor de simulación | Consecuencias deterministas decididas por el servidor | 006, 013-038, 063-066 | E2 | en_curso |
| E4 | Experiencia educativa | Recorrido completo, del pre-test al resumen | 005, 007-012, 039-061, 067 | E3 | pendiente |
| E5 | Identidad y aislamiento | Con o sin cuenta, cada persona accede solo a lo suyo | 074-077 | E4 | pendiente |
| E6 | Ciclo de datos y estadísticas | Borrar sin perder agregados ni reidentificar | 070, 072, 078-080 | E5 | pendiente |
| E7 | Administración y ARCO | API del panel para operar sin SQL manual | 069, 081-087 | E6 | pendiente |
| E8 | Aceptación del backend | Backend funcional demostrado de punta a punta | regresión de los 87 | E7 | pendiente |

## Control de cada fase (D-22)

Comando `/fase`; lo comprueba `context/validar_kg.py`. Mientras rija D-24 las puertas se registran como delegadas, con revisión humana pendiente.

1. **Reafirmar:** comprobar con evidencia que se sigue en el camino correcto y dar un dictamen.
2. **Planear:** criterios por RF, contrato, riesgos y permisos en `context/etapas/etapa-N.md`.
3. **Puerta A:** el usuario aprueba. Sin ella no se construye.
4. **Construir y comprobar:** prueba primero, regresión acumulada y auditor.
5. **Puerta B:** el usuario cierra con evidencia. Sin ella no empieza la fase siguiente.

| Fase | Qué se reafirma al planear | Sale cuando |
|---|---|---|
| E2 | las 52 pruebas reales antes de tocar el esquema, S3 (Alembic) y las versiones de las dependencias | una base vacía migra igual a `bd/schema.sql` con owner sin superusuario, cada defecto de E2 pasa de rojo a verde y la entrada funciona por HTTPS |
| E3 | la especificación con ejemplos a mano antes de programar y que el cliente no decide nada | los recorridos esperados coinciden, 1 000 pares concurrentes dan 0 duplicados, un fallo en cada escritura no deja cambios y cada contenido inválido se rechaza |
| E4 | criterios de H04 y H05, orden causal y D-29 (CONF-21) | tres recorridos dan los resultados calculados a mano, nada filtra respuestas, efectos o reglas antes de tiempo y nada califica a la persona |
| E5 | el contrato de tokens de Cognito y qué queda simulado | los tokens inválidos se rechazan, la vinculación concurrente deja una primera sesión y una ruta sin caso de acceso ajeno hace fallar la suite |
| E6 | el texto del Aviso contra lo implementado, el riesgo residual de reidentificación y RN-20 | el agregado es igual antes y después de borrar, opuesto y menor no dejan copia, 9 se suprime y 10 se muestra, y los cruces por xmin u orden no identifican |
| E7 | calendario de inhábiles, efecto de «limitación» y verificación manual sin correo, que decide el usuario | un escenario creado solo por API se juega completo, los seis derechos funcionan en sus plazos límite, al cerrar no queda documento y la bitácora no guarda respuestas |
| E8 | los 87 RF uno por uno y toda la deuda abierta | se cumple la definición de backend funcional de este plan |

## Definición de backend funcional

`./scripts/verify` pasa dos veces desde un clon limpio:

1. Levanta Compose vacío, migra y siembra la demostración.
2. Corre las pruebas SQL, unitarias y de caja negra por HTTPS, sin importar la aplicación en estas últimas.
3. Recorre la experiencia: entrada, pre-test, escenario, evaluaciones, resumen, encuesta, cuenta, descarga y baja.
4. Recorre la administración: contenido, publicación, ARCO, tareas programadas y reporte.
5. Falla si alguno de los 87 RF del KG no tiene prueba ejecutada.
6. Falla al sabotear idempotencia, filtro de dueño, oposición, umbral o bloqueo de publicación.
7. Cumple P95 menor de 200 ms en P5 con 150 usuarios y restaura un respaldo.
8. Imprime commit, lo no probado y cada RF como demostrado, simulado o con interfaz pendiente.

Al final el usuario hace el recorrido manual y el auditor revisa el total.

## Defectos por corregir

Del 2 al 9: reproducidos y corregidos en la base (`bd/pruebas/evidencia-rojo.md`); el 2 sigue abierto para la encuesta (T-16) y el 9 para la vinculación (T-18). El 1: corregido en P5 (T-07). Del 10 al 13: detectados por lectura, sin reproducir (S-03).

| # | Defecto | Arreglo propuesto | Tareas |
|---|---|---|---|
| 1 | P5 rechaza el reintento válido (RN-14) | buscar la decisión antes de validar el nodo actual | T-07 |
| 2 | xmin, orden y transacción ligan los hechos con la persona | copia al cerrar, reescritura aleatoria y jobs sin lectura de hechos | T-09, T-10, T-20 |
| 3 | INSERT de hechos con RETURNING falla | funciones restringidas de archivo y borrado, sin dar SELECT | T-09 |
| 4 | No se puede borrar un administrador que creó o publicó una versión publicada | RESTRICT y desactivar con is_active | T-09 |
| 5 | Se publica sin borrador, se retira un borrador o se altera una versión al retirarla | trigger de INSERT y comparación de la fila completa | T-09 |
| 6 | Carrera entre editar y publicar | bloqueo compartido al editar y exclusivo al publicar | T-09, T-12 |
| 7 | API y panel pueden alterar decisiones, versión, bloqueo e identidad | permisos por columna y triggers | T-09 |
| 8 | Jobs no puede bloquear ni copiar antes de borrar | función única con orden cuenta, participante y sesión | T-09, T-21 |
| 9 | Dos inicios o una vinculación dan dos primeras sesiones | bloquear al participante y recalcular todas | T-10, T-18 |
| 10 | Marcar todas las razones aprueba H05 | mínimo correcto y ninguna incorrecta | T-14 |
| 11 | La reconstrucción revela las respuestas causales | responder antes de ver la reconstrucción | T-15 |
| 12 | El upsert puede recrear una cuenta purgada | rechazar tokens anteriores a la baja | T-18 |
| 13 | ARCO no guarda la verificación ni define la limitación | definir ambos y el calendario hábil | T-25 |

## Tareas

### T-01 · Adoptar la metodología
- Etapa: E0
- Estado: cerrada
- Entregable: kit adaptado, CLAUDE.md integrado, hook instalado y handoff
- Criterios de cierre:
  - `python3 context/validar_kg.py` termina sin errores
  - `git check-ignore HANDOFF.md HISTORIAL.md` lista ambos
  - el usuario confirma el cierre

### T-02 · Términos y Condiciones v1.1
- Etapa: E1
- Estado: pendiente
- Entregable: versión nueva en docs/, sin sobrescribir la 1.0
- Criterios de cierre:
  - cita el Aviso 2.2
  - pide la aceptación antes de la primera sesión (RF-073)
  - cubre el uso sin cuenta y la pérdida del avance al borrar la cookie
  - tiene control de cambios
  - el usuario aprueba el texto y CONF-14 pasa a resuelto

### T-03 · Confirmar las prácticas del reporte técnico
- Etapa: E1
- Estado: pendiente
- Entregable: decisiones del equipo en el KG
- Criterios de cierre:
  - hay decisión sobre KMS, `rds.force_ssl` y Secrets Manager
  - hay decisión sobre enmascarar copias de producción
  - hay decisión sobre los umbrales de escalabilidad
  - si alguna se rechaza, hay versión nueva del reporte

### T-04 · Actualizar los índices en Word
- Etapa: E1
- Estado: pendiente
- Entregable: versiones nuevas de los .docx que lo necesiten
- Criterios de cierre:
  - el usuario decide si el reporte v1, ya reemplazado, se actualiza (decidido en D-12: no)
  - el índice de requerimientos coincide con su contenido
  - el KG registra versión y sha256 nuevos

### T-08 · Activar el plan del backend
- Etapa: E2
- Estado: cerrada
- Nota: Cerrada el 2026-11-22 por delegación (D-24) con EV-01. El usuario no la ha revisado.
- Entregable: KG, vistas, protocolo por fase y validador
- Criterios de cierre:
  - el KG registra D-15 a D-23, E2 a E8, T-05 a T-28 y una fase por RF
  - el validador rechaza una etapa sin Puerta A, una cerrada sin evidencia o Puerta B y un RF sin fase o con dos
  - el usuario confirma el cierre

### T-09 · Decisiones de base y esquema corregido
- Etapa: E2
- Estado: cerrada
- Nota: Cerrada el 2026-11-22 por delegación (D-24) con EV-02. El usuario no la ha revisado.
- Entregable: ADR-007, ADR-008, esquema, modelo y pruebas SQL
- Criterios de cierre:
  - ADR-007 reemplaza a ADR-004 y declara el riesgo residual (D-19 a D-21)
  - ADR-008 fija la estructura y la seguridad de la API
  - cada defecto de E2 tiene una prueba que falló con el esquema anterior
  - ninguna regla se debilita: los cambios a T01, T32, T36 y T39 se aprueban en la Puerta A
  - defecto 2 reproducido y corregido
  - defecto 3 reproducido y corregido
  - defecto 4 reproducido y corregido
  - defecto 5 reproducido y corregido
  - defecto 6 reproducido y corregido
  - defecto 7 reproducido y corregido
  - defecto 8 reproducido y corregido

### T-05 · Base de la API y migración inicial
- Etapa: E2
- Estado: cerrada
- Nota: Cerrada el 2026-11-22 por delegación (D-24) con EV-02. El usuario no la ha revisado.
- Entregable: FastAPI, Compose con TLS local, Alembic y roles
- Criterios de cierre:
  - `alembic upgrade head` crea el esquema en PostgreSQL 16 vacío, con owner sin superusuario
  - el esquema equivale a `bd/schema.sql`
  - pasan las pruebas SQL vigentes, con los cambios aprobados en la Puerta A
  - la API arranca con una conexión por rol

### T-06 · Revisiones automáticas del backend
- Etapa: E2
- Estado: cerrada
- Nota: Cerrada el 2026-11-22 por delegación (D-24) con EV-02. El usuario no la ha revisado.
- Entregable: CI, hooks de Python y `scripts/verify`
- Criterios de cierre:
  - CI corre las pruebas SQL y de la API
  - formato y lint con versión fija
  - `./scripts/verify` falla ante una prueba fallida u omitida

### T-10 · Recorrido de entrada
- Etapa: E2
- Estado: cerrada
- Nota: Cerrada el 2026-11-22 por delegación (D-24) con EV-02. El usuario no la ha revisado.
- Entregable: aceptación, participante y sesión por HTTPS
- Criterios de cierre:
  - sin las tres aceptaciones no hay sesión (RF-073)
  - la cookie cumple RF-062 y la base solo guarda el hash
  - dos inicios simultáneos dejan una primera sesión
  - un prototipo comprueba el archivo anónimo sin vínculo por xmin u orden
  - defecto 2 reproducido y corregido
  - defecto 9 reproducido y corregido

### T-11 · Especificación del motor
- Etapa: E3
- Estado: cerrada
- Nota: Especificación aceptada por delegación (D-24), sin revisión del usuario. Se comprueba con los ejemplos en T-07.
- Entregable: ADR-009 con ejemplos calculados a mano
- Criterios de cierre:
  - define condiciones, efectos, precedencia y causas
  - define el avance sin decisión y los ciclos
  - el usuario la aprueba antes de programar el motor

### T-07 · Motor de simulación
- Etapa: E3
- Estado: cerrada
- Nota: Cerrada el 2026-11-22 por delegación (D-24, D-32): PR #10, caja negra y auditoría sin bloqueos. Sin revisión humana.
- Entregable: motor puro, proceso P5, avance y reanudación
- Criterios de cierre:
  - cada proceso tiene pruebas
  - confirmar es idempotente aunque el nodo haya avanzado (ADR-003, RN-14)
  - 1 000 pares concurrentes dan 0 duplicados (S4)
  - el cliente no determina consecuencias (ARQ)
  - defecto 1 reproducido y corregido

### T-12 · Validación y publicación
- Etapa: E3
- Estado: pendiente
- Entregable: validador de RF-066 y proceso P12
- Criterios de cierre:
  - cada tipo de contenido inválido se rechaza
  - editar y publicar a la vez no altera una versión publicada
  - defecto 6 reproducido y corregido

### T-13 · Escenario de demostración
- Etapa: E3
- Estado: pendiente
- Entregable: contenido ficticio completo
- Criterios de cierre:
  - 8 decisiones, 3 variables, 2 eventos, 3 desenlaces y sus evaluaciones
  - está marcado como demostración y pasa RF-066

### T-14 · Evaluaciones
- Etapa: E4
- Estado: pendiente
- Entregable: pre-test, post-test, transferencia y causal
- Criterios de cierre:
  - las puntuaciones coinciden con las calculadas a mano
  - marcar todas las razones no aprueba H05
  - las respuestas correctas no salen antes de tiempo
  - defecto 10 reproducido y corregido

### T-15 · Reconstrucción y resumen
- Etapa: E4
- Estado: pendiente
- Entregable: recorrido causal, retroalimentación, referencias y resumen
- Criterios de cierre:
  - las preguntas causales se responden antes de ver la reconstrucción
  - solo atribuye relaciones del contenido y nada califica a la persona
  - defecto 11 reproducido y corregido

### T-16 · Encuesta no vinculada
- Etapa: E4
- Estado: pendiente
- Entregable: encuesta de RF-060
- Criterios de cierre:
  - CONF-21 resuelto por el usuario
  - la respuesta no se liga a la sesión ni a la cuenta

### T-17 · Verificación de tokens
- Etapa: E5
- Estado: pendiente
- Entregable: verificador OIDC y emisor simulado aparte
- Criterios de cierre:
  - rechaza firma, emisor, audiencia, tipo, vencimiento y grupo inválidos
  - el emisor no entra en la imagen de la API

### T-18 · Cuenta y vinculación
- Etapa: E5
- Estado: pendiente
- Entregable: cuenta, consentimientos y proceso P10
- Criterios de cierre:
  - la vinculación concurrente es idempotente y deja una primera sesión
  - un token anterior a la baja no recrea la cuenta
  - defecto 9 reproducido y corregido
  - defecto 12 reproducido y corregido

### T-19 · Aislamiento y CSRF
- Etapa: E5
- Estado: pendiente
- Entregable: protección de todas las rutas
- Criterios de cierre:
  - cada ruta tiene un caso de acceso ajeno
  - una escritura de origen ajeno se rechaza

### T-20 · Derechos del participante
- Etapa: E6
- Estado: pendiente
- Entregable: descarga, oposición, bloqueo y borrado
- Criterios de cierre:
  - se agrega antes de bloquear, salvo oposición o minoría de edad
  - el bloqueo es terminal y purgar solo borra
  - defecto 2 reproducido y corregido

### T-21 · Caducidad y purgas
- Etapa: E6
- Estado: pendiente
- Entregable: tareas idempotentes con fecha inyectable
- Criterios de cierre:
  - se prueban los límites de 30 días, 12 meses y 90 días
  - repetir una tarea o cruzarla con una petición no duplica ni pierde datos
  - defecto 8 reproducido y corregido

### T-22 · Reportes agregados
- Etapa: E6
- Estado: pendiente
- Entregable: reportes con aciertos por tema y abandono
- Criterios de cierre:
  - el agregado es igual antes y después de borrar
  - con 9 se suprime y con 10 se muestra
  - dos cortes no permiten despejar a una persona

### T-23 · Acceso administrativo
- Etapa: E7
- Estado: pendiente
- Entregable: autorización por grupo y bitácora
- Criterios de cierre:
  - sin el grupo de administradores no hay acceso
  - la bitácora no guarda respuestas ni secretos

### T-24 · API de contenido
- Etapa: E7
- Estado: pendiente
- Entregable: crear, editar, copiar, validar, publicar y retirar
- Criterios de cierre:
  - un escenario creado solo por API se juega completo
  - lo publicado no se edita

### T-25 · API de derechos ARCO
- Etapa: E7
- Estado: pendiente
- Entregable: solicitudes, plazos, verificación y documentos
- Criterios de cierre:
  - el usuario decidió el calendario, la limitación y la verificación manual
  - los seis derechos se prueban en sus plazos límite
  - al cerrar no queda documento
  - defecto 13 reproducido y corregido

### T-26 · Matriz de aceptación
- Etapa: E8
- Estado: pendiente
- Entregable: matriz de RF, RN, RNF, OR e interfaces, y sabotajes
- Criterios de cierre:
  - los 87 RF tienen prueba ejecutada y estado declarado
  - cada sabotaje hace fallar la suite

### T-27 · Seguridad y operación local
- Etapa: E8
- Estado: pendiente
- Entregable: seguridad, carga, logs, respaldo y restauración
- Criterios de cierre:
  - P5 cumple P95 menor de 200 ms con 150 usuarios
  - restaurar no resucita a quien se dio de baja

### T-28 · Entrega del backend
- Etapa: E8
- Estado: pendiente
- Entregable: guía local, OpenAPI y procedimiento de dependencias
- Criterios de cierre:
  - la guía funciona desde un clon limpio
  - RNF-16 tiene responsable y frecuencia
  - el usuario completa el recorrido manual

## Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Publicar datos personales (D-09) | Un push público no se puede deshacer del todo | ADR-006 y búsqueda de datos personales antes de cada push |
| El equipo no conoce o no acepta las reglas (S-01) | Commits y ramas fuera del método | Confirmarlo con ambos integrantes |
| Sin fechas ni rúbrica (D-16) | Prioridades equivocadas | Pedirlas cuando el usuario retome el tema |
| S1–S5 se validaron en otros proyectos, no en este | RDS, Cognito o Alembic pueden fallar aquí | S3 a S5 se prueban en local; S1 y S2 quedan fuera (S-04) |
| El mismo asistente escribe código y pruebas | Pruebas que confirman el error | Criterios aprobados antes, resultados a mano, sabotajes y auditor |
| Anonimato imperfecto con 50 personas | Reidentificación | Riesgo residual declarado en ADR-007 |
| Cambios al tratamiento de datos | Aviso o reporte desfasados | Contraste en E6; el texto lo decide el usuario |
| Docker o permisos denegados | Pruebas sin ejecutar | Detenerse y reportar; nada se da por probado |
