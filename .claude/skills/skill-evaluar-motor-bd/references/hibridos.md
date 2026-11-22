# ¿Un motor o un híbrido?

Un híbrido (persistencia políglota) es usar **más de un motor**, cada uno para el dominio que
mejor resuelve. Es legítimo, pero tiene un costo que se paga todos los días, no solo al construir.

---

## La regla de las tres condiciones

Un híbrido se recomienda **solo si se cumplen las tres**:

1. **Gana después del castigo.** En la salida de `score.py` queda arriba con el costo de motores
   adicionales y de escrituras cruzadas ya restado, y fuera de empate técnico.
2. **No hay variante en un solo motor que cubra lo mismo** a menos del umbral de empate.
3. **Las escrituras críticas no cruzan motores**, o si cruzan, está definido el mecanismo de
   consistencia y quién es la fuente de verdad.

Si falla cualquiera, la recomendación es **un solo motor** (el mejor puntuado), y el híbrido se
documenta como evolución futura con el disparador que lo justificaría («cuando el catálogo pase de
N variantes», «cuando la búsqueda semántica sea un requisito»).

---

## Variantes en un solo motor (pruébalas antes de sumar un segundo motor)

| Necesidad | Dentro de PostgreSQL | Dentro de MongoDB |
|---|---|---|
| Atributos variables | Columna `JSONB` con índice GIN o de expresión | Nativo |
| Transacción multi-entidad | Nativo | Transacciones multi-documento (replica set) |
| Integridad declarativa | Llaves foráneas, `CHECK`, `UNIQUE` | `$jsonSchema`, índices únicos (parciales) |
| Series de tiempo | TimescaleDB, particionado por fecha, índice BRIN | Colecciones *time series* |
| Vectores | `pgvector` | Atlas Vector Search |
| Texto con relevancia | `tsvector` + GIN, `pg_trgm` | Atlas Search, índice de texto |
| Recorridos de grafo cortos | CTE recursivas | `$graphLookup` |
| Expiración (TTL) | Tarea programada que borra por fecha | Índice TTL |
| Caché | Vista materializada | — (se suele agregar Redis) |

---

## Formas de híbrido frecuentes y cuándo tienen sentido

| Forma | Ejemplo | Tiene sentido cuando | Cuidado con |
|---|---|---|---|
| SQL transaccional + documentos | Pedidos/pagos/inventario en SQL; catálogo de forma muy variable en documentos | El catálogo varía mucho **y** se lee como objeto completo con alta frecuencia, y JSONB no basta | El precio que se cobra se **copia** a la venta en SQL; el catálogo no es fuente de verdad del cobro |
| SQL + clave-valor | Login y usuarios en SQL; sesiones y límites de peticiones en Redis | Volumen alto de sesiones o necesidad de latencia muy baja | Si Redis se pierde, solo se pierden sesiones (reconstruible) |
| SQL + búsqueda | Productos en SQL; índice de búsqueda en OpenSearch | Búsqueda con relevancia, facetas y errores de dedo sobre volumen grande | El índice es una **proyección**: se reconstruye desde SQL |
| SQL + grafo | Usuarios en SQL; red de relaciones en Neo4j | Recorridos de varios saltos son el patrón dominante | Doble escritura de cada relación |
| Documentos + series de tiempo | Dispositivos en Mongo; lecturas de sensores en InfluxDB/Timescale | Volumen de mediciones muy superior al resto | Retención y agregación por ventana |

---

## Costos que el híbrido agrega (deben aparecer en el informe)

- Segundo servicio gestionado: costo fijo mensual, aunque esté casi vacío.
- Segundo esquema de respaldos y de recuperación puntual, **sincronizados entre sí**.
- Consistencia entre motores: sin transacción común, una falla a mitad deja un estado inválido.
  Mecanismos: patrón *outbox*, captura de cambios (CDC), un motor como fuente de verdad y el otro
  como proyección reconstruible.
- Dos lenguajes de consulta, dos drivers, dos modelos mentales para el equipo.
- Pruebas de integración y entornos locales más pesados.

---

## Mecanismos de consistencia entre motores

| Mecanismo | Qué hace | Cuándo basta |
|---|---|---|
| Fuente de verdad única + proyección | Un motor manda; el otro se reconstruye desde él | Búsqueda, caché, vistas de lectura |
| *Outbox* transaccional | La escritura en el motor principal guarda también un evento en la misma transacción; un proceso lo publica al segundo motor | Cuando el segundo motor debe reflejar cambios con poco retraso |
| CDC (captura de cambios) | Se leen los cambios del log del motor principal | Volumen alto, varios consumidores |
| Doble escritura desde la aplicación | La app escribe en ambos | **Evitar** en datos críticos: es el contraejemplo clásico (falla entre la primera y la segunda) |
