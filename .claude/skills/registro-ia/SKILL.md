---
name: registro-ia
description: Registra el uso de IA del proyecto (prompts relevantes, resultado, modelo y revisión humana) en ia/. Úsala al cerrar una tarea o sesión, o cuando el usuario pida documentar el uso de IA.
---

# Registro del uso de IA

1. Una entrada en `ia/registro-prompts.md` por petición relevante:

   ```
   ## AAAA-MM-DD: título corto (T-xx)
   **Modelo:** nombre y versión
   **Prompt:** «texto literal, o resumen marcado como resumen»
   **Resultado:** qué se produjo o decidió, con rutas
   **Revisión humana:** qué revisó o cambió el usuario; «pendiente» si aún no
   ```

2. Una fila en `ia/modelos.md` si hay modelo, herramienta o tipo de tarea nuevo.
3. Las auditorías se guardan en `ia/auditorias/AAAA-MM-DD-<tema>.md` si el usuario lo pide.

No inventes prompts ni registres secretos o datos personales.
