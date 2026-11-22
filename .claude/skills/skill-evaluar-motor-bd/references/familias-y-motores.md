# Familias de bases de datos, motores y señales

Úsalo en la fase 4 para elegir **qué motores puntuar** en cada dominio. No decide por sí solo:
una señal abre una rama, la matriz decide.

---

## Familias

| Familia | Unidad de dato | Bueno para | Malo para | Motores típicos |
|---|---|---|---|---|
| Relacional | Fila en tabla con esquema fijo | Escrituras multi-entidad con ACID, cruces y reportes variados, integridad declarativa | Estructura muy variable entre registros; objetos profundamente anidados que siempre se leen completos | PostgreSQL, MySQL/MariaDB, SQL Server, Aurora |
| Documentos | Documento JSON/BSON | Leer un objeto completo de una vez, forma variable, patrones estables | Cruces frecuentes entre colecciones; integridad entre muchos documentos | MongoDB, Firestore, Couchbase, DocumentDB |
| Clave-valor | Par clave → valor | GET/PUT por clave, sesiones, caché, contadores, expiración (TTL) | Buscar por atributos secundarios | Redis, Valkey, DynamoDB (modo clave-valor), Memcached |
| Columnas anchas | Fila con columnas dinámicas por partición | Escrituras masivas distribuidas con accesos por clave de partición conocidos | Consultas ad hoc, transacciones | Cassandra, ScyllaDB, Bigtable |
| Grafos | Nodos y aristas | Relaciones profundas, recorridos de varios saltos (amigos de amigos, rutas) | Agregados masivos simples | Neo4j, Neptune, ArangoDB |
| Series de tiempo | Medición + marca de tiempo | Sensores, métricas, monitoreo, ventanas de tiempo, retención por antigüedad | Datos sin componente temporal | InfluxDB, TimescaleDB, colecciones *time series* de MongoDB |
| Vectores | Vector numérico (embedding) | Búsqueda por similitud (IA, recomendaciones, búsqueda semántica) | Búsquedas exactas por campo | pgvector, Atlas Vector Search, Pinecone, Qdrant |
| Búsqueda | Documento indexado invertido | Texto libre con relevancia, facetas, tolerancia a errores de dedo | Fuente de verdad transaccional | OpenSearch/Elasticsearch, Atlas Search, Meilisearch |

---

## Señales en los patrones → qué rama abrir

| Señal observada en la tabla de patrones | Rama que abre | Antes de abrirla, prueba |
|---|---|---|
| Una escritura crítica toca varias entidades (venta + inventario + pago) | Relacional | MongoDB con transacciones multi-documento (sabiendo su costo) |
| El patrón dominante lee «un objeto completo» (expediente, publicación, pedido) | Documentos | PostgreSQL con JSONB para la parte variable |
| Los atributos varían mucho entre registros del mismo tipo (catálogo con talla/color vs pulgadas/resolución) | Documentos o JSONB | Columna JSONB en una tabla relacional |
| Reportes cruzados variables, o patrones desconocidos o cambiantes | Relacional | — |
| Recorridos de 3+ saltos frecuentes («quién conoce a quién», rutas entre paradas) | Grafo | CTE recursivas en PostgreSQL si los saltos son pocos y la frecuencia baja |
| Medición + marca de tiempo, mucho volumen, consultas por ventana | Series de tiempo | TimescaleDB (extensión de PostgreSQL) o colección *time series* de MongoDB |
| Búsqueda por similitud o semántica | Vectores | `pgvector` o Atlas Vector Search dentro del motor principal |
| Sesiones, caché, límites de peticiones, datos con expiración | Clave-valor | Tabla con TTL o índice TTL de Mongo si el volumen es bajo |
| Búsqueda de texto con relevancia y errores de dedo | Búsqueda | Texto completo de PostgreSQL (`tsvector`) o Atlas Search |
| Disponibilidad por encima de consistencia en datos de bajo costo (likes, contadores, feed) | BASE es aceptable | — |

---

## ACID vs BASE (y CAP)

| | ACID (típico de SQL) | BASE (típico de NoSQL distribuido) |
|---|---|---|
| Significado | Atomicidad, Consistencia, Aislamiento, Durabilidad | *Basically Available, Soft state, Eventual consistency* |
| Prioriza | Que los datos estén siempre correctos | Que el sistema siempre responda |
| Consistencia | Inmediata | Eventual: las réplicas se igualan con el tiempo |
| Conviene en | Cobro, inventario, inscripción con cupo | Likes, comentarios, feed, métricas |

- **Pregunta de control:** ¿cuánto cuesta un dato inconsistente durante unos segundos? Si la
  respuesta es dinero, inventario o un cupo, el dominio exige ACID (veto de integridad).
- **MongoDB:** es atómico dentro de un documento y tiene transacciones multi-documento (requieren
  replica set; cuestan más). Por eso se diseña para que cada escritura crítica toque un solo documento.
- **CAP:** en un sistema distribuido, ante una partición de red hay que elegir entre consistencia
  y disponibilidad. Para un proyecto en un solo servidor gestionado, CAP casi nunca es el factor
  decisivo; no lo uses como argumento si no hay distribución real.

---

## JSON, BSON y JSONB

| | JSON | BSON | JSONB |
|---|---|---|---|
| Qué es | Texto clave-valor legible | JSON binario de MongoDB | JSON binario de PostgreSQL |
| Tipos | Pocos; no distingue fecha ni entero | `Date`, `ObjectId`, `Int32/64`, `Decimal128`, binarios | Los de JSON, ya parseados |
| Para qué | Intercambio (APIs) | Almacenar y recorrer documentos | Columnas JSON dentro de una base relacional, indexables (GIN, expresiones) |

**Implicación para la decisión:** «tenemos JSON» no es por sí solo un argumento a favor de
MongoDB. PostgreSQL con JSONB puede ganar, perder o empatar según la carga; es una hipótesis que
se mide, no se supone.

---

## Límites técnicos que suelen decidir

- **Documentos:** 16 MB por documento en MongoDB; archivos grandes van a GridFS u objeto (S3) con
  metadatos en el documento. Sin llaves foráneas: la existencia de una referencia la cuida la
  aplicación. `$lookup` existe, pero cada cruce cuesta lecturas.
- **Relacional:** el JOIN es barato con índices, pero un objeto muy anidado que siempre se lee
  completo obliga a reconstruirlo desde muchas tablas en cada lectura.
- **Clave-valor:** consultar por atributos secundarios no es su modelo natural.
- **Dinero:** nunca punto flotante. `numeric` en PostgreSQL, `Decimal128` en MongoDB.
