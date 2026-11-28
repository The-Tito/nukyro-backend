#!/usr/bin/env bash
# =====================================================================
# Nukyro · Ejecuta todas las pruebas de la base en un PostgreSQL 16
# desechable. Uso, desde cualquier carpeta:   bd/pruebas/ejecutar.sh
#
# - Un contenedor postgres:16 con nombre único (nukyro-t09-<pid>), sin
#   puerto publicado; un trap borra solo ese contenedor.
# - Bootstrap como superusuario: nukyro_owner (sin SUPERUSER ni CREATEROLE,
#   dueño de cada base) y los cuatro roles de grupo.
# - schema.sql y la semilla se aplican COMO nukyro_owner, en una base
#   nueva por suite (reglas, defectos, concurrencia).
# - Falla (código 1) ante cualquier FAIL, error de psql o conteo de PASS
#   menor al esperado. Corre todas las suites aunque una falle, para ver
#   el cuadro completo.
# =====================================================================
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RAIZ"

# Conteos mínimos de líneas PASS (si cambia una prueba, se actualiza aquí)
ESPERADO_REGLAS=57
ESPERADO_DEFECTOS=234
ESPERADO_CONCURRENCIA=21

C="nukyro-t09-$$"
LOGS="$(mktemp -d "${TMPDIR:-/tmp}/nukyro-pruebas.XXXXXX")"
FALLOS=0

limpiar() {
    # GUARDAR=<carpeta> conserva los registros completos de cada suite
    if [ -n "${GUARDAR:-}" ]; then mkdir -p "$GUARDAR" && cp "$LOGS"/*.log "$GUARDAR"/ 2>/dev/null || true; fi
    docker rm -f "$C" >/dev/null 2>&1 || true
    rm -rf "$LOGS"
}
trap limpiar EXIT
trap 'exit 130' INT TERM

psq() { docker exec -i "$C" psql -X -q -v ON_ERROR_STOP=1 "$@"; }
export C

echo "== Levantando postgres:16 desechable ($C) =="
docker run -d --rm --name "$C" -e POSTGRES_PASSWORD=local postgres:16 >/dev/null || { echo "FAIL no se pudo crear el contenedor"; exit 1; }
listo=0
for _ in $(seq 1 90); do
    # por TCP: el servidor temporal de initdb solo escucha por socket
    if docker exec "$C" pg_isready -q -h 127.0.0.1 -U postgres; then listo=1; break; fi
    sleep 1
done
[ "$listo" = 1 ] || { echo "FAIL postgres no arrancó"; exit 1; }

psq -U postgres -d postgres <<'SQL' || { echo "FAIL bootstrap de roles"; exit 1; }
CREATE ROLE nukyro_owner LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS;
CREATE ROLE nukyro_api       NOLOGIN;
CREATE ROLE nukyro_admin     NOLOGIN;
CREATE ROLE nukyro_jobs      NOLOGIN;
CREATE ROLE nukyro_analytics NOLOGIN;
SQL

# crear_base <nombre> : base nueva, esquema y semilla aplicados como nukyro_owner
crear_base() {
    psq -U postgres -d postgres -c "CREATE DATABASE $1 OWNER nukyro_owner" || return 1
    psq -U nukyro_owner -d "$1" < bd/schema.sql > "$LOGS/schema-$1.log" 2>&1 || { cat "$LOGS/schema-$1.log"; return 1; }
    psq -U nukyro_owner -d "$1" < bd/seed-prueba.sql > "$LOGS/seed-$1.log" 2>&1 || { cat "$LOGS/seed-$1.log"; return 1; }
}

# evaluar <suite> <log> <esperado> <código de salida>
evaluar() {
    local pass fail
    pass=$(grep -cE '(NOTICE:  |^)PASS' "$2" || true)
    fail=$(grep -cE '(NOTICE:  |ERROR:  |^)FAIL' "$2" || true)
    echo "-- $1: $pass PASS, $fail FAIL (esperado >= $3 PASS), código $4"
    if [ "$4" -ne 0 ] || [ "$fail" -ne 0 ] || [ "$pass" -lt "$3" ]; then
        FALLOS=$((FALLOS + 1))
        grep -E '(NOTICE:  |ERROR:  |^)FAIL|^ERROR|psql:' "$2" | head -80
    fi
}

correr_sql() { # <suite> <archivo> <esperado>
    local log="$LOGS/$1.log" rc=0
    if ! crear_base "nukyro_$1"; then
        echo "-- $1: FAIL no se pudo crear la base (esquema o semilla)"; FALLOS=$((FALLOS + 1)); return
    fi
    psq -U postgres -d "nukyro_$1" < "$2" > "$log" 2>&1 || rc=$?
    cp "$log" "$LOGS/ultimo-$1.log"
    evaluar "$1" "$log" "$3" "$rc"
}

echo "== Suite reglas (pruebas-reglas.sql) =="
correr_sql reglas bd/pruebas/pruebas-reglas.sql "$ESPERADO_REGLAS"

echo "== Suite defectos (pruebas-defectos.sql) =="
correr_sql defectos bd/pruebas/pruebas-defectos.sql "$ESPERADO_DEFECTOS"

echo "== Suite concurrencia (pruebas-concurrencia.sh) =="
if crear_base nukyro_conc; then
    rc=0
    bash bd/pruebas/pruebas-concurrencia.sh nukyro_conc > "$LOGS/conc.log" 2>&1 || rc=$?
    evaluar concurrencia "$LOGS/conc.log" "$ESPERADO_CONCURRENCIA" "$rc"
    grep -E 'PASS|FAIL' "$LOGS/conc.log" | sed 's/^/   /'
else
    echo "-- concurrencia: FAIL no se pudo crear la base"; FALLOS=$((FALLOS + 1))
fi

# MOSTRAR=1 imprime el detalle completo de cada suite
if [ "${MOSTRAR:-0}" = 1 ]; then cat "$LOGS"/ultimo-*.log "$LOGS/conc.log" 2>/dev/null; fi

echo
if [ "$FALLOS" -eq 0 ]; then
    echo "== TODAS LAS SUITES PASARON =="
    exit 0
fi
echo "== $FALLOS SUITE(S) CON FALLOS =="
exit 1
