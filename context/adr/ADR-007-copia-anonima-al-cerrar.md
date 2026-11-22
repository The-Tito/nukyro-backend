---
id: ADR-007
titulo: Copia anónima solo al borrar o bloquear
estado: Aceptada
fecha: 2026-11-22
decisores: usuario (D-19 a D-21); diseño del asistente por delegación (D-24), sin revisión humana
kg: [ADR-007, ADR-004, D-19, D-20, D-21, RN-20, RF-072]
---

# ADR-007 · Copia anónima solo al borrar o bloquear

## Contexto

ADR-004 copiaba los hechos durante la sesión. Así una fila «anónima» nacía en la misma transacción que la fila de la
persona (`xmin`), seguía su orden de llegada y quedaba aunque después se opusiera. Además, un INSERT con RETURNING
exige SELECT, que la API no tiene.

## Decisión

1. Mientras los datos existen, los reportes se calculan sobre ellos, sin quienes se opusieron (D-19).
2. La copia se crea solo antes de borrar o bloquear, salvo oposición o minoría de edad (D-20). Purgar solo borra.
3. La hacen funciones del owner con `search_path` fijo. API, panel, tareas y analítica no leen ni escriben hechos.
4. Cada fila lleva UUID v4 y la semana de inicio de la sesión. No guarda motivo de cierre.
5. Tras cada archivo se reescriben las tablas de hechos completas, con id nuevo y en orden aleatorio.
6. Se agregan aciertos por tema, en filas sueltas, y el punto de abandono (D-21).
7. La analítica solo ejecuta funciones agregadas, con umbral de 10 participantes.

## Alternativas consideradas

- **Copiar durante la sesión (ADR-004):** liga filas y no respeta una oposición posterior.
- **Archivar por lote programado:** durante el bloqueo obligaría a usar datos que D-20 no permite usar.
- **Solo quitar columnas:** no elimina el vínculo por transacción ni por orden físico.
- **Ruido estadístico:** con 50 participantes destruye las métricas del piloto.

## Consecuencias

- Archivar cuesta lo que midan las tablas de hechos. Es aceptable con DEC-VOLUMEN; hay que revisarlo si crece.
- **Riesgo residual:** el anonimato no es absoluto. Quien compare respaldos de antes y después de un borrado, lea
  páginas físicas o WAL como superusuario, o conozca al único que cerró esa semana puede inferir una fila. El
  umbral limita los reportes, no a quien tenga ese acceso.
- **Encuesta (T-16, D-29):** entra solo por `submit_survey`, con la semana de inicio, y se reescribe entera al enviar.
  La última sesión que respondió comparte `xmin` con todas las respuestas: se sabe que respondió, no cuál es la suya,
  salvo que sea la única.
- Si el Aviso o el reporte quedan desfasados se registra; el texto lo decide el usuario.

## Trazabilidad

Reemplaza a ADR-004. Concreta D-19, D-20 y D-21. Afecta RF-070, RF-072, RF-078 a RF-080, RF-085 y RN-20.
