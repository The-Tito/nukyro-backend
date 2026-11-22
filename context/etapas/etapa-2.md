# Etapa 2 · Base ejecutable y entrada: análisis y plan

> Estado: delegado el 2026-11-22 (D-24), con revisión humana pendiente. Tareas: T-09, T-05, T-06, T-10. Decisiones: D-15 a D-25. Supuestos: S-03, S-04.

## Objetivo

Esquema corregido que migra desde una base vacía y primer recorrido HTTPS: aceptar documentos, crear participante,
iniciar y consultar una sesión. **No incluye** motor, evaluaciones, cuentas, reportes completos ni panel.

## Reafirmación

| Pregunta | Evidencia | Resultado |
|---|---|---|
| ¿Sigue funcionando lo anterior? | Esquema, semilla y pruebas en un PostgreSQL 16.15 vacío | 52 PASS, 0 FAIL |
| ¿El objetivo sigue siendo el del KG? | Validador; RF-001 a 004, 062, 068, 071, 073 se planean en E2 | Sí |
| ¿Lo construido coincide con lo decidido? | `bd/schema.sql` contra D-19 a D-21 y los 13 defectos | No: es lo que corrige E2 |
| ¿Cuánto falta de verdad? | No hay código de aplicación | 0 demostrados, 0 simulados, 87 pendientes |
| ¿Qué aprendimos que cambie el plan? | Docker funciona; §7 del modelo no describe los procesos de entrada; la base no comprueba RF-073 | Ajuste: se definen aquí |

S3 (Alembic) sigue sin probar en este proyecto: se prueba en T-05.

## Dictamen

**Con ajuste.** Cambia el cómo (procesos de entrada y pruebas que fijaban el diseño viejo), no el alcance.

## Análisis

| Paso | Opciones | Elegida y por qué |
|---|---|---|
| Archivo anónimo | INSERT desde la API; funciones del owner | **Funciones:** ningún rol de conexión necesita leer ni escribir hechos |
| Vínculo por xmin u orden | Aceptarlo; lote programado; reescribir al archivar | **Reescribir** las tablas de hechos con id nuevo y orden aleatorio: un lote conservaría datos que D-20 no permite usar |
| Primera sesión | En la aplicación; en la base | **Base:** el trigger bloquea al participante y calcula el valor |
| Aceptación previa | Guardar antes del participante; una transacción | **Una transacción:** participante y tres aceptaciones nacen juntos (RF-062, RF-073) |
| Acceso a datos | ORM; SQL explícito | **SQL explícito** con SQLAlchemy Core: los bloqueos y permisos por columna quedan a la vista |
| Migración | Autogenerar; SQL congelado | **SQL congelado:** Alembic no genera funciones, triggers ni permisos. Se compara con `bd/schema.sql` |
| Documentos | Textos reales; ficticios | **Ficticios** con versión `DEMO-` (D-17). CONF-14 no se resuelve aquí |

Conceptos: una función `SECURITY DEFINER` corre con los permisos de su dueño, por eso fija `search_path` y no es
ejecutable por PUBLIC. `xmin` es la transacción que escribió una fila: dos filas con el mismo valor nacieron juntas.

## Criterios por RF

Las pruebas de API son de caja negra por HTTPS y no importan la aplicación.

| RF | Caso positivo | Caso negativo | Prueba |
|---|---|---|---|
| RF-001 | Con participante válido se crea una sesión: 201 | Sin cookie: 401; escenario inexistente: 404; nada se escribe | `tests/blackbox` |
| RF-002 | Dos sesiones reciben UUID distintos | Un `id` enviado por el cliente se rechaza: 422 | `tests/blackbox` |
| RF-003 | La sesión devuelve escenario y versión publicada, y los conserva al retirarla | Un `version_id` enviado se rechaza; borrador o retirada no inician | `tests/blackbox`, SQL |
| RF-004 | `started_at` lo pone el servidor, en UTC | Un `started_at` enviado se rechaza: 422 | `tests/blackbox` |
| RF-062 | Cookie `__Host-` Secure, HttpOnly, SameSite, Path=/; en la base solo SHA-256 | Cookie alterada: 401; sesión ajena: 404; el secreto no sale en cuerpo ni logs | `tests/blackbox`, `tests/integration` |
| RF-068 | Sin cookie se consultan responsable, categorías, finalidades, plazo y contacto, marcados como demo | Consultarlos no crea filas ni emite cookie | `tests/blackbox` |
| RF-071 | El escenario sembrado está marcado como demostración y vive en tablas de contenido | La API no puede escribir contenido; crear una sesión no altera el contenido | `tests/integration`, SQL |
| RF-073 | Tres aceptaciones con versión y fecha en una transacción | Falta una, es falsa o la versión no es la vigente: 422 y cero filas; sin las tres no hay sesión | `tests/blackbox`, `tests/integration` |

