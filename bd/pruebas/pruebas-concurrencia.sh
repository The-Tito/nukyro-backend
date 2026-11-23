#!/usr/bin/env bash
# =====================================================================
# Nukyro · Pruebas de concurrencia con dos sesiones psql (T-09)
#   CC1  dos inicios simultáneos de sesión (defecto 9)
#   CC2  dos archivos simultáneos sin pérdida de hechos (defecto 2/8)
#   CC3  editar contra publicar, en los dos órdenes (defecto 6)
#   CC4  la caducidad revalida la actividad tras esperar el bloqueo (defecto 8)
#   CC5  dos vinculaciones del mismo navegador (defecto 9, RF-076)
#   CC6  vincular contra una sesión que se inicia en el navegador (defecto 9)
# Uso: C=<contenedor> bash bd/pruebas/pruebas-concurrencia.sh <base>
# La base ya tiene schema.sql y la semilla (las aplica ejecutar.sh).
# Imprime «PASS ...» o «FAIL ...» por prueba y termina con código 1 si hubo FAIL.
# =====================================================================
set -u
DB="${1:?uso: pruebas-concurrencia.sh <base>}"
C="${C:?falta la variable C con el nombre del contenedor}"
L="$(mktemp -d "${TMPDIR:-/tmp}/nukyro-conc.XXXXXX")"
trap 'rm -rf "$L"' EXIT
FALLOS=0

psq() { docker exec -i "$C" psql -X -q -At -v ON_ERROR_STOP=1 -U postgres -d "$DB" "$@"; }
pasa() { echo "PASS $1"; }
falla() { echo "FAIL $1: $2"; FALLOS=$((FALLOS + 1)); }
# comprobar <nombre> <esperado> <obtenido>
comprobar() { if [ "$2" = "$3" ]; then pasa "$1"; else falla "$1" "se esperaba [$2], llegó [$3]"; fi; }

V1=00000000-0000-0000-0000-000000000011
D01=00000000-0000-0000-0000-000000000042
OPT_A=00000000-0000-0000-0000-000000000051
OPT_B=00000000-0000-0000-0000-000000000052

# --------------------------- Preparación ------------------------------
psq <<SQL || { falla "preparación" "no se pudieron crear los datos"; exit 1; }
SET search_path = nukyro, public;
-- CC1: participante nuevo
INSERT INTO participants (id, secret_hash) VALUES ('00000000-0000-0000-0000-00000000c001', sha256('c1'));
-- CC2: dos anónimos con una sesión y una decisión cada uno
INSERT INTO participants (id, secret_hash) VALUES
  ('00000000-0000-0000-0000-00000000c002', sha256('c2')), ('00000000-0000-0000-0000-00000000c003', sha256('c3'));
INSERT INTO sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session) VALUES
  ('00000000-0000-0000-0000-0000000c0a02', '00000000-0000-0000-0000-00000000c002', '$V1', '$D01', true, false),
  ('00000000-0000-0000-0000-0000000c0a03', '00000000-0000-0000-0000-00000000c003', '$V1', '$D01', true, false);
INSERT INTO session_decisions (session_id, scenario_version_id, node_id, option_id) VALUES
  ('00000000-0000-0000-0000-0000000c0a02', '$V1', '$D01', '$OPT_A'),
  ('00000000-0000-0000-0000-0000000c0a03', '$V1', '$D01', '$OPT_B');
-- CC3: dos escenarios, cada uno con un borrador y un nodo
INSERT INTO scenarios (id, key, title) VALUES
  ('00000000-0000-0000-0000-0000000000e1', 'CC3A', 'Editar primero'), ('00000000-0000-0000-0000-0000000000e2', 'CC3B', 'Publicar primero');
INSERT INTO scenario_versions (id, scenario_id, version_number, title) VALUES
  ('00000000-0000-0000-0000-0000000001e1', '00000000-0000-0000-0000-0000000000e1', 1, 'CC3A v1'),
  ('00000000-0000-0000-0000-0000000001e2', '00000000-0000-0000-0000-0000000000e2', 1, 'CC3B v1');
INSERT INTO nodes (id, version_id, key, node_type, title, body) VALUES
  ('00000000-0000-0000-0000-0000000002e1', '00000000-0000-0000-0000-0000000001e1', 'N', 'info', 'original', 'b'),
  ('00000000-0000-0000-0000-0000000002e2', '00000000-0000-0000-0000-0000000001e2', 'N', 'info', 'original', 'b');
