---
name: fase
description: Planea, comprueba o cierra una fase del plan del backend (E2 a E8) con sus dos puertas (D-22). Úsala con «$fase planear N», «$fase comprobar N» o «$fase cerrar N».
---

# Fase del plan con dos puertas (D-22)

Argumento: `planear|comprobar|cerrar N` (lo que el usuario escriba junto a la invocación). Fases E2 a E8.
Manda el KG; el plan está en `context/plan.md`. Sin subagentes (D-33).

## planear N
1. La fase anterior está cerrada (de E3 en adelante). Si no, detente.
2. **Reafirma con evidencia:** `./scripts/verify` sobre develop, validador, RF y decisiones nuevas, diferencias
   entre código, esquema, ADR y OpenAPI, RF demostrados de 87, supuestos y riesgos nuevos.
3. **Dictamen:** En camino; Con ajuste (cambia el cómo); Desviado (regresión, conflicto o alcance: detente).
4. Escribe `context/etapas/etapa-N.md` con `context/etapas/PLANTILLA.md`.
5. **Puerta A:** la aprueba el usuario, o se registra «delegada» si rige D-24. En el nodo de la etapa:
   `puerta_a: {estado, fecha, decision, plan}`. Los criterios quedan fijos.

## comprobar N
1. `./scripts/verify` desde una base vacía, sin pruebas omitidas.
2. Cada RF con su caso positivo y negativo; cada defecto, de rojo a verde.
3. Auditoría en la sesión con la skill `auditar` (D-33, sin subagentes) sin hallazgos que bloqueen; escaneo de secretos y de datos personales.
4. KG, vistas y modelo al día; nodo `EV-xx` con `commit`, `comando`, `resultado` y arista `respalda` a la etapa.

## cerrar N
1. **Puerta B:** muestra qué se hizo, cómo comprobarlo, qué se esperaba, qué no se probó y 2 o 3 preguntas para
   `context/estudio.md`. La cierra el usuario, o queda «delegada» si rige D-24.
2. `puerta_b: {estado, fecha, decision}`, tareas cerradas, etapa cerrada y validador en verde.
3. Push, PR y fusión según D-11 (`git merge --no-ff` local, nunca `gh pr merge`); skill `registro-ia`.
