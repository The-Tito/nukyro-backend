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
