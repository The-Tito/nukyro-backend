# Bitácora

Lo más reciente va al final. Formato de cada entrada:

    ## AAAA-MM-DD: T-xx, paso
    - **Resultado:** qué se hizo y qué resultó, con errores y descartes.
    - **Revisión:** cómo se comprobó y quién lo confirmó.
    - **Decisiones:** IDs.
    - **Evidencia:** rutas, PR, comandos.

## 2026-11-22: adopción, instalación
- **Resultado:** kit instalado y adaptado al KG existente (v1.14.0). Se retiró el `context/kg.json` del kit, se corrigió la ruta de REPORTE-BD-V2 y se copió el handoff a la raíz. Se descartó un repositorio aparte para la base.
- **Revisión:** `python3 context/validar_kg.py`. Pruebas SQL no ejecutadas (Docker apagado, esquema sin cambios). El usuario aún no confirma el cierre.
- **Decisiones:** D-01 a D-07, A-01, A-02, S-01.
- **Evidencia:** `context/proyecto/kg.json` (`meta.historial`).

## 2026-11-22: T-01, integración y cierre de sesión
- **Resultado:** CLAUDE.md integrado, context/HANDOFF.md retirado, correo noreply local, plan y análisis de E1 propuestos. El usuario rechazó hacer privado el repositorio: eso choca con D-05 y queda como A-03. Se quitaron de fuentes.md las rutas con nombres y matrículas.
- **Revisión:** validador, inventario de datos personales y ensayo de hooks en una copia. Sin agente auditor (revisión hecha por el mismo asistente). Pruebas SQL no ejecutadas. T-01 espera la confirmación del usuario.
- **Decisiones:** D-08 (cierra A-02), A-03.
- **Evidencia:** KG v1.15.0, `context/plan.md`, `context/etapas/etapa-1.md`. Sin commits ni push.

## 2026-11-22: T-01, paso 1, decisiones
- **Resultado:** el usuario aceptó las recomendaciones, delegó los PR y su fusión hasta nuevo aviso y eligió fusión local para conservar la firma de D-10.
- **Revisión:** decisiones confirmadas por el usuario.
- **Decisiones:** D-09 a D-13, ADR-006; A-03 cerrada y D-05 reemplazada.
- **Evidencia:** KG v1.16.0 (`meta.historial`), `context/decisiones.md`.

## 2026-11-22: T-01, paso 2, seudonimización
- **Resultado:** KG y ADR sin nombres, matrículas ni correo; docs/ y la guía .docx fuera de git; validador adaptado. Su primera versión falló con la ñ descompuesta de macOS y se corrigió comparando en NFC. Originales respaldados en versiones/ (solo local, misma máquina).
- **Revisión:** comparación del KG contra el respaldo; validador probado sin docs/, con sha256 alterado, patrón ambiguo, documento faltante y DDL faltante; 10 PNG revisados visualmente; 52/52 pruebas SQL en PostgreSQL 16.15.
- **Decisiones:** D-09, D-13.
- **Evidencia:** KG v1.17.0, `context/validar_kg.py`, `bd/pruebas/README.md`.

## 2026-11-22: T-01, paso 3, auditoría y cierre
- **Resultado:** el agente auditor (40 puntos) bloqueó el push por dos hallazgos y el cierre por otros. Se corrigieron: HANDOFF e HISTORIAL en .gitignore, grupo escolar y prefijos de matrícula omitidos (D-14), validador compatible con Python 3.9 y sin comodines fuera de lo local, espera en el README de pruebas. Los commits se rehicieron en una rama limpia antes de publicar. T-01 y E0 cerradas (D-12); el handoff se reescribe al cerrar la sesión.
- **Sin corregir, para decidir:** CLAUDE.md no detalla el push inicial de D-11; la skill evaluar-motor-bd guarda en docs/, que ya no se versiona; ningún hook revisa datos personales ni la identidad de git; el validador no compara el texto de las vistas; main no tiene el KG hasta el primer release, así que su hook fallaría. E0 no tuvo etapa-0.md porque la adopción fue anterior al método.
- **Revisión:** correcciones comprobadas por el mismo asistente, sin segunda auditoría: validador en 3.9 y 3.13, cuatro casos que deben fallar, comandos del README con 52/52 en PostgreSQL 16.15.
- **Decisiones:** D-14, S-02.
- **Evidencia:** KG v1.19.0, PR de feature/T-01-metodologia.