## Contrato y esquema

| Método y ruta | Entrada | Salida |
|---|---|---|
| `GET /api/v1/health` | | 200 si la base responde; 503 si no |
| `GET /api/v1/entry` | | 200: aviso de datos, documentos con versión, escenarios publicados |
| `POST /api/v1/participants` | `age_confirmed`, `privacy_notice_version`, `terms_version` | 201 y cookie; si ya hay cookie válida, 200 sin crear otro |
| `POST /api/v1/sessions` | `scenario_key`, `self_reported_first` | 201: sesión |
| `GET /api/v1/sessions` | | 200: sesiones propias |
| `GET /api/v1/sessions/{id}` | | 200: sesión; 404 si es ajena o no existe |

Toda escritura exige `Origin` exacto y `X-Nukyro-Request: 1`; si no, 403. Todo campo desconocido da 422.

| Defecto | Se reproduce con | Cambio al esquema |
|---|---|---|
| 2 | `xmin` de hechos igual al del participante | ADR-007: archivo por función, reescritura y copia solo al cerrar |
| 3 | INSERT RETURNING como API: 42501 | Sin INSERT directo de hechos |
| 4 | Borrar al administrador que publicó: 23514 | FK RESTRICT; sin DELETE de administradores |
| 5 | INSERT publicado; retirar un borrador; alterar al retirar | Trigger de INSERT y comparación de la fila completa |
| 6 | Editar mientras otra transacción publica | `FOR SHARE` sobre la versión al editar |
| 7 | API cambia decisión, versión, bloqueo o identidad | Permisos por columna y triggers de campos inmutables |
| 8 | jobs no puede archivar ni bloquear sin leer hechos | Funciones con orden cuenta, participante, sesión |
| 9 | Dos inicios simultáneos: dos primeras sesiones | Trigger que bloquea al participante |

Cambios a pruebas existentes. Ninguno debilita una regla:

| Prueba | Antes | Después |
|---|---|---|
| T01 | Inserta una segunda versión publicada | Publica un borrador con otra publicada: sigue 23505. Insertar publicado se prueba aparte |
| T31 | Usa `closure_reason` | La misma regla, sin la columna retirada |
| T32 | API inserta y no modifica hechos | API no inserta, lee ni modifica hechos |
| T36 | Analítica lee filas de hechos | Analítica no lee filas; solo función agregada con umbral de 10 |
| T38 | jobs borra con DELETE | La misma cascada, mediante la función |
| T39 | Hechos insertados a mano sobreviven | Los hechos archivados por la función sobreviven |

## Riesgos

- El anonimato con 50 personas no es absoluto: riesgo residual en ADR-007.
- Lo local no demuestra RDS ni Cognito (S-04).
- El mismo asistente dirige código y pruebas: otro modelo audita y los defectos se ven fallar antes de corregirlos.
- Sin revisión humana en las puertas (D-24): cada una se marca como delegada.

## Plan breve

| Paso | Qué | Entregable | Cómo se verifica |
|---|---|---|---|
| T-09 | Pruebas rojas, ADR y esquema | `bd/`, ADR-007, ADR-008 | Pruebas SQL y de concurrencia |
| T-05 | API, Compose con TLS, Alembic, roles | `src/`, `migrations/`, `compose.yaml` | Base vacía igual al esquema |
| T-06 | CI, hooks y verificación | `.github/`, `scripts/verify` | Una prueba fallida u omitida da rojo |
| T-10 | Recorrido de entrada | módulo de entrada | Criterios por RF por HTTPS |

## Puerta A

**Delegada el 2026-11-22 (D-24).** Nadie revisó este documento antes de construir. Cubre los criterios y cambios de
pruebas de arriba, commits y PR de la fase, Docker local desechable, la imagen de Caddy para el TLS local y las
dependencias del plan §7 con versión fija: uv, FastAPI, Uvicorn, SQLAlchemy 2, Alembic, psycopg 3, PyJWT, pytest, httpx y ruff.
No cubre AWS, textos legales reales, datos personales ni conflictos.

## Puerta B

**Delegada el 2026-11-22 (D-24), sin revisión humana.** Evidencia: EV-02 (commit `ee25eef`).

- **Comprobar:** `./scripts/verify`. Esperado: `verify OK` con sql=242, unit=14, integration=26, blackbox=40.
- **Demostrados:** RF-001 a RF-004, RF-062 y RF-071. **Backend demostrado, interfaz pendiente:** RF-068 y RF-073. 8 de 87.
- **S3:** Alembic migra una base vacía igual a `bd/schema.sql`, con owner sin superusuario.
- **No probado:** RDS y Cognito (S-04); el orden físico aleatorio de los hechos; el recorrido manual del usuario.
- **Sigue abierto:** defecto 2 en la encuesta (T-16, CONF-21) y defecto 9 en la vinculación (T-18).
