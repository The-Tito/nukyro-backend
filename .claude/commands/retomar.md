---
description: Retoma el trabajo donde quedó la última sesión, leyendo solo HANDOFF.md
---

Retoma la sesión. **No leas documentos completos.**

1. Lee solo `HANDOFF.md`. Si no existe (clon o worktree nuevo), dilo y reconstruye el estado con git y el
   grafo. No leas `HISTORIAL.md`.
2. Contrasta su sección «1. Estado» con la realidad:
   - `git branch --show-current`, `git status --short`, `git log --oneline -3` (si ya hay commits);
   - si el remoto ya tiene `develop`: `git fetch -q`,
     `git rev-list --left-right --count develop...origin/develop` y
     `gh pr list --state all --limit 6`;
   - fase y puerta actuales:
     `jq -c '.nodos[]|select(.tipo=="Etapa" and .estado=="en_curso")|{id,puerta_a,puerta_b}' context/proyecto/kg.json`;
   - para decisiones o tareas, `jq` sobre `context/proyecto/kg.json` (consultas en `context/README.md`).
3. Responde en pocas líneas: dónde quedamos, qué cambió desde el HANDOFF, fase y puerta, qué sigue, qué lo bloquea y los
   pasos cortos. Si se abre una etapa sin análisis aprobado, ese es el primer paso.
4. **Menciona los conflictos sin resolver. Espera confirmación antes de implementar** y haz las preguntas de «Decisiones pendientes», cada una
   con su recomendación.
5. Al implementar lee solo lo de la tabla «Qué leer». Lo demás, primero con `grep -rn`.
   Criterios de una tarea: `grep -n "### T-xx" -A 12 context/plan.md`.

Contexto adicional del usuario (puede venir vacío): $ARGUMENTS
