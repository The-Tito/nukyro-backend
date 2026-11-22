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
