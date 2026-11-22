---
id: ADR-004
titulo: Estadísticas anónimas desde el diseño
estado: Reemplazada por ADR-007
fecha: 2026-11-01
decisores: PER-DEV-01, PER-DEV-02, PER-DEV-03
kg: [ADR-004, D6, C5, C8, C7, C9, ENCUESTA-APP, PROC-10, RET-06]
---

# ADR-004 · Estadísticas anónimas desde el diseño

> **Superado en parte por D-19 a D-21 (2026-11-22):** no implementar el §2. ADR-007 lo reemplazará en T-09.

## Contexto

- Las sesiones sin cuenta se desvinculan a los 30 días (RET-06); las cuentas se cancelan tras 12 meses de inactividad, con un bloqueo previo de 30 días (RET-01, DEC-BLOQUEO); cualquier persona puede pedir la cancelación (ARCO).
- Aun así, el piloto necesita datos **emparejados por persona**: H02 compara pre-test y post-test filtrando a quienes sacaron menos de 80 %, H03–H05 cuentan aciertos por persona y H06 incluye sesiones abandonadas (C5).
- Las estadísticas globales sobreviven sin plazo, sin datos que identifiquen y sin publicar grupos menores de 10 (PROC-10, RET-04, RF-072).
- La encuesta dentro de la app no se liga a la persona, pero H07 solo cuenta la primera sesión (ENCUESTA-APP, C8).
- Con 50 participantes, fechas exactas o recorridos completos podrían identificar a alguien.
- La persona puede oponerse a entrar en las estadísticas (Aviso §5.2).

*Este ADR no es opinión legal.*

## Decisión

1. **Tablas de resultados anónimas**, sin identificador de sesión, participante ni cuenta, con la fecha reducida a la **semana ISO**:
   - `session_facts`: una fila por sesión cerrada, con la versión del escenario, si es primera sesión, puntuación de pre-test, post-test y transferencia, aciertos causales y de justificación, si alcanzó el desenlace y cuál, si terminó las evaluaciones y su duración redondeada. Alimenta H02–H06.
   - `decision_facts`: una fila por decisión tomada, con la versión del escenario, la clave estable de la decisión y de la alternativa, y si es primera sesión. Alimenta "decisiones más frecuentes" (PROC-9, PROC-10).
   - `survey_responses`: respuestas de la encuesta dentro de la app, con la marca de primera sesión copiada y la semana. Alimenta H07.
2. **Cuándo se escriben.**
   - `session_facts` se escribe al **cerrar** la sesión: al terminar las evaluaciones o cuando se va a borrar (caducidad, cancelación o ARCO), lo que ocurra primero. Va en la misma transacción que el cierre o el borrado.
   - `decision_facts` se escribe al confirmar cada decisión.
   - `survey_responses` se escribe al enviar la encuesta. En la sesión solo queda `survey_answered` (RF-060).
3. **Oposición.** Si el participante tiene `exclude_from_stats`, no se escriben resultados nuevos. Los ya escritos no se pueden localizar, como dice el Aviso.
4. **Borrado de una persona.** Es un borrado en cascada desde el participante o la cuenta, sin procesos de anonimización: lo anónimo ya está separado.
5. **El umbral de 10** para publicar se aplica al generar los reportes, no en la base.
6. **Datos operativos, también anónimos o efímeros:**
   - **Solicitudes ARCO (C7):** `arco_requests` guarda el correo del solicitante, el derecho, el estado (`received`, `awaiting_info`, `in_review`, `accepted`, `executed`, `denied`, `withdrawn`; refinado el 2026-11-01, ver plan H-06: `answered` mezclaba "respondida" con su resultado), las fechas límite y una sola ampliación. Los documentos de identidad van a almacenamiento de archivos y se borran al cerrar la solicitud.
   - **Bitácora del panel (C9):** `admin_audit_log` solo admite agregar registros, no tiene llaves foráneas (usa identificadores como valores opacos), no guarda respuestas de participantes y se purga a los 90 días (RET-02, RNF-15).

## Alternativas consideradas

| Opción | Por qué se descartó |
| --- | --- |
| Calcular en el momento de consultar | Se pierde todo lo que caducó o se borró; con caducidad de 30 días, el análisis del piloto queda incompleto. |
| Anonimizar las filas al borrar | Frágil: los recorridos y las fechas exactas pueden identificar a alguien en una muestra de 50. |

## Consecuencias

- **A favor:** las hipótesis se pueden calcular aunque los datos personales ya no existan; la baja es un borrado sin efectos colaterales; cumple RF-072 y PROC-10.
- **En contra:** las métricas solo pueden ser las previstas en `session_facts`. Una métrica nueva no se puede recalcular sobre sesiones ya borradas. La escritura en el cierre debe probarse en todas las rutas: terminar, caducar, cancelar y ARCO.
- **Riesgo residual:** con muestras pequeñas, una fila de resultados podría ser única. Se mitiga con la semana en lugar de la fecha, la duración redondeada y el umbral de 10 en los reportes.

## Trazabilidad

RF-060, RF-061, RF-067, RF-069, RF-070, RF-072, RNF-02, RNF-15, RNF-19, H02–H07, PROC-09, PROC-10, RET-01, RET-02, RET-04, RET-06, ENCUESTA-APP, DEC-BLOQUEO.
