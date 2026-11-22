# Plan: Nukyro

Vista del KG: si difieren, manda el KG. Propuesto y aprobado por el usuario el 2026-11-22 (D-12).

## Objetivo y límites

- **Se entrega:** el backend y la base de datos del MVP 1.0 (FUN-01 a FUN-11) y su documentación.
- **Para quién:** estudiantes de TI mayores de 18 años; piloto de hasta 50 participantes y un escenario (DEC-VOLUMEN).
- **Fuera:** FA-01 a FA-23 del KG. La interfaz y el panel se planean al resolver A-01.

## Etapas

| ID | Etapa | Resultado | Depende de | Estado |
|---|---|---|---|---|
| E0 | Adopción de la metodología | Método instalado, validado y confirmado |  | cerrada |
| E1 | Cierre documental | Documentos coherentes con el KG |  | pendiente |
| E2 | Base ejecutable | API arrancable y esquema creado por Alembic | E0 | pendiente |
| E3 | Motor de simulación | Procesos P5, P9, P10 y P12 probados | E2 | pendiente |

## Tareas

### T-01 · Adoptar la metodología
- Etapa: E0
- Estado: cerrada
- Entregable: kit adaptado, CLAUDE.md integrado, hook instalado y handoff
- Criterios de cierre:
  - `python3 context/validar_kg.py` termina sin errores
  - `git check-ignore HANDOFF.md HISTORIAL.md` lista ambos
  - el usuario confirma el cierre

### T-02 · Términos y Condiciones v1.1
- Etapa: E1
- Estado: pendiente
- Entregable: versión nueva en docs/, sin sobrescribir la 1.0
- Criterios de cierre:
  - cita el Aviso 2.2
  - pide la aceptación antes de la primera sesión (RF-073)
  - cubre el uso sin cuenta y la pérdida del avance al borrar la cookie
  - tiene control de cambios
  - el usuario aprueba el texto y CONF-14 pasa a resuelto

### T-03 · Confirmar las prácticas del reporte técnico
- Etapa: E1
- Estado: pendiente
- Entregable: decisiones del equipo en el KG
- Criterios de cierre:
  - hay decisión sobre KMS, `rds.force_ssl` y Secrets Manager
  - hay decisión sobre enmascarar copias de producción
  - hay decisión sobre los umbrales de escalabilidad
  - si alguna se rechaza, hay versión nueva del reporte

### T-04 · Actualizar los índices en Word
- Etapa: E1
- Estado: pendiente
- Entregable: versiones nuevas de los .docx que lo necesiten
- Criterios de cierre:
  - el usuario decide si el reporte v1, ya reemplazado, se actualiza (decidido en D-12: no)
  - el índice de requerimientos coincide con su contenido
  - el KG registra versión y sha256 nuevos

### T-05 · Base de la API y migración inicial
- Etapa: E2
- Estado: pendiente
- Entregable: proyecto FastAPI con Alembic en este repositorio
- Criterios de cierre:
  - `alembic upgrade head` crea el esquema en PostgreSQL 16 vacío
  - el esquema equivale a `bd/schema.sql`
  - pasan las 52 pruebas SQL
  - la API arranca

### T-06 · Revisiones automáticas del backend
- Etapa: E2
- Estado: pendiente
- Entregable: CI y hooks de Python
- Criterios de cierre:
  - CI corre las pruebas SQL
  - formato y lint con versión fija

### T-07 · Motor de simulación
- Etapa: E3
- Estado: pendiente
- Entregable: procesos P5, P9, P10 y P12 de `bd/modelo-datos.md` §7
- Criterios de cierre:
  - cada proceso tiene pruebas
  - confirmar una decisión es idempotente (ADR-003, RN-14)
  - el cliente no determina consecuencias (ARQ)

## Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Publicar datos personales (D-09) | Un push público no se puede deshacer del todo | ADR-006 y búsqueda de datos personales antes de cada push |
| El equipo no conoce o no acepta las reglas (S-01) | Commits y ramas fuera del método | Confirmarlo con ambos integrantes |
| Sin fechas ni rúbrica registradas | Prioridades equivocadas | Pedirlas al abrir E1 |
| S1–S5 se validaron en otros proyectos, no en este | RDS, Cognito o Alembic pueden fallar aquí | Comprobarlo en E2 |
