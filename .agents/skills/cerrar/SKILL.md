---
name: cerrar
description: Cierra la sesión dejando el registro completo y el HANDOFF listo para $retomar. Úsala al terminar una sesión o cuando se agote el límite de uso o de contexto.
---

# Cerrar la sesión

Cierra la sesión para que la siguiente empiece sin releer nada. Lo versionado va primero, para que el
HANDOFF describa el estado final.

1. Completa `context/bitacora.md` con las entradas que falten.
2. Verifica que decisiones, supuestos, tareas y etapas de la sesión estén en
   `context/proyecto/kg.json` (manda) y en sus vistas. Corre `python3 context/validar_kg.py`.
3. Usa la skill `registro-ia`.
4. Revisa `git status --short`. Si queda trabajo sin commit, dilo y pregunta. **No hagas commit sin permiso.**
5. Reescribe `HANDOFF.md` con solo lo vigente (~120 líneas como máximo), con sus seis secciones:
   1. **Estado:** rama, commits, PR abiertos con orden de fusión, etapa, tarea y paso.
   2. **Siguiente tarea:** objetivo con IDs, rama, tabla «Qué leer» con comandos `grep` o `sed` exactos,
      lo que ya existe, decisiones pendientes con recomendación y criterios de cierre.
   3. **Después:** las 2 o 3 tareas siguientes.
   4. **Cómo levantar el entorno:** comandos exactos.
   5. **Reglas y trampas vigentes.**
   6. **Deuda abierta.**
6. Pasa lo que dejó de ser vigente al final de `HISTORIAL.md`, en `## Sesión AAAA-MM-DD: tema`.
7. Detén los servicios que se levantaron en esta sesión y resume en 3 a 5 líneas cómo quedó todo.

`HANDOFF.md` y `HISTORIAL.md` son locales y no se versionan (D-03).
