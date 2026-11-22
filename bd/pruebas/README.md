# Pruebas de la base de datos

Comprueban el DDL de referencia (`bd/schema.sql`) y la semilla en un PostgreSQL 16 desechable (§5 de
`bd/modelo-datos.md`, ADR-007, defectos 2 a 9 de la etapa 2).

```bash
bd/pruebas/ejecutar.sh
```

Requiere Docker. El script levanta `postgres:16` con nombre único (`nukyro-t09-<pid>`, sin puerto publicado) y
lo borra al terminar (trap; solo ese contenedor). Crea como bootstrap `nukyro_owner` (sin SUPERUSER ni
CREATEROLE, dueño de cada base) y los cuatro roles de grupo; aplica `schema.sql` y `seed-prueba.sql` **como
`nukyro_owner`** en una base nueva por suite; corre las tres suites aunque una falle y termina con código 1 ante
cualquier FAIL, error de psql o conteo de PASS menor al esperado (constantes `ESPERADO_*` del script).
`GUARDAR=<carpeta>` conserva los registros completos; `MOSTRAR=1` los imprime.

| Suite | Archivo | Qué prueba |
|---|---|---|
| reglas | `pruebas-reglas.sql` | Reglas de integridad del §5 (T01 a T44). Se detiene en el primer FAIL |
| defectos | `pruebas-defectos.sql` | Defectos 2 a 9 y hitos de una sola escritura (T-14): hechos y funciones del owner, xmin, umbral de 10, FK de administradores, ciclo de la versión, permisos por columna, primera sesión. Cuenta todos los FAIL |
| concurrencia | `pruebas-concurrencia.sh` | Dos sesiones psql: inicios simultáneos, dos archivos simultáneos, editar contra publicar (dos órdenes), caducidad contra actividad |

La línea `ERROR` de T10b es esperada: es el rechazo al `COMMIT` de la referencia diferida.
`evidencia-rojo.md` registra lo que falló al correr estas pruebas contra el esquema original, antes de corregir.

Resultado esperado: `reglas: 57 PASS`, `defectos: 197 PASS`, `concurrencia: 15 PASS` y `== TODAS LAS SUITES PASARON ==`.

Último resultado: 2026-11-22, PostgreSQL 16, esquema con los defectos 2 a 9 corregidos: 57 + 184 + 15, 0 FAIL.

## Lo que no prueban

- Que el orden físico de las filas reescritas sea aleatorio (solo que comparten xmin).
- RDS, Cognito ni la aplicación (S-04); los roles de conexión reales se crean por entorno.
- Interbloqueos entre el orden de bloqueo de la API (cuenta, participante, sesiones) y el de las funciones: el orden
  se documenta en `schema.sql`; la API debe respetarlo.
