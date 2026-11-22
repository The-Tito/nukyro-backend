# Contexto: memoria de trabajo versionada

| Archivo | Contenido |
|---|---|
| `fuentes.md` | Requisitos externos y su evidencia |
| `plan.md` | Etapas y tareas con criterios de cierre |
| `decisiones.md` | Decisiones tomadas (D-xx) y abiertas (A-xx) |
| `supuestos.md` | Lo que se da por cierto sin haberlo verificado |
| `cambios-alcance.md` | Diferencias con lo acordado (CA-xx) |
| `bitacora.md` | Registro cronológico |
| `adr/` | Decisiones importantes con su razonamiento |
| `etapas/` | Análisis y plan de cada etapa |
| `estudio.md` | Preguntas para defender |
| `planes/`, `evaluaciones/` | Planes y evaluaciones que alimentan decisiones |
| `proyecto/kg.json` | **Única fuente de verdad**; lo anterior son vistas o detalle suyo |

## Grafo de conocimiento

Manda `proyecto/kg.json` (D-02). Sus tipos y relaciones están en `esquema`; los nodos de seguimiento agregan:

```json
{"id": "D-01", "tipo": "Decision", "nombre": "Una línea", "texto": "La decisión", "estado": "tomada",
 "fecha": "AAAA-MM-DD", "ruta": "context/decisiones.md", "buscar": "| D-01 |",
 "fuente": [{"doc": "DECISION-USUARIO", "seccion": "AAAA-MM-DD"}]}
```

| Tipo | ID | Estados |
|---|---|---|
| `Etapa` | E0 | pendiente, en_curso, cerrada |
| `Tarea` | T-01 | pendiente, en_curso, cerrada, descartada |
| `Decision` | D-01 | tomada, reemplazada, descartada |
| `Decision` | A-01 | abierta, cerrada, descartada |
| `Supuesto` | S-01 | por_verificar, confirmado, refutado, resuelto |
| `Evidencia` | EV-01 | vigente, obsoleta |
| `CambioAlcance` | CA-01 | vigente, retirado |
| `ADR` | ADR-001 | Propuesta, Aceptada, Reemplazada por ADR-nnn |

Arista: `{"origen": "T-01", "relacion": "pertenece_a", "destino": "E0"}`.
`D-01` y `S-01` (seguimiento) no son `D1` ni `S1` (modelo de datos).

## Consultas

```bash
KG=context/proyecto/kg.json
# Un nodo
jq --arg id RF-062 '.nodos[] | select(.id==$id)' $KG
# Sus relaciones
jq -r --arg id RF-062 '.aristas[] | select(.origen==$id or .destino==$id) | "\(.origen) \(.relacion) \(.destino)"' $KG
# Qué está abierto o en curso
jq -r '.nodos[] | select(.estado=="abierta" or .estado=="en_curso") | "\(.id) \(.nombre)"' $KG
# Conflictos sin resolver
jq -r '.conflictos[] | select(.estado!="resuelto") | "\(.id) \(.tema)"' $KG
```

## Mantenimiento

- Primero el KG y luego su vista, en el mismo commit que el cambio que describen.
- Cada cambio incrementa `meta.version`, agrega `meta.historial` y actualiza `estadisticas`.
- No se borran decisiones: cambia su estado y, si aplica, se agrega `reemplaza`.
- El ID de una fila no se tacha ni se decora: el estado va en su columna.
- Si dos ramas usan el mismo ID, se renumera el más nuevo y se valida.
