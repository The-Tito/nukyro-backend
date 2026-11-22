# Pruebas de la base de datos

Ejecutan el DDL de referencia y comprueban las reglas que garantiza PostgreSQL (§5 de `bd/modelo-datos.md`).

```bash
docker run -d --rm --name nukyro-pg16 -e POSTGRES_PASSWORD=local -e POSTGRES_DB=nukyro postgres:16
until docker exec nukyro-pg16 pg_isready -h 127.0.0.1 -U postgres; do sleep 1; done
docker exec -i nukyro-pg16 psql -U postgres -d nukyro -v ON_ERROR_STOP=1 -q < bd/schema.sql
docker exec -i nukyro-pg16 psql -U postgres -d nukyro -v ON_ERROR_STOP=1 -q < bd/seed-prueba.sql
docker exec -i nukyro-pg16 psql -U postgres -d nukyro -v ON_ERROR_STOP=1 -q < bd/pruebas/pruebas-reglas.sql
docker stop nukyro-pg16
```

Resultado esperado: 52 líneas `PASS` y `== Todas las pruebas pasaron ==`. La línea `ERROR` de T10b es esperada: es el rechazo al `COMMIT`.

Último resultado: 2026-11-22, PostgreSQL 16.15, 52/52 (modelo v0.2).
