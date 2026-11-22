# Evaluación de insumos

Para cada insumo: búscalo (puede tener otro nombre o estar dentro de otro documento), califica su estado y anota qué decisión del modelo queda bloqueada si falta.

**Estados:** Completo · Parcial (existe pero le falta algo de la columna «Calidad mínima») · Ausente.

## Imprescindibles

Sin estos el veredicto es «Insuficiente».

| Insumo | Calidad mínima para modelar | Qué alimenta del modelo |
| --- | --- | --- |
| **Requerimientos funcionales** | Cada requerimiento dice qué actor hace qué sobre qué cosa. Se pueden subrayar sustantivos (entidades) y verbos (operaciones). Tienen identificadores estables. | Entidades, atributos principales, relaciones, operaciones de escritura |
| **Reglas de negocio** (pueden estar dentro de los requerimientos) | Restricciones explícitas: unicidad, límites, quién puede qué, qué pasa con los dependientes al borrar. | Restricciones `UNIQUE`, `CHECK`, llaves foráneas, comportamiento al borrar |
| **Actores y roles** | Lista de tipos de usuario y qué ve o modifica cada uno. Si hay varios clientes u organizaciones, quién es dueño de qué. | Propiedad de los datos, aislamiento, privilegios |
| **Motor de base de datos** | Cuál es, o al menos relacional o documental. | Tipos, capacidades disponibles (RLS, `jsonb`, triggers) |

## Muy recomendables

Si faltan, el veredicto es como mucho «Suficiente con supuestos».

| Insumo | Calidad mínima | Qué alimenta | Qué falla sin él |
| --- | --- | --- | --- |
| **Casos de uso con flujos alternos y excepciones** | Además del flujo feliz: cancelaciones, errores, reintentos, qué pasa a medias | Estados, transiciones, casos borde | Estados sin final definido, transiciones imposibles |
| **Diagramas o descripción de estados** | Estados de cada entidad que los tiene y qué los cambia | Máquinas de estado, catálogos | Estados que mezclan dimensiones independientes |
| **Ciclo de vida y borrado** | Qué se puede borrar, qué se conserva, por cuánto tiempo | Borrado físico o lógico, cascadas, retención | Datos huérfanos o historial que se pierde |
| **Requisitos no funcionales de datos** | Volumen esperado, auditoría, privacidad, retención, respaldos | Granularidad, índices, bitácora, cifrado | Tablas que crecen sin control, auditoría imposible |
| **Contexto legal** | País y tipo de datos personales | Anonimización, derechos de los titulares (en México, ARCO), plazos | Incumplimiento descubierto tarde |

## Útiles

Mejoran el modelo pero no bloquean.

| Insumo | Qué alimenta |
| --- | --- |
| Arquitectura: componentes, procesos en segundo plano, proveedor de autenticación | Roles de base de datos, fuente de verdad de la identidad, quién escribe qué |
| Pantallas, listados, filtros y reportes | Patrones de consulta, índices, qué se calcula y qué se guarda |
| Estadísticas o métricas que se piden | Si deben sobrevivir a los borrados, tablas de hechos |
| Integraciones e importaciones de datos externos | Versionado, llaves estables, idempotencia |
| Contrato de la API, si ya existe | Identificadores expuestos, nombres, paginación |

## Cómo detectar huecos aunque el documento exista

Hazte estas preguntas al leer. Cada «no sé» es un hueco que va al informe:

- ¿Puedo listar todas las entidades y decir quién es dueño de cada una?
- Para cada entidad con estados: ¿sé todos los estados, cuál es el inicial, cuáles son finales y qué los cambia?
- ¿Sé qué pasa con los dependientes cuando se borra cada entidad?
- ¿Sé qué datos tienen historial y cuáles solo importa su valor actual?
- ¿Sé si algún dato viene de fuera y puede cambiar (versiones, sincronización)?
- ¿Sé qué consultas o pantallas van a ser las más frecuentes?
- ¿Sé si hay datos sensibles (credenciales, datos personales, datos de terceros)?
- ¿Sé si las estadísticas tienen que sobrevivir cuando un usuario se da de baja?

## Preguntas al usuario

Si eliges preguntar en lugar de pedir un documento:

- Cerradas o con opciones, nunca «cuéntame más sobre…».
- Máximo 10 en total, agrupadas por tema y ordenadas por impacto en el modelo.
- Con tu suposición por defecto, para que el usuario solo corrija lo que no coincide: «Supongo que un usuario puede tener varios proyectos y cada proyecto un solo dueño. ¿Correcto?».
