# Preguntas de diseño

Catálogo de decisiones que suelen definir un modelo de datos. Recórrelo en la fase 3 y desarrolla **solo las que aplican** según los insumos. Las opciones son puntos de partida: si el proyecto pide otra, proponla.

## 1. Identificadores

**Aplica si:** siempre.

- Entero autoincremental: simple y compacto, pero deja ver volumen y facilita enumerar recursos si aparece en URLs.
- UUID v4: no adivinable, pero desordena el índice.
- UUID v7 (ordenado por tiempo): no adivinable y con buen índice. Comprueba si el motor lo genera o si va en la aplicación.
- Número visible por contenedor («Pedido 3 del cliente») además del identificador, si la interfaz lo necesita.

**Señales:** identificadores en URLs públicas o datos de varios dueños → no usar enteros expuestos.

## 2. Fuente de verdad de cada dato

**Aplica si:** hay un proveedor externo (autenticación, pagos, catálogos) o datos que podrían copiarse.

- Por cada dato, decide quién manda. Copiar a la base lo que ya vive en otro sistema (rol, nombre, correo) crea una segunda verdad que se desincroniza.
- Con un proveedor de identidad externo, guarda un `id` propio más el identificador del proveedor, no solo este: si el proveedor se recrea, puedes volver a ligar los datos.

## 3. Propiedad y aislamiento entre dueños

**Aplica si:** hay varios usuarios, clientes u organizaciones cuyos datos no deben mezclarse.

- A. Columna de dueño en la entidad raíz + filtro en el código. Depende por completo del código.
- B. A + el identificador de la raíz en cada tabla hija y llaves foráneas compuestas. La base impide referencias cruzadas entre dueños al escribir.
- C. B + seguridad por fila del motor (en PostgreSQL, Row-Level Security con el usuario fijado por transacción). La base también filtra las lecturas. Hay que probar que funciona con el pool de conexiones del ORM.

**Señales:** datos sensibles, requisito explícito de aislamiento o auditoría → B o C. Proyecto pequeño de un solo dueño → no aplica.

## 4. Estados: guardados o calculados

**Aplica si:** alguna entidad tiene estados.

- ¿El estado mezcla dimensiones independientes? Sepáralas (por ejemplo, «verificado» y «concluido» son dos cosas).
- Un estado que se deriva de otros datos («concluido si no hay pendientes») se **calcula** con una consulta indexada; guardarlo invita a desincronizarlo.
- Define estado inicial, finales y qué evento causa cada transición. Un final sin motivo («cancelada» por qué) suele necesitar un campo de motivo.

## 5. Historial y eventos

**Aplica si:** importa cómo cambió algo, no solo su valor actual (auditoría, seguimiento, métricas de tiempo).

- A. Una fila por momento con el estado copiado: simple, pero el estado vive en muchas filas.
- B. Entidad lógica (estado actual) + ocurrencias (cada vez que aparece) + eventos (cada cambio: quién, cuándo, por qué). Los tiempos (de detección a resolución) salen de los eventos.
- C. Historial en JSON dentro de la entidad: difícil de consultar y validar.

Si una entidad debe reconocerse entre ejecuciones o importaciones, define su **huella** (qué campos la identifican) y fija que esos campos sean estables.

## 6. Datos importados o versionados

**Aplica si:** se importan datos externos que pueden cambiar (contratos, catálogos, archivos) y otras entidades dependen de ellos.

- Cada importación como versión inmutable.
- Lo que configura el usuario sobre esos datos se liga a una **llave estable** a nivel contenedor, no a la fila de la versión; así sobrevive a una importación nueva.
- Decide qué pasa con lo configurado cuando el elemento desaparece o cambia en la versión nueva (huérfano, aviso, revisión).

## 7. Granularidad

**Aplica si:** hay procesos que generan muchos registros (ejecuciones, eventos, lecturas, peticiones).

- Guarda al nivel en que se consulta. Si la pantalla muestra una matriz, una fila por celda; el detalle fino solo como evidencia de lo relevante.
- Estima volumen por operación y por mes.

## 8. Borrado y retención

**Aplica si:** siempre. Recorre cada entidad.

| Pregunta | Opciones |
| --- | --- |
| ¿Qué pasa al borrarla? | Borrado físico en cascada · borrado lógico (fecha de borrado) · prohibido mientras tenga dependientes |
| ¿Otros la referencian para historial? | Si sí, borrado lógico y elimina de inmediato lo sensible de la fila |
| ¿Qué pasa con los dependientes abiertos? | Se cierran con un motivo registrado, o bloquean el borrado |
| ¿Cuánto se conserva y dónde? | Plazo de retención, respaldos y su rotación |

Para bitácoras: sin llaves foráneas (guarda identificadores como valores opacos para sobrevivir a los borrados), inmutable por permisos y trigger, sin texto libre del usuario y con plazo de purga.

## 9. Estadísticas tras los borrados y datos personales

**Aplica si:** se piden métricas globales, o los usuarios pueden darse de baja.

- A. Consultar en vivo: ligero, pero las métricas pierden lo borrado.
- B. Anonimizar al borrar: frágil, porque datos como una URL o un texto identifican al dueño aunque se quite la columna de usuario.
- C. Métricas anónimas desde el diseño: tablas de hechos sin usuario ni dueño, con fechas agregadas (semana, mes), escritas cuando ocurre el hecho. La baja es un borrado en cascada sin proceso extra.

Revisa la ley aplicable (en México, la LFPDPPP vigente desde marzo de 2025: bloqueo antes de la supresión, derechos ARCO) y declara que no es opinión legal.

## 10. Datos sensibles

**Aplica si:** se guardan credenciales, tokens, datos personales o datos de terceros.

- Cifrado a nivel campo (por ejemplo, AES-256-GCM con el `id` de la fila como dato asociado) y versión de llave para rotarla.
- Qué se enmascara antes de guardarse y quién lo garantiza (la base no puede verificar un enmascarado; queda en el código, con pruebas).
- Datos de terceros que pueden colarse en evidencias o archivos.

## 11. Quién escribe qué

**Aplica si:** hay más de un proceso que escribe (API, procesos en segundo plano, tareas programadas, respaldos).

- Un rol de base de datos por proceso con solo los permisos que necesita, hasta nivel columna si hace falta.
- Comprueba que los permisos alcanzan para cada transición de estado que ese proceso hace.

## 12. Reglas que garantiza la base de datos

**Aplica si:** siempre.

Para cada regla de negocio, decide si la garantiza la base (`UNIQUE`, índice único parcial, `CHECK`, llave foránea, trigger, permisos) o el código. Lo que la base puede garantizar, lo garantiza; lo que no, se declara con la prueba que lo cubre.

## Detalles menores (decídelos tú y decláralos)

- Catálogos como `text` + `CHECK` en lugar de `ENUM` nativo cuando cambiarlos en migraciones es incómodo.
- `jsonb` para configuraciones que se guardan como foto y se repiten tal cual; no para datos que se filtran o relacionan.
- Fechas como `timestamptz` en UTC.
- Archivos grandes: en la base hasta cierto tamaño, o en almacenamiento de objetos.
- Una fila especial en lugar de `NULL` con significado (por ejemplo, un usuario anónimo como fila real) cuando el `NULL` complicaría llaves, huellas o consultas.
