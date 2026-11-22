# Registro de prompts

Solo peticiones que deciden algo, inician una tarea o corrigen el rumbo.

## 2026-10-31 a 2026-11-10: trabajo previo a la adopción
**Modelo:** no registrado
**Prompt:** resumen; no se conservaron los textos
**Resultado:** KG, ADR-001 a ADR-005, modelo de datos, documentos y presentación (ver `meta.historial` del KG)
**Revisión humana:** aprobación del modelo v0.2 y decisiones registradas como DECISION-USUARIO; el resto, no registrada

## 2026-11-22: adopción de la metodología (D-01 a D-07)
**Modelo:** Claude Opus 5.5
**Prompt:** «todo lo recomendado, antes de nada, consideras necesario crear dos repositorios uno para el backend y otro para la base de datos? si no es asi, aqui tienes el repositorio del backend: git@github.com:The-Tito/nukyro-backend.git»
**Resultado:** metodología instalada y un solo repositorio (D-04)
**Revisión humana:** configuración aprobada; CLAUDE.md y cierre, pendientes

## 2026-11-22: cierre de la adopción (T-01)
**Modelo:** Claude Opus 5.5
**Prompt:** «apruebo 1,2,4, el tres no lo haremos, solo quiero que dejes la metodologia despeus seguire trabajando en el proyecto en otro chat, tu encargate de dejar la metodologia»
**Resultado:** CLAUDE.md integrado, D-08, A-03, plan y análisis de E1
**Revisión humana:** aprobó diff, traslado y correo; rechazó el repositorio privado; plan y cierre de T-01, pendientes

## 2026-11-22: cierre de E0, privacidad y PR (T-01)
**Modelo:** Claude Opus 5.5
**Prompt:** «todo lo recomendado, si quiero que hagas todo paso a paso, pero que tu hagas los PRs y los fusiiones, al finalizar todo continuamos, puedes levantar el docker, etc etc». Sobre el alcance del permiso: «hazta que yo te diga que regresamos a la configuracion de "el usuario revisa y fusiona"». Sobre la fusión eligió: «Fusión local y push».
**Resultado:** D-09 a D-14, ADR-006, KG seudonimizado, validador adaptado, pruebas SQL repetidas, auditoría con el agente auditor y sus bloqueos corregidos
**Revisión humana:** aprobó las decisiones, el plan y el cierre de T-01 tras la auditoría; delegó la revisión y fusión del PR, así que no revisó el diff

## 2026-11-22: análisis del estado del proyecto
**Modelo:** Claude Opus 5.5
**Prompt:** «quiero que hagas un analisis del proyecto y su estado actual, que ya hay definido, que ya hay de desarrollo, el proyecto ya esta listo y definido para su desarrollo, etc etc»
**Resultado:** diagnóstico con cobertura del plan, defectos por lectura y contradicciones; pruebas SQL no ejecutadas
**Revisión humana:** pendiente

## 2026-11-22: plan del backend (T-08)
**Modelo:** Claude Opus 5.5, con un agente de planeación (modelo no registrado)
**Prompt:** «quiero que hagas un plan para completar el desarrollo del backand, por cada fase haras una planeacion para reafirmar y comprobar que se va por el buen camino, deja eso definido, al concluir con el plan debemos tener el backend funcional de nukyro»
**Resultado:** plan E2 a E8 con dos puertas por fase, D-15 a D-23 en el KG y `context/plan.md`
**Revisión humana:** respondió ocho preguntas y aprobó el plan; diff del registro, pendiente

## 2026-11-22: pausa y cierre de sesión (T-08)
**Modelo:** Claude Opus 5.5
**Prompt:** «no quiero que empieces aun con el plan, quiero que hagamos /cerrar para que retome en un nuevo chat y empecemos con el plan»
**Resultado:** T-08 en pausa con registro parcial sin commit; bitácora y handoff
**Revisión humana:** pendiente

## 2026-11-22: ejecución autónoma del plan, T-08 y E2 (T-05, T-06, T-08, T-09, T-10)
**Modelo:** Claude Opus 5.5 (dirección, diseño y auditoría de fase), Claude Sonnet (programación y auditoría de T-08), Claude Haiku (lectura)
**Prompt:** «quiero que te quedes realizando el desarollo, quiero que uses distintos tipos de modelos, por ejemplo opus el cerebro, sonnet para programar,  haiku para leer archivos, etc etc, tu lo defines segun lo mejor, y empieces con el desarrollo, quiero que vayas haciendo commits, prs y los fusiones, verifiques que todo se vaya implementando correctamente y siguiendo el plan que es la base, pon un seguro que si se llega al 96% de uso del limite de 5 horas se haga automaticamente /cerrar para no quedarnos parados sin registrar en que, dicho esto te dejo trabajando, no estare para aprobar, verificar o hacer prs, tu haras todo hasta finalizar.»
**Resultado:** D-24, D-25, protocolo por fases, ADR-007 y ADR-008, esquema v0.3, base de la API, CI, recorrido de entrada y E2 cerrada por delegación (EV-01, EV-02). Código en `src/`, `bd/`, `tests/`.
**Revisión humana:** pendiente

## 2026-11-22: ejecución autónoma de E3, primera parte (T-11, T-07)
**Modelo:** Claude Opus 5.5 (especificación y revisión), Claude Sonnet (auditoría de ADR-009, motor y P5)
**Prompt:** la misma petición de la entrada anterior (D-24)
**Resultado:** plan de E3, ADR-009 y, sin fusionar, `src/nukyro/engine/` y `src/nukyro/modules/simulation/`
**Revisión humana:** pendiente

## 2026-11-22: sesión retomada, cierre de E3 (T-07, T-12, T-13)
**Modelo:** Claude Opus 5.5 (dirección y auditorías), Claude Sonnet (programación, contenido y auditorías acotadas)
**Prompt:** «si a todo, continua con el desarrollo, ya fusione el pr», «continuamos haciendo tu los prs y fusionando, nada mas» y «continuaras solo hasta finalizar el backend, dame un porcentaje estomado de cuanto llevas desarrollado y cuanto falta»
**Resultado:** D-26 a D-32, validador y publicación, DEMO-BECAS y E3 cerrada por delegación (EV-03)
**Revisión humana:** decisiones respondidas por el usuario; código, puertas y textos pendientes de revisar

## 2026-11-22: E4, experiencia educativa (T-14, T-15, T-16)
**Modelo:** Claude Opus 5.5 (plan, revisión y auditoría), Claude Sonnet (programación, pruebas y verificación final)
**Prompt:** «continuaras solo hasta finalizar el backend» (D-32)
**Resultado:** evaluaciones, resumen y encuesta; E4 cerrada por delegación (EV-04)
**Revisión humana:** pendiente