## 2026-11-22: análisis del estado del proyecto
- **Resultado:** sin código de aplicación, plan con tarea para 27 de 87 RF y defectos de diseño hallados por lectura (luego 13, con la revisión del agente de planeación). Las pruebas SQL **no se ejecutaron**: Docker estaba apagado y el control de permisos bloqueó dos veces un PostgreSQL temporal; no se insistió.
- **Revisión:** validador del KG, hooks y gitleaks en un clon, escáner de datos personales sobre las ramas publicadas (0 hallazgos). Los defectos no se reprodujeron (S-03).
- **Decisiones:** ninguna.
- **Evidencia:** `MODELO-DATOS.pendientes` del KG.

## 2026-11-22: T-08, plan del backend
- **Resultado:** el usuario respondió ocho preguntas y aprobó el plan E2 a E8. Un agente de planeación revisó el diseño.
- **Revisión:** reparto de los 87 RF comprobado por script, sin huecos ni repetidos.
- **Decisiones:** D-15 a D-23, CONF-15 a CONF-21, CA-01 a CA-03, S-03, S-04.
- **Evidencia:** `context/plan.md`, KG v1.20.0.

## 2026-11-22: T-08, en pausa y cierre de sesión
- **Resultado:** el usuario pidió no empezar el plan y retomarlo en otro chat. El mensaje llegó con el registro en el KG y las vistas ya escrito: se conservó sin commit. No se instalaron `/fase`, la plantilla, el cambio de CLAUDE.md ni las reglas del validador; no se programó nada.
- **Revisión:** validador, comparación del KG contra HEAD (0 nodos y 0 aristas perdidos) y de las vistas contra el KG. Sin auditor ni revisión humana del diff. T-08 sigue abierta.
- **Decisiones:** pausa registrada en la nota de T-08.
- **Evidencia:** rama local feature/T-08-plan-backend, KG v1.20.1.

## 2026-11-22: T-08, protocolo instalado y ejecución delegada
- **Resultado:** el usuario delegó la ejecución (D-24). Quedaron `/fase`, la plantilla, CLAUDE.md, `retomar` y las reglas del validador. Seguro local del límite de 5 horas al 96%.
- **Revisión:** 12 casos de `context/pruebas/probar_validador.py` y rechazos repetidos sobre una copia del KG real. Sin revisión humana.
- **Decisiones:** D-24, D-25.
- **Evidencia:** línea base SQL 52/52 en PostgreSQL 16.15, antes de tocar el esquema.

## 2026-11-22: T-08, auditada y cerrada por delegación; Puerta A de E2
- **Resultado:** T-08 cerrada con EV-01. E2 planeada en `context/etapas/etapa-2.md` y en curso.
- **Revisión:** auditor con Sonnet sin bloqueos; se completó la cita de D-24. Revisión humana pendiente.
- **Decisiones:** Puerta A de E2 delegada (D-24).
- **Evidencia:** EV-01, KG v1.23.0.

## 2026-11-22: T-09, esquema v0.3
- **Resultado:** ADR-007 y ADR-008, defectos 2 a 9 corregidos en la base, funciones de archivo y permisos por columna.
- **Revisión:** la dirección repitió la suite, reprodujo el defecto 2 y halló dos fallos más (reabrir y completar un intento enviado), de rojo a verde. Sin revisión humana.
- **Decisiones:** ADR-004 reemplazada por ADR-007.
- **Evidencia:** `bd/pruebas/ejecutar.sh`: 239 comprobaciones; `bd/pruebas/evidencia-rojo.md`.

