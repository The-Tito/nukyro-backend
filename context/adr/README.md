# Registro de decisiones de arquitectura (ADR)

Cada ADR explica una decisión difícil de revertir: su contexto, las alternativas descartadas y sus consecuencias. Cada ADR también existe como nodo del grafo (`context/proyecto/kg.json`, tipo `ADR`), que sigue siendo la única fuente de verdad. Si un ADR y el grafo difieren, manda el grafo y se corrige el ADR.

| ADR | Título | Estado | Fecha |
| --- | --- | --- | --- |
| [ADR-001](ADR-001-contenido-versionado-hibrido.md) | Contenido del escenario versionado, híbrido y con claves estables | Aceptada | 2026-11-01 |
| [ADR-002](ADR-002-participante-raiz-identidad.md) | El participante como raíz de identidad, con o sin cuenta | Aceptada | 2026-11-01 |
| [ADR-003](ADR-003-decisiones-idempotentes-trazabilidad.md) | Registro idempotente de decisiones y trazabilidad causal | Aceptada | 2026-11-01 |
| [ADR-004](ADR-004-estadisticas-anonimas.md) | Estadísticas anónimas desde el diseño | Aceptada | 2026-11-01 |
| [ADR-005](ADR-005-postgresql-fastapi.md) | PostgreSQL 16 en Amazon RDS con backend FastAPI | Aceptada | 2026-11-01 |
| [ADR-006](ADR-006-repositorio-publico-seudonimizado.md) | Repositorio público con contexto seudonimizado | Aceptada | 2026-11-22 |

**Formato:** encabezado con `id`, `titulo`, `estado` (Propuesta · Aceptada · Reemplazada por ADR-nnn), `fecha`, `decisores` y `kg` (nodos relacionados), seguido de Contexto, Decisión, Alternativas consideradas, Consecuencias y Trazabilidad.
