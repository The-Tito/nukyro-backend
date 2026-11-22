---
id: ADR-005
titulo: PostgreSQL 16 en Amazon RDS con backend FastAPI
estado: Aceptada
fecha: 2026-11-01
decisores: PER-DEV-01, PER-DEV-02, PER-DEV-03
kg: [ADR-005, EVAL-MOTOR, DEC-STACK]
---

# ADR-005 · PostgreSQL 16 en Amazon RDS con backend FastAPI

## Contexto

La evaluación del motor (`context/evaluaciones/evaluacion-motor-bd.md`) determinó la familia relacional con confianza alta y dejó un empate técnico entre PostgreSQL (4.70) y MySQL 8 (4.60). El dato que lo resolvía era la experiencia del equipo. El stack del backend estaba diferido (DEC-STACK) y el reporte técnico de la materia pide motor con versión, ORM y hosting.

## Decisión

1. **Motor: PostgreSQL 16**, por decisión del equipo. Además es el que mejor resuelve el único diferencial técnico: índice único parcial para RN-16 y `jsonb` para las reglas de ADR-001.
2. **Hosting: Amazon RDS for PostgreSQL** en us-east-1, instancia única de la familia más pequeña, con respaldo automático y TLS obligatorio. Se paga con los **créditos del laboratorio escolar**.
3. **Backend: FastAPI** (Python), porque el equipo ya lo usa en otros proyectos.
4. **ORM y migraciones: SQLAlchemy 2.x + Alembic, con el driver psycopg 3.** Confirmado por el equipo el 2026-11-01.
5. **Roles de base de datos separados por proceso:** `nukyro_api` (rutas de participantes), `nukyro_admin` (panel), `nukyro_jobs` (tareas programadas) y `nukyro_analytics` (reportes). FastAPI usa un usuario de conexión distinto para participantes y para el panel. Decisión del usuario sobre el riesgo F4 del modelo de datos.

## Alternativas consideradas

| Opción | Por qué se descartó |
| --- | --- |
| MySQL 8 | Empate técnico; el equipo eligió PostgreSQL. RN-16 habría requerido una columna generada. |
| MongoDB, DynamoDB | Puntuaron 3.90 y 3.18; escrituras críticas multi-entidad (ver evaluación §7–§9). |
| Híbrido | Pierde tras el castigo (4.25) y tiene tres escrituras cruzadas sin mitigar. |

## Consecuencias

- **A favor:**
  - unicidad parcial, `jsonb`, `ON CONFLICT` y transacciones multi-tabla son nativos;
  - Alembic versiona el esquema;
  - el reporte técnico ya tiene motor, ORM y hosting.
- **En contra y riesgos:**
  - PostgreSQL 16 no genera UUID v7 de forma nativa; la función `uuidv7()` llega en PostgreSQL 18. Ver plan, hallazgo H-01.
  - Los créditos del laboratorio pueden limitar servicios, tamaños de instancia o la duración de las sesiones. Hay que verificar que permitan RDS PostgreSQL 16 y Amazon Cognito antes de construir. Ver plan, hallazgo H-02.

## Trazabilidad

EVAL-MOTOR, DEC-STACK, ADR-001, ADR-003, ADR-004, RN-14, RN-16, RNF-13, RNF-14.