-- CC4: anónimo inactivo con una sesión
INSERT INTO participants (id, secret_hash, last_activity_at) VALUES
  ('00000000-0000-0000-0000-00000000c004', sha256('c4'), now() - interval '100 days');
INSERT INTO sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session) VALUES
  ('00000000-0000-0000-0000-0000000c0a04', '00000000-0000-0000-0000-00000000c004', '$V1', '$D01', true, false);
-- CC5 y CC6: una cuenta con su participante y una sesión antigua; un navegador con una sesión más reciente
INSERT INTO accounts (id, cognito_sub, email, nickname) VALUES
  ('00000000-0000-0000-0000-0000000000a5', 'cc5', 'cc5@example.test', 'cc5'),
  ('00000000-0000-0000-0000-0000000000a6', 'cc6', 'cc6@example.test', 'cc6');
INSERT INTO participants (id, account_id) VALUES
  ('00000000-0000-0000-0000-00000000c005', '00000000-0000-0000-0000-0000000000a5'),
  ('00000000-0000-0000-0000-00000000c007', '00000000-0000-0000-0000-0000000000a6');
INSERT INTO participants (id, secret_hash) VALUES
  ('00000000-0000-0000-0000-00000000c006', sha256('c6')), ('00000000-0000-0000-0000-00000000c008', sha256('c8'));
INSERT INTO sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first, started_at, last_activity_at) VALUES
  ('00000000-0000-0000-0000-0000000c0a05', '00000000-0000-0000-0000-00000000c005', '$V1', '$D01', true, now() - interval '5 hours', now() - interval '5 hours'),
  ('00000000-0000-0000-0000-0000000c0a06', '00000000-0000-0000-0000-00000000c006', '$V1', '$D01', true, now() - interval '2 hours', now() - interval '2 hours'),
  ('00000000-0000-0000-0000-0000000c0a07', '00000000-0000-0000-0000-00000000c007', '$V1', '$D01', true, now() - interval '5 hours', now() - interval '5 hours'),
  ('00000000-0000-0000-0000-0000000c0a08', '00000000-0000-0000-0000-00000000c008', '$V1', '$D01', true, now() - interval '2 hours', now() - interval '2 hours');
SQL

# ejecuta un script SQL en segundo plano: salida en $L/<nombre>.out y código en $L/<nombre>.rc
fondo() { # <nombre> <sql>
    ( printf '%s\n' "$2" | psq > "$L/$1.out" 2>&1; echo $? > "$L/$1.rc" ) &
}

# --------------------------- CC1 · dos inicios ------------------------
INS1="INSERT INTO nukyro.sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session)
      VALUES ('%s', '00000000-0000-0000-0000-00000000c001', '$V1', '$D01', true, false);"
fondo cc1a "BEGIN; $(printf "$INS1" 00000000-0000-0000-0000-0000000c0a11) SELECT pg_sleep(2); COMMIT;"
sleep 0.7
fondo cc1b "BEGIN; $(printf "$INS1" 00000000-0000-0000-0000-0000000c0a12) COMMIT;"
wait
comprobar "CC1 los dos inicios terminaron sin error" "0/0" "$(cat "$L/cc1a.rc")/$(cat "$L/cc1b.rc")"
comprobar "CC1 dos inicios simultáneos: una sola primera sesión (2 sesiones, 1 primera)" "2/1" \
    "$(psq -c "SELECT count(*) || '/' || count(*) FILTER (WHERE is_first_session) FROM nukyro.sessions WHERE participant_id = '00000000-0000-0000-0000-00000000c001'")"