## 2026-11-22: T-05, base de la API
- **Resultado:** FastAPI con una conexión por rol, Compose con HTTPS y migración inicial congelada (PR #4).
- **Revisión:** la dirección leyó el código. La prueba de equivalencia contra `bd/schema.sql` pasa y detecta un GRANT de más.
- **Decisiones:** ADR-008.
- **Evidencia:** `./scripts/verify`, integración; S3 comprobado en local.

## 2026-11-22: T-06, verificación y CI
- **Resultado:** `scripts/verify`, CI y hooks de Python (PR #5).
- **Revisión:** se quitó una variable que permitía sustituir las pruebas SQL y se corrigió el conteo de suites.
- **Decisiones:** ninguna.
- **Evidencia:** sabotajes con exit 1: una prueba fallida (paso integration) y una omitida (paso unit, «no se admiten skipped»). CI en verde.

## 2026-11-22: T-10, recorrido de entrada
- **Resultado:** aceptación, participante y sesión por HTTPS, con contenido de demostración (PR #6).
- **Revisión:** la auditoría de E2 con Opus halló 5 bloqueos, atendidos en el PR #7. El principal, de rojo a verde: al cambiar la versión de un documento, quien tenía cookie no podía volver a aceptar.
- **Decisiones:** excepción de CSRF en los GET, declarada en ADR-008.
- **Evidencia:** prueba del orden físico vista fallar al quitar el orden aleatorio; dos inicios simultáneos dejan una primera sesión.

## 2026-11-22: E2 cerrada por delegación
- **Resultado:** Puerta B delegada (D-24). 8 de 87 RF: 6 demostrados y 2 con interfaz pendiente.
- **Revisión:** auditor con Opus, hallazgos atendidos; no se volvió a auditar después del arreglo. Sin revisión humana.
- **Decisiones:** ninguna.
- **Evidencia:** EV-02: `./scripts/verify` con sql=242, unit=14, integration=26, blackbox=40.

## 2026-11-22: E3 planeada y T-11, especificación del motor
- **Resultado:** Puerta A de E3 delegada y ADR-009 con cuatro recorridos calculados a mano.
- **Revisión:** `./scripts/verify` en verde sobre develop (705dd90) antes de planear. Sin auditor ni revisión humana de ADR-009.
- **Decisiones:** ADR-009.
- **Evidencia:** `context/etapas/etapa-3.md`.
- **Auditoría de T-11:** Sonnet recalculó los cuatro ejemplos; 5 observaciones sin bloqueo, precisadas en ADR-009.

## 2026-11-22: T-07 a medias y cierre de sesión por límite de uso
- **Resultado:** motor puro y P5 con sus rutas, en `feature/T-07-motor`, sin fusionar.
- **Revisión:** la dirección corrigió de rojo a verde tres fallos del motor (un evento en la ruta no avanzaba, variables sin límite, justificación no pedida) y uno de P5 (no renovaba la actividad: RF-080 habría borrado a alguien activo).
- **Decisiones:** ninguna. Pendiente: qué hace una versión sin pre-test al llegar al desenlace (el CHECK lo exige y hoy da 409).
- **Evidencia:** `./scripts/verify` con sql=242, unit=59, integration=45, blackbox=40. Sin caja negra de E3 ni auditor.

## 2026-11-22: sesión retomada y respuestas del usuario
- **Resultado:** el usuario aceptó las recomendaciones pendientes y pidió continuar. Había fusionado el PR #10 con el botón de GitHub, lo que expuso datos de su perfil en e8dbae5: decidió dejarlo.
- **Revisión:** alcance comprobado: un solo commit remoto, main limpio, sin forks, mismo árbol que d6ab902.
- **Decisiones:** D-26 a D-31, CONF-21 resuelto. S-02 sigue por verificar: no se indicó dónde está el respaldo.
- **Evidencia:** escáner acotado con `^e8dbae5`: 0 hallazgos.

## 2026-11-22: T-07 cerrada y D-32
- **Resultado:** caja negra de E3, matriz `tests/trazabilidad-e3.md` y prueba de vivacidad. El usuario pidió continuar hasta finalizar el backend.
- **Revisión:** auditor con Sonnet sin bloqueos; se agregó la carrera con alternativas distintas y se precisó ADR-009.
- **Decisiones:** D-32.
- **Evidencia:** `./scripts/verify`; 1 000 pares concurrentes con 0 duplicados (S4) y un fallo inyectado en cada escritura sin cambios.

## 2026-11-22: T-12, validación y publicación
- **Resultado:** validador de RF-066 (23 códigos) y P12, con pre-test obligatorio.
- **Revisión:** la dirección corrigió de rojo a verde que el validador rechazaba eventos en la ruta y no revisaba sus salidas. Auditor con Sonnet sin bloqueos.
- **Decisiones:** D-28 aplicada.
- **Evidencia:** `./scripts/verify`; dos sabotajes del bloqueo hicieron fallar la carrera editar contra publicar.
- **Escáner:** un correo ficticio en `example.invalid` detuvo el push de T-12. Se cambió a `example.test` y la rama se rehízo desde develop sin tocar el escáner; la anterior nunca se subió.

## 2026-11-22: T-13, escenario de demostración
- **Resultado:** DEMO-BECAS ficticio (8 decisiones, 3 variables, 2 eventos, 3 desenlaces, evaluaciones 6, 6, 5 y 5), sembrado por P12.
- **Revisión:** la primera auditoría de E3 con Opus dio 8 bloqueos y la reauditoría 4: conteos del instrumento, claves falsas en algunas rutas, introducción oculta y pistas de forma que aprobaban a ciegas. La verificación final no dejó bloqueos. La dirección halló además una siembra que borraba borradores.
- **Decisiones:** precisiones de ADR-009.
- **Evidencia:** prueba sobre las 6 561 rutas; 15 estrategias ciegas antes, 0 después.

## 2026-11-22: E3 cerrada por delegación
- **Resultado:** Puerta B delegada (D-32). 39 de 87 RF. El release a main no se hizo: llevaría e8dbae5 a main (A-04).
- **Revisión:** tres auditorías de la fase. Sin revisión humana.
- **Decisiones:** A-04 abierta.
- **Evidencia:** EV-03: `./scripts/verify` con sql=242, unit=188, integration=108, blackbox=61.

## 2026-11-22: E4 planeada
- **Resultado:** Puerta A delegada y criterios en `context/etapas/etapa-4.md`.
- **Revisión:** `./scripts/verify` en verde sobre develop (b44b08b). Sin revisión humana.
- **Decisiones:** A-05 abierta, sin bloquear RF-060.
- **Evidencia:** plan de la fase.

## 2026-11-22: T-14, evaluaciones
- **Resultado:** pre-test, post-test, transferencia y causal por API; hitos de una sola escritura en la base.
- **Revisión:** la dirección cerró de rojo a verde una fuga: la puntuación salía al enviar cada evaluación y revelaba respuestas. T30 se adaptó al trigger sin cambiar su regla.
- **Decisiones:** la puntuación se ve al terminar todas las evaluaciones.
- **Evidencia:** `./scripts/verify` con sql=256, unit=217, integration=129, blackbox=69; defecto 10 visto en rojo.

## 2026-11-22: T-15, reconstrucción y resumen
- **Resultado:** resumen con historial, causas guardadas, retroalimentación, referencias y resultados por evaluación (PR #15).
- **Revisión:** la auditoría de E4 halló pruebas que no afirmaban lo declarado; se agregó integración con valores exactos.
- **Decisiones:** ninguna.
- **Evidencia:** defecto 11 y filtro por alternativa vistos en rojo, también por la dirección (`tests/evidencia-rojo-e4.md`).

## 2026-11-22: T-16, encuesta no vinculada
- **Resultado:** `submit_survey`; la API ya no inserta encuestas directamente. Opuesto: no se ofrece ni se acepta (D-29).
- **Revisión:** diff de la función y de D2-07 y D3-08, que fijaban el INSERT viejo.
- **Decisiones:** A-05 sigue abierta.
- **Evidencia:** 13 pruebas SQL nuevas (xmin común y orden físico).

## 2026-11-22: E4 cerrada por delegación
- **Resultado:** Puerta B delegada (D-32). 70 de 87 RF.
- **Revisión:** auditoría con Opus (3 bloqueos) y verificación final sin bloqueos. Sin revisión humana.
- **Decisiones:** ninguna.
- **Evidencia:** EV-04: `./scripts/verify` con sql=269, unit=217, integration=140, blackbox=77.

## 2026-11-22: cierre de la segunda sesión autónoma
- **Resultado:** E3 y E4 cerradas por delegación (PR #11 a #16). 70 de 87 RF; siguen E5 a E8. Se cerró al 85 % del límite de 5 horas: una tarea de E5 no cabía antes del seguro del 96 %.
- **Revisión:** validador, vistas y KG al día; sin PR abiertos antes de este. Sin revisión humana del código, las puertas ni los textos.
- **Decisiones:** esperan al usuario A-04 (release) y A-05 (encuesta). S-02 sigue por verificar.
- **Evidencia:** EV-03, EV-04, KG v1.36.0.

## 2026-11-22: E5 planeada y D-33
- **Resultado:** `context/etapas/etapa-5.md`, Puerta A delegada (D-32). Dictamen: con ajuste.
- **Revisión:** verify sobre develop en d54c24a (sql=269, unit=217, integration=140, blackbox=77) y validador en verde. Sin revisión humana.
- **Decisiones:** D-33 del usuario (sin multiagentes, modifica D-25; CLAUDE.md y `fase.md` ajustados). Declaradas: D-34 (token de identidad y emisor aparte) y D-35 (defecto 12 por edad del token). Abierta: A-06 (plazo mínimo de bloqueo).
- **Evidencia:** KG v1.37.0.

## 2026-11-22: T-17 construida, pendiente de auditoría
- **Resultado:** `src/nukyro/identity.py` (RS256 con JWKS, emisor, audiencia, `token_use=id`, vencimiento, edad y vida de 1 hora según D-35, grupo `admins`), `load_oidc_settings`, emisor simulado en `devtools/issuer/` con su contenedor y PyJWT 2.15.1 fijado. Faltar el emisor o la audiencia impide arrancar la API.
- **Revisión:** `./scripts/verify`: sql=269, unit=254, integration=157, blackbox=77. Ocho sabotajes del verificador hacen fallar las pruebas. Falta la auditoría en Opus (D-33); T-17 sigue en curso.
- **Decisiones:** sin descubrimiento OIDC: la URL de claves por omisión es `{emisor}/.well-known/jwks.json`. Anotado: Cognito real debe fijar el token de identidad en 1 hora o menos.
- **Evidencia:** pruebas `tests/unit/test_identity.py` y `tests/integration/test_identity.py`.

## 2026-11-22: T-17 auditada y cerrada
- **Resultado:** T-17 cerrada por delegación (D-32). Cumple sus dos criterios: rechaza firma, emisor, audiencia, tipo, vencimiento y grupo inválidos, y el emisor no entra en la imagen de la API.
- **Revisión:** auditoría en la sesión con Opus (D-33), sin agentes. Dos hallazgos, corregidos:
  1. `JwksCache` reintentaba en cada petición con el emisor caído, y con el candado puesto cada petición esperaba su propio tiempo de espera. Ahora espera 10 s tras un fallo y conserva las claves anteriores.
  2. La prueba de integración del emisor caído usaba un token mal formado y nunca llegaba a pedir las claves. Ahora usa un token real y espera `jwks_unavailable`.
- **Sabotajes:** la imagen de la API con `devtools/` copiado dentro es detectada por la misma búsqueda de la prueba. Quitar la espera tras fallo hace fallar su prueba. Se repitieron los ocho del verificador.
- **Para T-18:** `WrongGroup` hereda de `InvalidToken`; hay que atraparla antes para responder 403 y no 401. La comprobación de edad es redundante con la de vida (si exp − iat ≤ 1 h y no venció, la edad es menor de 1 h); se conserva como defensa.
- **Evidencia:** `./scripts/verify`: sql=269, unit=260, integration=157, blackbox=77. Escáner de datos personales con 0 hallazgos y gitleaks del historial limpio.

## 2026-11-22: T-18 construida, falta el defecto 12 (A-06)
- **Resultado:** `link_participant` (función del owner, solo `nukyro_api`), módulo `account` (`POST /api/v1/account/login`, `GET /api/v1/account`), `nukyro.auth` (token o cookie; el token manda y uno inválido no cae a la cookie), códigos `account_blocked` (403) y `documents_required` (409). Todas las rutas aceptan `Authorization: Bearer`.
- **Defecto 9 (vinculación):** el traslado recalcula `has_prior_session` por `(started_at, id)`: queda una sola primera sesión, la más antigua. Visto en rojo al quitar el recálculo (L-07, L-09, CC5, CC6; `bd/pruebas/evidencia-rojo.md`).
- **Revisión:** `./scripts/verify`: sql=294 (57 + 216 + 21), unit=260, integration=198, blackbox=90. Falta la auditoría en Opus.
- **Defecto 12:** pendiente. D-35 necesita el `CHECK` de una hora entre bloqueo y purga (A-06), que toca la conservación de datos personales y no se delegó. Sin él T-18 no cierra.
- **Declarado al construir:**
  - La cookie anónima se borra en todo inicio de sesión con cuenta (`Max-Age=0`), haya vinculado o no.
  - Se registran las dos casillas del registro en `consent_events`, también cuando están sin marcar.
  - Cuenta sin participante: las rutas de sesión responden 409 `documents_required`.
  - Cuenta sin haber iniciado sesión: 401.
- **Evidencia:** `tests/trazabilidad-e5.md`.

## 2026-11-22: A-06 aprobada
- **Resultado:** el usuario aprueba el `CHECK` de una hora entre bloqueo y purga. Se aplica al empezar la próxima sesión, con sus pruebas, y con él se cierran el defecto 12 y T-18.
- **Decisiones:** A-06 cerrada con la aprobación del usuario.

## 2026-11-28: T-18, A-06 aplicada y cierre delegado
- **Resultado:** PostgreSQL exige una hora desde `blocked_at` hasta `deletion_due_at`. Se regeneró la migración inicial y se verificaron el mínimo exacto y el instante anterior.
- **Revisión:** los cuatro criterios de T-18 tienen respaldo. CC5, CC6 y la integración comprobaron la primera sesión única y la idempotencia. El defecto 9 está documentado en rojo. Para el defecto 12, SQL devolvió 23514 en plazos menores y el mismo token recibió 403 mientras la cuenta estuvo bloqueada y 401 en el instante de purga. La cuenta quedó ausente. Revisión humana del código pendiente.
- **Decisiones:** A-06, D-35 y cierre delegado por D-32.
- **Evidencia:** `./scripts/verify` desde una base vacía dio sql=298, unit=260, integration=199, blackbox=90. El rojo se conserva en `bd/pruebas/evidencia-rojo.md`.
