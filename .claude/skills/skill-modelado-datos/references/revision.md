# Revisión del modelo

Revisa el modelo como lo haría alguien que tiene que implementarlo y que quiere encontrarle fallas. Entrega las tres listas; si una queda vacía, revisa de nuevo antes de decir que no hay nada.

## Qué puede fallar

- **Procesos que no son atómicos:** operaciones que tocan la base y un sistema externo (proveedor de identidad, almacenamiento, API ajena). ¿Qué queda si falla a la mitad? ¿Hay reintento?
- **Permisos amplios:** un proceso con permiso de escribir en datos de cualquier dueño. ¿Qué lo protege de un error propio?
- **Huellas o llaves de negocio inestables:** si cambia un código o un catálogo, ¿los registros reaparecen como nuevos?
- **Datos que no deberían estar:** datos personales de terceros en evidencias, archivos o texto libre.
- **Información que se filtra por canales laterales:** búsquedas por hash que permiten adivinar valores, conteos que revelan datos de otros.
- **Crecimiento:** tablas sin límite ni purga.

## Casos que no cubre bien

Recorre cada caso de uso, en especial los flujos alternos y de excepción, y pregunta:

- ¿Cada transición de estado tiene quién la haga y permiso para hacerla?
- ¿Qué pasa si los datos importados cambian entre versiones?
- ¿Un usuario puede abusar de una regla para llegar a un estado que no merece (por ejemplo, borrar algo para cerrar pendientes)?
- ¿Los usuarios especiales (administradores, cuentas de servicio) se cuentan donde no deben?
- ¿Algún requerimiento quedó sin entidad, columna o regla que lo soporte? Haz la matriz mental requerimiento → elemento del modelo.

## Supuestos que hay que probar

Lista cada capacidad que el diseño da por hecha y que nadie ha comprobado en el stack real. Para cada una:

| Supuesto | Prueba técnica | Plan B si falla |
| --- | --- | --- |
| Ejemplo: las variables de sesión por transacción no se arrastran entre peticiones en el pool asíncrono | Dos peticiones seguidas en la misma conexión con usuarios distintos | Fijarlas en el evento de inicio de transacción |

Estas pruebas van **antes** de construir encima: si el supuesto falla, cambia el modelo.