# --------------------------- CC2 · dos archivos -----------------------
fondo cc2a "BEGIN; SET ROLE nukyro_api; SELECT nukyro.erase_anonymous_participant('00000000-0000-0000-0000-00000000c002'); SELECT pg_sleep(2); COMMIT;"
sleep 0.7
fondo cc2b "SELECT clock_timestamp() AS t0 \\gset
SET ROLE nukyro_api;
SELECT nukyro.erase_anonymous_participant('00000000-0000-0000-0000-00000000c003');
SELECT (extract(epoch FROM clock_timestamp() - :'t0'::timestamptz) * 1000)::int;"
wait
comprobar "CC2 los dos archivos terminaron sin error" "0/0" "$(cat "$L/cc2a.rc")/$(cat "$L/cc2b.rc")"
ms=$(tail -1 "$L/cc2b.out")
if [ "${ms:-0}" -ge 500 ] 2>/dev/null; then pasa "CC2 el segundo archivo esperó al primero (${ms} ms)"; else falla "CC2 el segundo archivo esperó al primero" "tardó ${ms:-?} ms"; fi
comprobar "CC2 sin pérdida: 2 hechos de sesión, 2 de decisión y ningún participante" "2/2/0" \
    "$(psq -c "SELECT (SELECT count(*) FROM nukyro.session_facts) || '/' || (SELECT count(*) FROM nukyro.decision_facts) || '/' || (SELECT count(*) FROM nukyro.participants WHERE id IN ('00000000-0000-0000-0000-00000000c002', '00000000-0000-0000-0000-00000000c003'))")"
comprobar "CC2 los hechos de ambos archivos comparten un solo xmin" "1" \
    "$(psq -c "SELECT count(DISTINCT x) FROM (SELECT xmin::text x FROM nukyro.session_facts UNION ALL SELECT xmin::text FROM nukyro.decision_facts UNION ALL SELECT xmin::text FROM nukyro.topic_facts) u")"
comprobar "CC2 las dos decisiones (D01-A y D01-B) llegaron a los hechos" "D01-A,D01-B" \
    "$(psq -c "SELECT string_agg(option_key, ',' ORDER BY option_key) FROM nukyro.decision_facts")"

# --------------------------- CC3a · editar primero, luego publicar ----
fondo cc3a_edit "BEGIN; SET ROLE nukyro_admin;
UPDATE nukyro.nodes SET title = 'editado' WHERE id = '00000000-0000-0000-0000-0000000002e1';
SELECT pg_sleep(3); COMMIT;"
sleep 1
fondo cc3a_pub "SELECT clock_timestamp() AS t0 \\gset
SET ROLE nukyro_admin;
UPDATE nukyro.scenario_versions SET status = 'published', published_at = now() WHERE id = '00000000-0000-0000-0000-0000000001e1';
SELECT (extract(epoch FROM clock_timestamp() - :'t0'::timestamptz) * 1000)::int;"
wait
comprobar "CC3a editar y publicar terminaron sin error" "0/0" "$(cat "$L/cc3a_edit.rc")/$(cat "$L/cc3a_pub.rc")"
ms=$(tail -1 "$L/cc3a_pub.out")
if [ "${ms:-0}" -ge 800 ] 2>/dev/null; then pasa "CC3a publicar esperó a que terminara la edición en curso (${ms} ms)"; else falla "CC3a publicar esperó a la edición" "tardó ${ms:-?} ms, no esperó"; fi
comprobar "CC3a la edición quedó antes de publicar: versión publicada con el título editado" "published/editado" \
    "$(psq -c "SELECT v.status || '/' || n.title FROM nukyro.scenario_versions v JOIN nukyro.nodes n ON n.version_id = v.id WHERE v.id = '00000000-0000-0000-0000-0000000001e1'")"

# --------------------------- CC3b · publicar primero, luego editar ----
fondo cc3b_pub "BEGIN; SET ROLE nukyro_admin;
UPDATE nukyro.scenario_versions SET status = 'published', published_at = now() WHERE id = '00000000-0000-0000-0000-0000000001e2';
SELECT pg_sleep(3); COMMIT;"
sleep 1
fondo cc3b_edit "SET ROLE nukyro_admin;
UPDATE nukyro.nodes SET title = 'tarde' WHERE id = '00000000-0000-0000-0000-0000000002e2';"
wait
comprobar "CC3b la publicación terminó bien" "0" "$(cat "$L/cc3b_pub.rc")"
if [ "$(cat "$L/cc3b_edit.rc")" != "0" ] && grep -q 'published' "$L/cc3b_edit.out"; then
    pasa "CC3b la edición que llegó tras publicar fue rechazada"
else
    falla "CC3b la edición tras publicar debía rechazarse" "código $(cat "$L/cc3b_edit.rc"): $(head -c 200 "$L/cc3b_edit.out")"
fi
comprobar "CC3b el contenido publicado quedó intacto" "published/original" \
    "$(psq -c "SELECT v.status || '/' || n.title FROM nukyro.scenario_versions v JOIN nukyro.nodes n ON n.version_id = v.id WHERE v.id = '00000000-0000-0000-0000-0000000001e2'")"

# --------------------------- CC4 · caducidad contra actividad ---------
SF0=$(psq -c "SELECT count(*) FROM nukyro.session_facts")
fondo cc4a "BEGIN; SET ROLE nukyro_api;
UPDATE nukyro.participants SET last_activity_at = now() WHERE id = '00000000-0000-0000-0000-00000000c004';
SELECT pg_sleep(2); COMMIT;"
sleep 0.7
fondo cc4b "SET ROLE nukyro_jobs;
SELECT nukyro.expire_anonymous_participants(now() - interval '90 days');"
wait
comprobar "CC4 la caducidad no borró a quien volvió justo antes (devuelve 0)" "0" "$(tail -1 "$L/cc4b.out")"
comprobar "CC4 el participante y su sesión siguen vivos; sin hechos nuevos" "1/1/$SF0" \
    "$(psq -c "SELECT (SELECT count(*) FROM nukyro.participants WHERE id = '00000000-0000-0000-0000-00000000c004') || '/' || (SELECT count(*) FROM nukyro.sessions WHERE participant_id = '00000000-0000-0000-0000-00000000c004') || '/' || (SELECT count(*) FROM nukyro.session_facts)")"

# --------------------------- CC5 · dos vinculaciones del mismo navegador (RF-076)
LINK5="SELECT nukyro.link_participant('00000000-0000-0000-0000-0000000000a5', sha256('c6'));"
fondo cc5a "BEGIN; SET ROLE nukyro_api; $LINK5 SELECT pg_sleep(2); COMMIT;"
sleep 0.7
fondo cc5b "SET ROLE nukyro_api; $LINK5"
wait
comprobar "CC5 las dos vinculaciones terminaron sin error" "0/0" "$(cat "$L/cc5a.rc")/$(cat "$L/cc5b.rc")"
comprobar "CC5 una traslada y la otra no hace nada (idempotente)" "merged/none" "$(head -1 "$L/cc5a.out")/$(tail -1 "$L/cc5b.out")"
comprobar "CC5 queda un participante, dos sesiones y una sola primera" "1/2/1" \
    "$(psq -c "SELECT (SELECT count(*) FROM nukyro.participants WHERE id IN ('00000000-0000-0000-0000-00000000c005', '00000000-0000-0000-0000-00000000c006')) || '/' || count(*) || '/' || count(*) FILTER (WHERE is_first_session) FROM nukyro.sessions WHERE participant_id = '00000000-0000-0000-0000-00000000c005'")"

# --------------------------- CC6 · vincular contra una sesión que se inicia
fondo cc6a "BEGIN; SET ROLE nukyro_api;
INSERT INTO nukyro.sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first)
VALUES ('00000000-0000-0000-0000-0000000c0a09', '00000000-0000-0000-0000-00000000c008', '$V1', '$D01', true);
SELECT pg_sleep(2); COMMIT;"
sleep 0.7
fondo cc6b "SET ROLE nukyro_api; SELECT nukyro.link_participant('00000000-0000-0000-0000-0000000000a6', sha256('c8'));"
wait
comprobar "CC6 la sesión nueva y la vinculación terminaron sin error" "0/0" "$(cat "$L/cc6a.rc")/$(cat "$L/cc6b.rc")"
comprobar "CC6 la vinculación esperó y trasladó las tres sesiones" "merged/3" \
    "$(tail -1 "$L/cc6b.out")/$(psq -c "SELECT count(*) FROM nukyro.sessions WHERE participant_id = '00000000-0000-0000-0000-00000000c007'")"
comprobar "CC6 queda una sola primera sesión: la más antigua" "1/0000000c0a07" \
    "$(psq -c "SELECT count(*) || '/' || max(right(id::text, 12)) FROM nukyro.sessions WHERE participant_id = '00000000-0000-0000-0000-00000000c007' AND is_first_session")"

echo
if [ "$FALLOS" -eq 0 ]; then echo "== Todas las pruebas de concurrencia pasaron =="; exit 0; fi
echo "FAIL concurrencia: $FALLOS prueba(s) fallaron"
exit 1
