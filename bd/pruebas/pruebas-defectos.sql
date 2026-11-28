-- =====================================================================
-- Nukyro · Pruebas de los defectos 2 a 9 del esquema (T-09, S-03)
--   2/3/8  ADR-007: archivo de hechos por funciones, sin vínculo por xmin
--   4      FK created_by / published_by en RESTRICT
--   5      ciclo de vida de la versión (insertar, retirar, alterar)
--   6      edición contra publicación (FOR SHARE; ver concurrencia)
--   7      permisos por columna y campos inmutables
--   9      primera sesión calculada por la base
-- Requiere schema.sql y seed-prueba.sql en una base NUEVA, aplicados por
-- nukyro_owner. Ejecutar como superusuario (usa SET ROLE a los roles de grupo):
--   psql -v ON_ERROR_STOP=1 -f bd/pruebas/pruebas-defectos.sql
-- A diferencia de pruebas-reglas.sql, una prueba que falla NO detiene el
-- script: imprime «FAIL» y sigue, para ver todos los defectos de una vez.
-- Al final, si hubo algún FAIL, el script termina con error.
-- La concurrencia está en pruebas-concurrencia.sh.
-- =====================================================================
\set ON_ERROR_STOP 1
SET search_path = nukyro, public;
SET client_min_messages = notice;
SELECT set_config('nukyro_t.fails', '0', false) AS "contador de fallos";

-- ------------------------- Ayudantes ---------------------------------
CREATE FUNCTION pg_temp.fail(p_name text, p_msg text) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    RAISE NOTICE 'FAIL %: %', p_name, p_msg;
    PERFORM set_config('nukyro_t.fails',
        (coalesce(nullif(current_setting('nukyro_t.fails', true), ''), '0')::int + 1)::text, false);
END $$;

-- La sentencia debe fallar con ese SQLSTATE; si no falla, se deshace y se reporta
CREATE FUNCTION pg_temp.expect(p_name text, p_sql text, p_state text) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE v_ran boolean := false;
BEGIN
    BEGIN
        EXECUTE p_sql;
        v_ran := true;
        RAISE EXCEPTION USING ERRCODE = 'XX999', MESSAGE = '__sin_fallo__';
    EXCEPTION WHEN OTHERS THEN
        IF v_ran THEN
            PERFORM pg_temp.fail(p_name, format('no falló (se esperaba %s)', p_state));
        ELSIF SQLSTATE = p_state THEN
            RAISE NOTICE 'PASS %  (% %)', p_name, SQLSTATE, left(SQLERRM, 90);
        ELSE
            PERFORM pg_temp.fail(p_name, format('se esperaba %s, llegó %s %s', p_state, SQLSTATE, left(SQLERRM, 120)));
        END IF;
    END;
END $$;

-- La sentencia debe ejecutarse sin error (y sus efectos se conservan)
CREATE FUNCTION pg_temp.allow(p_name text, p_sql text) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE p_sql;
    RAISE NOTICE 'PASS %', p_name;
EXCEPTION WHEN OTHERS THEN
    PERFORM pg_temp.fail(p_name, format('%s %s', SQLSTATE, left(SQLERRM, 120)));
END $$;

CREATE FUNCTION pg_temp.ok(p_name text, p_cond boolean) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    IF p_cond IS TRUE THEN RAISE NOTICE 'PASS %', p_name;
    ELSE PERFORM pg_temp.fail(p_name, 'la condición no se cumple'); END IF;
END $$;

-- La consulta (texto) debe devolver true; un error cuenta como FAIL
CREATE FUNCTION pg_temp.chk(p_name text, p_sql text) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE v boolean;
BEGIN
    EXECUTE p_sql INTO v;
    IF v IS TRUE THEN RAISE NOTICE 'PASS %', p_name;
    ELSE PERFORM pg_temp.fail(p_name, format('devolvió %s', coalesce(v::text, 'NULL'))); END IF;
EXCEPTION WHEN OTHERS THEN
    PERFORM pg_temp.fail(p_name, format('%s %s', SQLSTATE, left(SQLERRM, 120)));
END $$;

-- Preparación que no es una prueba: si falla, se reporta, pero no cuenta como PASS
CREATE FUNCTION pg_temp.fx(p_sql text) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE p_sql;
EXCEPTION WHEN OTHERS THEN
    PERFORM pg_temp.fail('preparación', format('%s %s', SQLSTATE, left(SQLERRM, 120)));
END $$;

CREATE FUNCTION pg_temp.finish() RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    IF current_setting('nukyro_t.fails')::int > 0 THEN
        RAISE EXCEPTION 'FAIL defectos: % prueba(s) fallaron', current_setting('nukyro_t.fails');
    END IF;
    RAISE NOTICE '== Todas las pruebas de defectos pasaron ==';
END $$;

-- Ids legibles: id('bb', 101) = 00000000-0000-0000-0000-bb0000000101
CREATE FUNCTION pg_temp.id(p_prefix text, p_n int) RETURNS uuid
LANGUAGE sql IMMUTABLE AS $$
    SELECT ('00000000-0000-0000-0000-' || p_prefix || lpad(p_n::text, 10, '0'))::uuid
$$;

-- Fixtures (compatibles con el esquema viejo y el nuevo: solo tablas y columnas comunes)
CREATE FUNCTION pg_temp.mk_anon(p_n int) RETURNS void LANGUAGE sql AS $$
    INSERT INTO nukyro.participants (id, secret_hash)
    VALUES (pg_temp.id('bb', p_n), sha256(convert_to('secreto-' || p_n, 'UTF8')));
$$;

CREATE FUNCTION pg_temp.mk_account(p_n int, p_part int DEFAULT NULL, p_secret boolean DEFAULT false) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO nukyro.accounts (id, cognito_sub, email, nickname)
    VALUES (pg_temp.id('ac', p_n), 'sub-' || p_n, 'u' || p_n || '@example.test', 'nick' || p_n);
    IF p_part IS NOT NULL THEN
        INSERT INTO nukyro.participants (id, account_id, secret_hash)
        VALUES (pg_temp.id('bb', p_part), pg_temp.id('ac', p_n),
                CASE WHEN p_secret THEN sha256(convert_to('secreto-' || p_part, 'UTF8')) END);
    END IF;
END $$;

-- Sesión ligera sobre la versión 1, nodo D01; has_prior_session se envía en false
-- (en el esquema nuevo la base lo ignora y lo calcula)
CREATE FUNCTION pg_temp.mk_session(p_n int, p_part int, p_started timestamptz DEFAULT now() - interval '1 hour',
                                   p_self_first boolean DEFAULT true) RETURNS void LANGUAGE sql AS $$
    INSERT INTO nukyro.sessions (id, participant_id, scenario_version_id, current_node_id,
                                 self_reported_first, has_prior_session, started_at, last_activity_at)
    VALUES (pg_temp.id('cc', p_n), pg_temp.id('bb', p_part), '00000000-0000-0000-0000-000000000011',
            '00000000-0000-0000-0000-000000000042', p_self_first, false, p_started, p_started + interval '2 minutes');
$$;

-- Sesión completa: decisión, pre-test (1/1), causal (0/1), desenlace OUT1, 13.5 min.
-- Inicia el domingo 2026-11-29 23:00 (-06) = lunes 2026-11-30 05:00 UTC.
CREATE FUNCTION pg_temp.mk_rich_session(p_n int, p_part int) RETURNS void LANGUAGE plpgsql AS $$
DECLARE s uuid := pg_temp.id('cc', p_n);
BEGIN
    INSERT INTO nukyro.sessions (id, participant_id, scenario_version_id, current_node_id, outcome_node_id,
                                 self_reported_first, has_prior_session, started_at, pretest_completed_at,
                                 outcome_reached_at, completed_at, last_activity_at)
    VALUES (s, pg_temp.id('bb', p_part), '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000044',
            '00000000-0000-0000-0000-000000000044', true, false,
            '2026-11-29 23:00:00-06', '2026-11-29 23:01:00-06', '2026-11-29 23:11:00-06',
            '2026-11-29 23:13:30-06', '2026-11-29 23:13:30-06');
    INSERT INTO nukyro.session_decisions (id, session_id, scenario_version_id, node_id, option_id, justification_correct)
    VALUES (pg_temp.id('dd', p_n), s, '00000000-0000-0000-0000-000000000011',
            '00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000051', true);
    INSERT INTO nukyro.assessment_attempts (id, session_id, scenario_version_id, question_set_id) VALUES
        (pg_temp.id('a1', p_n), s, '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000091'),
        (pg_temp.id('a2', p_n), s, '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000092');
    INSERT INTO nukyro.assessment_answers (attempt_id, question_set_id, question_id, option_id) VALUES
        (pg_temp.id('a1', p_n), '00000000-0000-0000-0000-000000000091', '00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000b1'),
        (pg_temp.id('a2', p_n), '00000000-0000-0000-0000-000000000092', '00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-0000000000b4');
    -- se envía después de responder: un intento enviado no admite respuestas
    UPDATE nukyro.assessment_attempts SET submitted_at = '2026-11-29 23:01:00-06', answered_count = 1, correct_count = 1, score = 100
     WHERE id = pg_temp.id('a1', p_n);
    UPDATE nukyro.assessment_attempts SET submitted_at = '2026-11-29 23:12:00-06', answered_count = 1, correct_count = 0, score = 0
     WHERE id = pg_temp.id('a2', p_n);
END $$;

-- =====================================================================
-- A · Estructura de los hechos (defectos 2, 3, 8; ADR-007)
-- =====================================================================
SELECT pg_temp.chk('D2-01 session_facts sin closure_reason y con stopped_at_key',
 $q$SELECT NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'nukyro' AND table_name = 'session_facts' AND column_name = 'closure_reason')
        AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'nukyro' AND table_name = 'session_facts' AND column_name = 'stopped_at_key')$q$);
SELECT pg_temp.chk('D2-02 topic_facts existe con sus columnas',
 $q$SELECT (SELECT count(*) FROM information_schema.columns WHERE table_schema = 'nukyro' AND table_name = 'topic_facts'
             AND column_name IN ('id', 'scenario_version_id', 'week_start', 'set_type', 'topic', 'is_first_session', 'correct', 'total')) = 8$q$);
SELECT pg_temp.chk('D2-03 los hechos no llevan sesión, participante ni cuenta',
 $q$SELECT NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'nukyro'
                        AND table_name IN ('session_facts', 'decision_facts', 'topic_facts', 'survey_responses')
                        AND column_name IN ('session_id', 'participant_id', 'account_id', 'user_id'))$q$);
SELECT pg_temp.chk('D2-04 ningún rol de conexión tiene privilegio de tabla sobre los hechos',
 $q$SELECT NOT EXISTS (
      SELECT 1 FROM (VALUES ('nukyro_api'), ('nukyro_admin'), ('nukyro_jobs'), ('nukyro_analytics')) r(rol),
                    (VALUES ('nukyro.session_facts'), ('nukyro.decision_facts'), ('nukyro.topic_facts')) t(tabla),
                    (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE'), ('TRUNCATE'), ('REFERENCES'), ('TRIGGER')) p(priv)
       WHERE has_table_privilege(r.rol, t.tabla, p.priv))$q$);
SELECT pg_temp.chk('D2-05 ni privilegio de columna sobre los hechos',
 $q$SELECT NOT EXISTS (
      SELECT 1 FROM (VALUES ('nukyro_api'), ('nukyro_admin'), ('nukyro_jobs'), ('nukyro_analytics')) r(rol),
                    (VALUES ('nukyro.session_facts'), ('nukyro.decision_facts'), ('nukyro.topic_facts')) t(tabla),
                    (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('REFERENCES')) p(priv)
       WHERE has_any_column_privilege(r.rol, t.tabla, p.priv))$q$);
SELECT pg_temp.chk('D2-06 PUBLIC no tiene nada sobre los hechos',
 $q$SELECT (SELECT count(*) FROM pg_class WHERE relnamespace = 'nukyro'::regnamespace
             AND relname IN ('session_facts', 'decision_facts', 'topic_facts')) = 3
        AND NOT EXISTS (SELECT 1 FROM pg_class c, aclexplode(c.relacl) a
                         WHERE c.relnamespace = 'nukyro'::regnamespace
                           AND c.relname IN ('session_facts', 'decision_facts', 'topic_facts') AND a.grantee = 0)$q$);
SELECT pg_temp.chk('D2-07 survey_responses: api ni inserta ni lee (solo submit_survey); jobs y analítica no leen',
 $q$SELECT NOT has_table_privilege('nukyro_api', 'nukyro.survey_responses', 'INSERT')
        AND NOT has_table_privilege('nukyro_api', 'nukyro.survey_responses', 'SELECT')
        AND NOT has_table_privilege('nukyro_api', 'nukyro.survey_responses', 'UPDATE')
        AND NOT has_any_column_privilege('nukyro_jobs', 'nukyro.survey_responses', 'SELECT')
        AND NOT has_any_column_privilege('nukyro_analytics', 'nukyro.survey_responses', 'SELECT')$q$);

-- Todo rol es rechazado en lo prohibido (privilegios en ejecución)
SET ROLE nukyro_api;
SELECT pg_temp.expect('D3-01 api no inserta session_facts (RETURNING)',
 $q$INSERT INTO nukyro.session_facts (scenario_version_id, week_start, is_first_session, outcome_reached, evaluations_completed)
    VALUES ('00000000-0000-0000-0000-000000000011', date_trunc('week', now())::date, true, true, true) RETURNING id$q$, '42501');
SELECT pg_temp.expect('D3-02 api no inserta decision_facts',
 $q$INSERT INTO nukyro.decision_facts (scenario_version_id, week_start, decision_key, option_key, is_first_session)
    VALUES ('00000000-0000-0000-0000-000000000011', date_trunc('week', now())::date, 'D01', 'D01-A', true)$q$, '42501');
SELECT pg_temp.expect('D3-03 api no inserta topic_facts',
 $q$INSERT INTO nukyro.topic_facts (scenario_version_id, week_start, set_type, topic, is_first_session, correct, total)
    VALUES ('00000000-0000-0000-0000-000000000011', date_trunc('week', now())::date, 'pretest', 't', true, 1, 1)$q$, '42501');
SELECT pg_temp.expect('D3-04 api no lee session_facts', $q$SELECT count(*) FROM nukyro.session_facts$q$, '42501');
SELECT pg_temp.expect('D3-05 api no lee decision_facts', $q$SELECT count(*) FROM nukyro.decision_facts$q$, '42501');
SELECT pg_temp.expect('D3-06 api no lee topic_facts', $q$SELECT count(*) FROM nukyro.topic_facts$q$, '42501');
SELECT pg_temp.expect('D3-07 api no borra hechos', $q$DELETE FROM nukyro.session_facts$q$, '42501');
SELECT pg_temp.expect('D3-08 api no inserta encuestas directamente (T-16)',
 $q$INSERT INTO nukyro.survey_responses (scenario_version_id, week_start, is_first_session, usefulness)
    VALUES ('00000000-0000-0000-0000-000000000011', date_trunc('week', now())::date, true, 4)$q$, '42501');
SELECT pg_temp.expect('D3-09 api no lee las encuestas', $q$SELECT count(*) FROM nukyro.survey_responses$q$, '42501');
SELECT pg_temp.expect('D3-10 api no modifica las encuestas', $q$UPDATE nukyro.survey_responses SET usefulness = 5$q$, '42501');
RESET ROLE;

SET ROLE nukyro_jobs;
SELECT pg_temp.expect('D3-11 jobs no inserta session_facts',
 $q$INSERT INTO nukyro.session_facts (scenario_version_id, week_start, is_first_session, outcome_reached, evaluations_completed)
    VALUES ('00000000-0000-0000-0000-000000000011', date_trunc('week', now())::date, true, true, true)$q$, '42501');
SELECT pg_temp.expect('D3-12 jobs no lee session_facts', $q$SELECT count(*) FROM nukyro.session_facts$q$, '42501');
SELECT pg_temp.expect('D3-13 jobs no lee decision_facts', $q$SELECT count(*) FROM nukyro.decision_facts$q$, '42501');
SELECT pg_temp.expect('D3-14 jobs no lee topic_facts', $q$SELECT count(*) FROM nukyro.topic_facts$q$, '42501');
SELECT pg_temp.expect('D3-15 jobs no lee las encuestas', $q$SELECT count(*) FROM nukyro.survey_responses$q$, '42501');
SELECT pg_temp.expect('D8-01 jobs no borra participantes directamente', $q$DELETE FROM nukyro.participants$q$, '42501');
SELECT pg_temp.expect('D8-02 jobs no borra cuentas directamente', $q$DELETE FROM nukyro.accounts$q$, '42501');
SELECT pg_temp.expect('D8-03 jobs no actualiza cuentas', $q$UPDATE nukyro.accounts SET email = 'x@example.test'$q$, '42501');
SELECT pg_temp.expect('D8-04 jobs no actualiza sesiones', $q$UPDATE nukyro.sessions SET last_activity_at = now()$q$, '42501');
RESET ROLE;

SET ROLE nukyro_analytics;
SELECT pg_temp.expect('D3-16 analítica no lee session_facts', $q$SELECT count(*) FROM nukyro.session_facts$q$, '42501');
SELECT pg_temp.expect('D3-17 analítica no lee decision_facts', $q$SELECT count(*) FROM nukyro.decision_facts$q$, '42501');
SELECT pg_temp.expect('D3-18 analítica no lee topic_facts', $q$SELECT count(*) FROM nukyro.topic_facts$q$, '42501');
SELECT pg_temp.expect('D3-19 analítica no lee las encuestas', $q$SELECT count(*) FROM nukyro.survey_responses$q$, '42501');
RESET ROLE;

SET ROLE nukyro_admin;
SELECT pg_temp.expect('D3-20 admin no lee session_facts', $q$SELECT count(*) FROM nukyro.session_facts$q$, '42501');
SELECT pg_temp.expect('D3-21 admin no lee topic_facts', $q$SELECT count(*) FROM nukyro.topic_facts$q$, '42501');
RESET ROLE;

-- Funciones: SECURITY DEFINER del owner, search_path fijo, sin PUBLIC, grants exactos
SELECT pg_temp.chk('D8-05 hay al menos 7 funciones SECURITY DEFINER, todas del owner con search_path fijo',
 $q$SELECT (SELECT count(*) FROM pg_proc WHERE pronamespace = 'nukyro'::regnamespace AND prosecdef) >= 7
        AND NOT EXISTS (SELECT 1 FROM pg_proc p WHERE p.pronamespace = 'nukyro'::regnamespace AND p.prosecdef
                           AND (p.proowner <> 'nukyro_owner'::regrole
                                OR NOT coalesce(p.proconfig, '{}') @> ARRAY['search_path=pg_catalog, nukyro, pg_temp']))$q$);
SELECT pg_temp.chk('D8-06 ninguna función SECURITY DEFINER es ejecutable por PUBLIC',
 $q$SELECT (SELECT count(*) FROM pg_proc WHERE pronamespace = 'nukyro'::regnamespace AND prosecdef) >= 7
        AND NOT EXISTS (SELECT 1 FROM pg_proc p, aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
                         WHERE p.pronamespace = 'nukyro'::regnamespace AND p.prosecdef
                           AND a.grantee = 0 AND a.privilege_type = 'EXECUTE')$q$);
SELECT pg_temp.chk('D8-07 grants de ejecución exactos por rol',
 $q$SELECT has_function_privilege('nukyro_api',       'nukyro.erase_anonymous_participant(uuid)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_admin',     'nukyro.erase_anonymous_participant(uuid)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_jobs',      'nukyro.erase_anonymous_participant(uuid)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_analytics', 'nukyro.erase_anonymous_participant(uuid)', 'EXECUTE')
        AND has_function_privilege('nukyro_api',   'nukyro.block_account(uuid, text, timestamptz)', 'EXECUTE')
        AND has_function_privilege('nukyro_admin', 'nukyro.block_account(uuid, text, timestamptz)', 'EXECUTE')
        AND has_function_privilege('nukyro_jobs',  'nukyro.block_account(uuid, text, timestamptz)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_analytics', 'nukyro.block_account(uuid, text, timestamptz)', 'EXECUTE')
        AND has_function_privilege('nukyro_jobs', 'nukyro.expire_anonymous_participants(timestamptz)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_api',   'nukyro.expire_anonymous_participants(timestamptz)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_admin', 'nukyro.expire_anonymous_participants(timestamptz)', 'EXECUTE')
        AND has_function_privilege('nukyro_jobs', 'nukyro.purge_blocked_accounts(timestamptz)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_api',   'nukyro.purge_blocked_accounts(timestamptz)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_admin', 'nukyro.purge_blocked_accounts(timestamptz)', 'EXECUTE')
        AND has_function_privilege('nukyro_analytics', 'nukyro.report_session_summary(uuid)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_api',  'nukyro.report_session_summary(uuid)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_jobs', 'nukyro.report_session_summary(uuid)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_admin','nukyro.report_session_summary(uuid)', 'EXECUTE')$q$);
SELECT pg_temp.chk('D8-08 archive_participant y rewrite_facts son internas: ningún rol las ejecuta',
 $q$SELECT NOT has_function_privilege('nukyro_api',       'nukyro.archive_participant(uuid)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_admin',     'nukyro.archive_participant(uuid)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_jobs',      'nukyro.archive_participant(uuid)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_analytics', 'nukyro.archive_participant(uuid)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_api',       'nukyro.rewrite_facts()', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_jobs',      'nukyro.rewrite_facts()', 'EXECUTE')$q$);

SET ROLE nukyro_api;
SELECT pg_temp.expect('D8-09 api no ejecuta la purga', $q$SELECT nukyro.purge_blocked_accounts(now())$q$, '42501');
SELECT pg_temp.expect('D8-10 api no ejecuta la caducidad', $q$SELECT nukyro.expire_anonymous_participants(now())$q$, '42501');
SELECT pg_temp.expect('D8-11 api no ejecuta archive_participant',
 $q$SELECT nukyro.archive_participant(pg_temp.id('bb', 1))$q$, '42501');
SELECT pg_temp.expect('D8-12 api no ejecuta rewrite_facts', $q$SELECT nukyro.rewrite_facts()$q$, '42501');
SELECT pg_temp.expect('D8-13 api no ejecuta el reporte', $q$SELECT * FROM nukyro.report_session_summary(pg_temp.id('00', 0))$q$, '42501');
RESET ROLE;
SET ROLE nukyro_admin;
SELECT pg_temp.expect('D8-14 admin no ejecuta la caducidad', $q$SELECT nukyro.expire_anonymous_participants(now())$q$, '42501');
SELECT pg_temp.expect('D8-15 admin no borra participantes anónimos',
 $q$SELECT nukyro.erase_anonymous_participant(pg_temp.id('bb', 1))$q$, '42501');
RESET ROLE;
SET ROLE nukyro_analytics;
SELECT pg_temp.expect('D8-16 analítica no ejecuta el borrado anónimo',
 $q$SELECT nukyro.erase_anonymous_participant(pg_temp.id('bb', 1))$q$, '42501');
SELECT pg_temp.expect('D8-17 analítica no bloquea cuentas',
 $q$SELECT nukyro.block_account(pg_temp.id('ac', 1), 'user_request', now())$q$, '42501');
RESET ROLE;

-- =====================================================================
-- B · Archivo, reescritura y xmin (defecto 2)
-- Participantes y sesiones se crean en transacciones distintas de las del archivo.
-- =====================================================================
SELECT pg_temp.mk_anon(101);  SELECT pg_temp.mk_rich_session(201, 101);          -- sesión completa
SELECT pg_temp.mk_anon(102);  SELECT pg_temp.mk_session(202, 102);               -- se quedó en D01
SELECT pg_temp.mk_anon(103);  SELECT pg_temp.mk_session(203, 103);               -- sigue vivo
SELECT pg_temp.mk_anon(104);  SELECT pg_temp.mk_rich_session(204, 104);          -- se opone
UPDATE participants SET exclude_from_stats = true WHERE id = pg_temp.id('bb', 104);

SET ROLE nukyro_api;
SELECT pg_temp.allow('D2-10 api borra a un anónimo (archiva sus hechos)',
 $q$SELECT nukyro.erase_anonymous_participant(pg_temp.id('bb', 101))$q$);
RESET ROLE;
SELECT pg_temp.chk('D2-11 el participante y su sesión ya no existen; el vivo sigue',
 $q$SELECT NOT EXISTS (SELECT 1 FROM participants WHERE id = pg_temp.id('bb', 101))
        AND NOT EXISTS (SELECT 1 FROM sessions WHERE id = pg_temp.id('cc', 201))
        AND EXISTS (SELECT 1 FROM participants WHERE id = pg_temp.id('bb', 103))$q$);
SELECT pg_temp.chk('D2-12 un solo registro de sesión, con los hechos de la sesión completa',
 $q$SELECT (SELECT count(*) FROM session_facts) = 1
        AND EXISTS (SELECT 1 FROM session_facts
                     WHERE scenario_version_id = '00000000-0000-0000-0000-000000000011'
                       AND week_start = date '2026-11-30'        -- semana en UTC, no la local (domingo 29)
                       AND is_first_session
                       AND pretest_score = 100 AND posttest_score IS NULL
                       AND transfer_correct IS NULL AND transfer_total IS NULL
                       AND causal_correct = 0 AND causal_total = 1
                       AND justification_correct = 1 AND justification_total = 1
                       AND outcome_reached AND outcome_key = 'OUT1' AND stopped_at_key IS NULL
                       AND evaluations_completed AND duration_bucket_min = 10)$q$);
SELECT pg_temp.chk('D2-13 hechos de decisión y por tema',
 $q$SELECT (SELECT count(*) FROM decision_facts) = 1
        AND EXISTS (SELECT 1 FROM decision_facts WHERE decision_key = 'D01' AND option_key = 'D01-A' AND is_first_session
                       AND week_start = date '2026-11-30')
        AND (SELECT count(*) FROM topic_facts) = 2
        AND EXISTS (SELECT 1 FROM topic_facts WHERE set_type = 'pretest' AND topic = 'privacidad' AND correct = 1 AND total = 1 AND is_first_session)
        AND EXISTS (SELECT 1 FROM topic_facts WHERE set_type = 'causal'  AND topic = 'privacidad' AND correct = 0 AND total = 1 AND is_first_session)$q$);
SELECT set_config('nukyro_t.x1', (SELECT xmin::text FROM session_facts LIMIT 1), false) AS "xmin tras el primer archivo";

SET ROLE nukyro_api;
SELECT pg_temp.allow('D2-14 segundo archivo', $q$SELECT nukyro.erase_anonymous_participant(pg_temp.id('bb', 102))$q$);
SELECT pg_temp.allow('D2-15 el opuesto se borra sin dejar copia', $q$SELECT nukyro.erase_anonymous_participant(pg_temp.id('bb', 104))$q$);
RESET ROLE;
SELECT pg_temp.chk('D2-16 la sesión interrumpida guarda la clave del nodo en que se quedó',
 $q$SELECT (SELECT count(*) FROM session_facts) = 2
        AND EXISTS (SELECT 1 FROM session_facts WHERE NOT outcome_reached AND outcome_key IS NULL AND stopped_at_key = 'D01'
                       AND NOT evaluations_completed AND pretest_score IS NULL AND duration_bucket_min = 0)$q$);
SELECT pg_temp.chk('D2-17 opuesto (exclude_from_stats): no deja copia de ninguna clase',
 $q$SELECT NOT EXISTS (SELECT 1 FROM participants WHERE id = pg_temp.id('bb', 104))
        AND (SELECT count(*) FROM session_facts) = 2 AND (SELECT count(*) FROM decision_facts) = 1
        AND (SELECT count(*) FROM topic_facts) = 2$q$);
SELECT pg_temp.chk('D2-18 hechos de dos archivos sucesivos comparten un xmin distinto del primero',
 $q$SELECT (SELECT count(DISTINCT x) FROM (SELECT xmin::text AS x FROM session_facts
                                           UNION ALL SELECT xmin::text FROM decision_facts
                                           UNION ALL SELECT xmin::text FROM topic_facts) u) = 1
        AND (SELECT xmin::text FROM session_facts LIMIT 1) <> current_setting('nukyro_t.x1')$q$);
SELECT pg_temp.chk('D2-19 ese xmin no es el de ningún participante vivo ni de sus sesiones',
 $q$SELECT NOT EXISTS (SELECT 1 FROM participants WHERE xmin::text = (SELECT xmin::text FROM session_facts LIMIT 1))
        AND NOT EXISTS (SELECT 1 FROM sessions WHERE xmin::text = (SELECT xmin::text FROM session_facts LIMIT 1))$q$);
SELECT pg_temp.chk('D2-20 los ids de hechos son UUID v4 en las tres tablas',
 $q$SELECT (SELECT count(*) FROM session_facts) > 0 AND (SELECT count(*) FROM decision_facts) > 0 AND (SELECT count(*) FROM topic_facts) > 0
        AND NOT EXISTS (SELECT 1 FROM (SELECT id FROM session_facts UNION ALL SELECT id FROM decision_facts UNION ALL SELECT id FROM topic_facts) f
                         WHERE substr(f.id::text, 15, 1) <> '4' OR substr(f.id::text, 20, 1) NOT IN ('8', '9', 'a', 'b'))$q$);

-- Participante con cuenta: no se borra con la función anónima
SELECT pg_temp.mk_account(304, 108);
SET ROLE nukyro_api;
SELECT pg_temp.expect('D8-18 erase_anonymous_participant rechaza a quien tiene cuenta',
 $q$SELECT nukyro.erase_anonymous_participant(pg_temp.id('bb', 108))$q$, '23514');
RESET ROLE;
SELECT pg_temp.chk('D8-19 el participante con cuenta sigue ahí',
 $q$SELECT EXISTS (SELECT 1 FROM participants WHERE id = pg_temp.id('bb', 108))$q$);

-- Caducidad: bloquea, revalida y archiva una vez
SELECT pg_temp.mk_anon(110); SELECT pg_temp.mk_session(210, 110, now() - interval '101 days');
SELECT pg_temp.mk_anon(111); SELECT pg_temp.mk_session(211, 111, now() - interval '101 days');
SELECT pg_temp.mk_anon(112); SELECT pg_temp.mk_session(212, 112);
UPDATE participants SET last_activity_at = now() - interval '100 days' WHERE id IN (pg_temp.id('bb', 110), pg_temp.id('bb', 111));
SELECT set_config('nukyro_t.n_sf', (SELECT count(*)::text FROM session_facts), false) AS "hechos antes de expirar";
SET ROLE nukyro_jobs;
SELECT pg_temp.chk('D8-20 expire_anonymous_participants devuelve el conteo y solo toca a los inactivos',
 $q$SELECT nukyro.expire_anonymous_participants(now() - interval '90 days') = 2$q$);
RESET ROLE;
SELECT pg_temp.chk('D8-21 los expirados dejaron su hecho; el activo sigue vivo y sin copia',
 $q$SELECT (SELECT count(*) FROM session_facts) = current_setting('nukyro_t.n_sf')::int + 2
        AND NOT EXISTS (SELECT 1 FROM participants WHERE id IN (pg_temp.id('bb', 110), pg_temp.id('bb', 111)))
        AND EXISTS (SELECT 1 FROM participants WHERE id = pg_temp.id('bb', 112))
        AND (SELECT facts_written_at IS NULL FROM sessions WHERE id = pg_temp.id('cc', 212))$q$);
SELECT pg_temp.chk('D2-21 tras la caducidad todos los hechos comparten un solo xmin',
 $q$SELECT (SELECT count(DISTINCT x) FROM (SELECT xmin::text AS x FROM session_facts
                                           UNION ALL SELECT xmin::text FROM decision_facts
                                           UNION ALL SELECT xmin::text FROM topic_facts) u) = 1$q$);

-- Bloqueo de cuentas: archiva (salvo opuesto o menor), es terminal, y la purga solo borra vencidas
SELECT pg_temp.mk_account(301, 105); SELECT pg_temp.mk_session(205, 105);      -- menor de edad
SELECT pg_temp.mk_account(302, 106); SELECT pg_temp.mk_rich_session(206, 106); -- cuenta normal
SELECT pg_temp.mk_account(303, 107); SELECT pg_temp.mk_rich_session(207, 107); -- cuenta con oposición
UPDATE participants SET exclude_from_stats = true WHERE id = pg_temp.id('bb', 107);
SELECT pg_temp.mk_account(305);                                                -- activa, sin participante
SELECT set_config('nukyro_t.n_sf', (SELECT count(*)::text FROM session_facts), false) AS "hechos antes de bloquear";

SET ROLE nukyro_admin;
SELECT pg_temp.chk('D8-22 block_account de un menor: bloquea y no deja copia',
 $q$SELECT nukyro.block_account(pg_temp.id('ac', 301), 'underage', now() + interval '10 days')$q$);
RESET ROLE;
SELECT pg_temp.chk('D8-23 menor: sin hechos nuevos y su sesión queda sin marcar',
 $q$SELECT (SELECT count(*) FROM session_facts) = current_setting('nukyro_t.n_sf')::int
        AND (SELECT status = 'blocked' AND block_reason = 'underage' FROM accounts WHERE id = pg_temp.id('ac', 301))
        AND (SELECT facts_written_at IS NULL FROM sessions WHERE id = pg_temp.id('cc', 205))$q$);
SET ROLE nukyro_jobs;
SELECT pg_temp.chk('D8-24 block_account de una cuenta normal archiva y reescribe',
 $q$SELECT nukyro.block_account(pg_temp.id('ac', 302), 'user_request', now() + interval '10 days')$q$);
SELECT pg_temp.expect('D12-01 rechaza una purga inmediata al bloquear (A-06)',
 $q$SELECT nukyro.block_account(pg_temp.id('ac', 303), 'user_request', now())$q$, '23514');
SELECT pg_temp.expect('D12-02 rechaza un plazo un microsegundo menor a una hora (A-06)',
 $q$SELECT nukyro.block_account(pg_temp.id('ac', 303), 'user_request', now() + interval '1 hour -1 microsecond')$q$, '23514');
SELECT pg_temp.chk('D8-25 block_account de una cuenta con oposición bloquea sin copia',
 $q$SELECT nukyro.block_account(pg_temp.id('ac', 303), 'user_request', now() + interval '1 hour')$q$);
RESET ROLE;
SELECT pg_temp.chk('D12-03 se acepta exactamente una hora (A-06)',
 $q$SELECT deletion_due_at = blocked_at + interval '1 hour' FROM accounts WHERE id = pg_temp.id('ac', 303)$q$);
SELECT pg_temp.chk('D8-26 normal: un hecho más y sesión marcada; opuesta: ninguno',
 $q$SELECT (SELECT count(*) FROM session_facts) = current_setting('nukyro_t.n_sf')::int + 1
        AND (SELECT facts_written_at IS NOT NULL FROM sessions WHERE id = pg_temp.id('cc', 206))
        AND (SELECT facts_written_at IS NULL FROM sessions WHERE id = pg_temp.id('cc', 207))$q$);
SELECT pg_temp.chk('D8-27 tras bloquear, todos los hechos comparten un solo xmin',
 $q$SELECT (SELECT count(DISTINCT x) FROM (SELECT xmin::text AS x FROM session_facts
                                           UNION ALL SELECT xmin::text FROM decision_facts
                                           UNION ALL SELECT xmin::text FROM topic_facts) u) = 1$q$);
SET ROLE nukyro_jobs;
SELECT pg_temp.chk('D8-28 el bloqueo es terminal: repetirlo no hace nada',
 $q$SELECT NOT nukyro.block_account(pg_temp.id('ac', 302), 'terms_breach', now() + interval '99 days')$q$);
RESET ROLE;
SELECT pg_temp.chk('D8-29 y no cambia el motivo ni la fecha ni agrega hechos',
 $q$SELECT (SELECT block_reason = 'user_request' FROM accounts WHERE id = pg_temp.id('ac', 302))
        AND (SELECT count(*) FROM session_facts) = current_setting('nukyro_t.n_sf')::int + 1$q$);

-- Cuenta bloqueada: no se modifica ni se reactiva; cognito_sub inmutable
SELECT pg_temp.expect('D7-01 cuenta bloqueada no se modifica (superusuario)',
 $q$UPDATE accounts SET email = 'otro@example.test' WHERE id = pg_temp.id('ac', 302)$q$, '23514');
SELECT pg_temp.expect('D7-02 cuenta bloqueada no se reactiva',
 $q$UPDATE accounts SET status = 'active', blocked_at = NULL, block_reason = NULL, deletion_due_at = NULL
    WHERE id = pg_temp.id('ac', 302)$q$, '23514');
SELECT pg_temp.expect('D7-03 cognito_sub es inmutable',
 $q$UPDATE accounts SET cognito_sub = 'otro-sub' WHERE id = pg_temp.id('ac', 305)$q$, '23514');
SET ROLE nukyro_api;
SELECT pg_temp.expect('D7-04 api no modifica una cuenta bloqueada',
 $q$UPDATE nukyro.accounts SET nickname = 'x' WHERE id = pg_temp.id('ac', 302)$q$, '23514');
RESET ROLE;
SET ROLE nukyro_admin;
SELECT pg_temp.expect('D7-05 admin no modifica una cuenta bloqueada',
 $q$UPDATE nukyro.accounts SET nickname = 'x' WHERE id = pg_temp.id('ac', 302)$q$, '23514');
RESET ROLE;
SELECT pg_temp.expect('D9-01 una cuenta bloqueada no inicia sesiones nuevas',
 $q$INSERT INTO sessions (participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session)
    VALUES (pg_temp.id('bb', 106), '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000042', true, false)$q$, '23514');

-- Purga: solo las vencidas (D-20)
SET ROLE nukyro_jobs;
SELECT pg_temp.chk('D12-04 antes del plazo no se purga ninguna cuenta (A-06)',
 $q$SELECT nukyro.purge_blocked_accounts(now()) = 0$q$);
SELECT pg_temp.chk('D8-30 purge_blocked_accounts borra solo la vencida',
 $q$SELECT nukyro.purge_blocked_accounts(now() + interval '1 hour') = 1$q$);
RESET ROLE;
SELECT pg_temp.chk('D8-31 la vencida y su cascada desaparecen; las no vencidas y la activa siguen',
 $q$SELECT NOT EXISTS (SELECT 1 FROM accounts WHERE id = pg_temp.id('ac', 303))
        AND NOT EXISTS (SELECT 1 FROM participants WHERE id = pg_temp.id('bb', 107))
        AND NOT EXISTS (SELECT 1 FROM sessions WHERE id = pg_temp.id('cc', 207))
        AND EXISTS (SELECT 1 FROM accounts WHERE id = pg_temp.id('ac', 301))
        AND EXISTS (SELECT 1 FROM accounts WHERE id = pg_temp.id('ac', 302))
        AND EXISTS (SELECT 1 FROM accounts WHERE id = pg_temp.id('ac', 305))$q$);
SET ROLE nukyro_jobs;
SELECT pg_temp.chk('D8-32 pasado el plazo, la purga borra las otras dos; los hechos de la cuenta normal sobreviven',
 $q$SELECT nukyro.purge_blocked_accounts(now() + interval '11 days') = 2$q$);
RESET ROLE;
SELECT pg_temp.chk('D8-33 sin rastro de las cuentas purgadas y con los hechos intactos',
 $q$SELECT NOT EXISTS (SELECT 1 FROM sessions WHERE id IN (pg_temp.id('cc', 205), pg_temp.id('cc', 206)))
        AND (SELECT count(*) FROM session_facts) = current_setting('nukyro_t.n_sf')::int + 1$q$);

-- Reporte agregado con umbral de 10 (sobre la versión 2; sin sesiones de verdad)
SELECT pg_temp.fx($q$
 INSERT INTO session_facts (scenario_version_id, week_start, is_first_session, pretest_score, posttest_score, outcome_reached, evaluations_completed)
 SELECT '00000000-0000-0000-0000-000000000012', date '2026-11-30', true, 40, 80, true, true FROM generate_series(1, 9);
 INSERT INTO session_facts (scenario_version_id, week_start, is_first_session, pretest_score, posttest_score, outcome_reached, evaluations_completed)
 SELECT '00000000-0000-0000-0000-000000000012', date '2026-11-30', false, 0, 0, false, false FROM generate_series(1, 3)$q$);
SET ROLE nukyro_analytics;
SELECT pg_temp.chk('D8-34 con 9 primeras sesiones: suprimido y sin valores (las no primeras no cuentan)',
 $q$SELECT suppressed AND first_sessions IS NULL AND outcome_reached_count IS NULL
           AND avg_pretest_score IS NULL AND avg_posttest_score IS NULL
      FROM nukyro.report_session_summary('00000000-0000-0000-0000-000000000012')$q$);
RESET ROLE;
SELECT pg_temp.fx($q$
 INSERT INTO session_facts (scenario_version_id, week_start, is_first_session, pretest_score, posttest_score, outcome_reached, evaluations_completed)
 VALUES ('00000000-0000-0000-0000-000000000012', date '2026-11-30', true, 100, 80, false, true)$q$);
SET ROLE nukyro_analytics;
SELECT pg_temp.chk('D8-35 con 10: muestra agregados de las primeras sesiones',
 $q$SELECT NOT suppressed AND first_sessions = 10 AND outcome_reached_count = 9
           AND avg_pretest_score = 46 AND avg_posttest_score = 80
      FROM nukyro.report_session_summary('00000000-0000-0000-0000-000000000012')$q$);
SELECT pg_temp.chk('D8-36 una versión sin hechos devuelve suprimido',
 $q$SELECT suppressed AND first_sessions IS NULL
      FROM nukyro.report_session_summary('00000000-0000-0000-0000-0000000000ff')$q$);
RESET ROLE;

-- =====================================================================
-- C · Defecto 4: FK de administradores en RESTRICT
-- =====================================================================
SELECT pg_temp.chk('D4-01 las FK created_by y published_by son RESTRICT',
 $q$SELECT (SELECT count(*) FROM pg_constraint c
             WHERE c.conrelid = 'nukyro.scenario_versions'::regclass AND c.contype = 'f'
               AND c.confrelid = 'nukyro.admin_users'::regclass AND c.confdeltype = 'r') = 2$q$);
SELECT pg_temp.expect('D4-02 no se borra al administrador que publicó',
 $q$DELETE FROM admin_users WHERE id = '00000000-0000-0000-0000-00000000ad01'$q$, '23503');
INSERT INTO admin_users (id, cognito_sub, email, display_name) VALUES (pg_temp.id('ad', 2), 'cognito-admin-2', 'a2@example.test', 'Admin 2');
INSERT INTO scenarios (id, key, title) VALUES (pg_temp.id('50', 4), 'D4', 'Escenario del defecto 4');
INSERT INTO scenario_versions (id, scenario_id, version_number, title, created_by)
VALUES (pg_temp.id('51', 4), pg_temp.id('50', 4), 1, 'borrador de ad02', pg_temp.id('ad', 2));
SELECT pg_temp.expect('D4-03 tampoco al que creó un borrador',
 $q$DELETE FROM admin_users WHERE id = pg_temp.id('ad', 2)$q$, '23503');
SET ROLE nukyro_admin;
SELECT pg_temp.expect('D4-04 el rol admin no tiene DELETE sobre admin_users',
 $q$DELETE FROM nukyro.admin_users WHERE id = pg_temp.id('ad', 2)$q$, '42501');
RESET ROLE;

-- =====================================================================
-- D · Defecto 5: ciclo de vida de la versión
-- =====================================================================
INSERT INTO scenarios (id, key, title) VALUES (pg_temp.id('50', 5), 'D5', 'Escenario del defecto 5'), (pg_temp.id('50', 6), 'D5b', 'Otro');
SELECT pg_temp.expect('D5-01 no se inserta una versión publicada',
 $q$INSERT INTO scenario_versions (scenario_id, version_number, title, status, published_at)
    VALUES (pg_temp.id('50', 5), 1, 'ya publicada', 'published', now())$q$, '23514');
SELECT pg_temp.expect('D5-02 no se inserta una versión retirada',
 $q$INSERT INTO scenario_versions (scenario_id, version_number, title, status, published_at, retired_at)
    VALUES (pg_temp.id('50', 5), 1, 'ya retirada', 'retired', now(), now())$q$, '23514');
SELECT pg_temp.expect('D5-03 un borrador no nace con published_by',
 $q$INSERT INTO scenario_versions (scenario_id, version_number, title, published_by)
    VALUES (pg_temp.id('50', 5), 1, 'borrador raro', '00000000-0000-0000-0000-00000000ad01')$q$, '23514');
SELECT pg_temp.allow('D5-04 se inserta un borrador',
 $q$INSERT INTO scenario_versions (id, scenario_id, version_number, title) VALUES (pg_temp.id('51', 5), pg_temp.id('50', 5), 1, 'borrador')$q$);
SELECT pg_temp.expect('D5-05 un borrador no se retira sin publicarse',
 $q$UPDATE scenario_versions SET status = 'retired', published_at = now(), retired_at = now() WHERE id = pg_temp.id('51', 5)$q$, '23514');
SELECT pg_temp.expect('D5-06 un borrador no cambia de escenario',
 $q$UPDATE scenario_versions SET scenario_id = pg_temp.id('50', 6) WHERE id = pg_temp.id('51', 5)$q$, '23514');
SELECT pg_temp.allow('D5-07 un borrador se edita',
 $q$UPDATE scenario_versions SET title = 'borrador editado' WHERE id = pg_temp.id('51', 5)$q$);
SELECT pg_temp.allow('D5-08 un borrador se publica',
 $q$UPDATE scenario_versions SET status = 'published', published_at = now(), published_by = '00000000-0000-0000-0000-00000000ad01'
    WHERE id = pg_temp.id('51', 5)$q$);
SELECT pg_temp.expect('D5-09 al retirar no se puede alterar published_by',
 $q$UPDATE scenario_versions SET status = 'retired', retired_at = now(), published_by = pg_temp.id('ad', 2) WHERE id = pg_temp.id('51', 5)$q$, '23514');
SELECT pg_temp.expect('D5-10 al retirar no se puede alterar created_at',
 $q$UPDATE scenario_versions SET status = 'retired', retired_at = now(), created_at = now() - interval '1 year' WHERE id = pg_temp.id('51', 5)$q$, '23514');
SELECT pg_temp.expect('D5-11 al retirar no se puede alterar el escenario',
 $q$UPDATE scenario_versions SET status = 'retired', retired_at = now(), scenario_id = pg_temp.id('50', 6) WHERE id = pg_temp.id('51', 5)$q$, '23514');
SELECT pg_temp.expect('D5-12 una versión publicada no se edita sin retirarla',
 $q$UPDATE scenario_versions SET title = 'cambio' WHERE id = pg_temp.id('51', 5)$q$, '23514');
SELECT pg_temp.allow('D5-13 retirar cambiando solo status y retired_at',
 $q$UPDATE scenario_versions SET status = 'retired', retired_at = now() WHERE id = pg_temp.id('51', 5)$q$);
SELECT pg_temp.expect('D5-14 una versión retirada no cambia',
 $q$UPDATE scenario_versions SET title = 'cambio' WHERE id = pg_temp.id('51', 5)$q$, '23514');
SELECT pg_temp.expect('D5-15 una versión retirada no vuelve a publicarse',
 $q$UPDATE scenario_versions SET status = 'published', retired_at = NULL WHERE id = pg_temp.id('51', 5)$q$, '23514');
SELECT pg_temp.expect('D5-16 ni siquiera una actualización vacía de una retirada',
 $q$UPDATE scenario_versions SET title = title WHERE id = pg_temp.id('51', 5)$q$, '23514');

-- Defecto 6 (parte secuencial; la carrera editar/publicar está en pruebas-concurrencia.sh)
SELECT pg_temp.expect('D6-01 contenido publicado no se mueve a un borrador',
 $q$UPDATE nodes SET version_id = '00000000-0000-0000-0000-000000000012' WHERE id = '00000000-0000-0000-0000-000000000042'$q$, '23514');
SELECT pg_temp.allow('D6-02 borrar un borrador con contenido sigue funcionando en cascada',
 $q$INSERT INTO scenario_versions (id, scenario_id, version_number, title) VALUES (pg_temp.id('51', 7), pg_temp.id('50', 6), 1, 'borrador con contenido');
    INSERT INTO nodes (id, version_id, key, node_type, title, body) VALUES (pg_temp.id('52', 7), pg_temp.id('51', 7), 'N', 'info', 't', 'b');
    DELETE FROM scenario_versions WHERE id = pg_temp.id('51', 7)$q$);
SELECT pg_temp.chk('D6-03 la cascada borró el contenido',
 $q$SELECT NOT EXISTS (SELECT 1 FROM nodes WHERE version_id = pg_temp.id('51', 7))$q$);

-- =====================================================================
-- E · Defecto 7: permisos por columna y campos inmutables
-- =====================================================================
SELECT pg_temp.mk_account(320, 120);                      -- cuenta con participante
SELECT pg_temp.mk_anon(121); SELECT pg_temp.mk_account(321);   -- anónimo y cuenta para vincular
SELECT pg_temp.mk_anon(122);
SELECT pg_temp.mk_account(322, 123, true);                -- cuenta y secreto a la vez
SELECT pg_temp.mk_anon(125);
SELECT pg_temp.mk_session(220, 120);
INSERT INTO session_variables (session_id, scenario_version_id, variable_id, value)
VALUES (pg_temp.id('cc', 220), '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000031', 3);
INSERT INTO assessment_attempts (id, session_id, scenario_version_id, question_set_id)
VALUES (pg_temp.id('a1', 220), pg_temp.id('cc', 220), '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000091');
INSERT INTO assessment_answers (attempt_id, question_set_id, question_id, option_id)
VALUES (pg_temp.id('a1', 220), '00000000-0000-0000-0000-000000000091', '00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000b2');

SET ROLE nukyro_api;
-- cuentas
SELECT pg_temp.allow('D7-10 api actualiza sus columnas permitidas de la cuenta',
 $q$UPDATE nukyro.accounts SET email = 'n@example.test', nickname = 'nuevo', newsletter_opt_in = true,
        surveys_opt_in = true, last_login_at = now() WHERE id = pg_temp.id('ac', 320)$q$);
SELECT pg_temp.expect('D7-11 api no cambia el estado de la cuenta', $q$UPDATE nukyro.accounts SET status = 'blocked' WHERE id = pg_temp.id('ac', 320)$q$, '42501');
SELECT pg_temp.expect('D7-12 api no cambia cognito_sub', $q$UPDATE nukyro.accounts SET cognito_sub = 'otro' WHERE id = pg_temp.id('ac', 320)$q$, '42501');
SELECT pg_temp.expect('D7-13 api no fija la fecha de borrado', $q$UPDATE nukyro.accounts SET deletion_due_at = now() WHERE id = pg_temp.id('ac', 320)$q$, '42501');
SELECT pg_temp.expect('D7-14 api no crea una cuenta ya bloqueada',
 $q$INSERT INTO nukyro.accounts (cognito_sub, email, nickname, status, blocked_at, block_reason, deletion_due_at)
    VALUES ('sub-x', 'x@example.test', 'x', 'blocked', now(), 'underage', now())$q$, '42501');
SELECT pg_temp.allow('D7-15 api crea una cuenta activa',
 $q$INSERT INTO nukyro.accounts (cognito_sub, email, nickname) VALUES ('sub-nueva', 'nueva@example.test', 'nueva')$q$);
SELECT pg_temp.expect('D7-16 api no borra cuentas', $q$DELETE FROM nukyro.accounts WHERE id = pg_temp.id('ac', 320)$q$, '42501');
-- participantes
SELECT pg_temp.expect('D7-20 api no cambia created_at del participante', $q$UPDATE nukyro.participants SET created_at = now() WHERE id = pg_temp.id('bb', 122)$q$, '42501');
SELECT pg_temp.allow('D7-21 api vincula al anónimo con su cuenta y suelta el secreto',
 $q$UPDATE nukyro.participants SET account_id = pg_temp.id('ac', 321), secret_hash = NULL, last_activity_at = now() WHERE id = pg_temp.id('bb', 121)$q$);
SELECT pg_temp.expect('D7-22 account_id es inmutable una vez asignado',
 $q$UPDATE nukyro.participants SET account_id = pg_temp.id('ac', 320) WHERE id = pg_temp.id('bb', 121)$q$, '23514');
SELECT pg_temp.expect('D7-23 secret_hash no pasa de NULL a un valor',
 $q$UPDATE nukyro.participants SET secret_hash = sha256('nuevo') WHERE id = pg_temp.id('bb', 121)$q$, '23514');
SELECT pg_temp.expect('D7-24 secret_hash no cambia a otro valor',
 $q$UPDATE nukyro.participants SET secret_hash = sha256('otro') WHERE id = pg_temp.id('bb', 122)$q$, '23514');
SELECT pg_temp.allow('D7-25 secret_hash sí puede pasar a NULL (si hay cuenta)',
 $q$UPDATE nukyro.participants SET secret_hash = NULL WHERE id = pg_temp.id('bb', 123)$q$);
SELECT pg_temp.allow('D7-26 secret_hash puede quedarse igual',
 $q$UPDATE nukyro.participants SET secret_hash = secret_hash, exclude_from_stats = true WHERE id = pg_temp.id('bb', 122)$q$);
SELECT pg_temp.expect('D7-27 api no borra participantes', $q$DELETE FROM nukyro.participants WHERE id = pg_temp.id('bb', 122)$q$, '42501');
-- sesiones
SELECT pg_temp.expect('D7-30 api no cambia la versión de la sesión', $q$UPDATE nukyro.sessions SET scenario_version_id = '00000000-0000-0000-0000-000000000012' WHERE id = pg_temp.id('cc', 220)$q$, '42501');
SELECT pg_temp.expect('D7-31 api no cambia el participante de la sesión', $q$UPDATE nukyro.sessions SET participant_id = pg_temp.id('bb', 122) WHERE id = pg_temp.id('cc', 220)$q$, '42501');
SELECT pg_temp.expect('D7-32 api no cambia started_at', $q$UPDATE nukyro.sessions SET started_at = now() WHERE id = pg_temp.id('cc', 220)$q$, '42501');
SELECT pg_temp.expect('D7-33 api no cambia has_prior_session', $q$UPDATE nukyro.sessions SET has_prior_session = true WHERE id = pg_temp.id('cc', 220)$q$, '42501');
SELECT pg_temp.expect('D7-34 api no cambia self_reported_first', $q$UPDATE nukyro.sessions SET self_reported_first = false WHERE id = pg_temp.id('cc', 220)$q$, '42501');
SELECT pg_temp.expect('D7-35 api no toca facts_written_at', $q$UPDATE nukyro.sessions SET facts_written_at = now() WHERE id = pg_temp.id('cc', 220)$q$, '42501');
SELECT pg_temp.expect('D7-36 api no borra sesiones', $q$DELETE FROM nukyro.sessions WHERE id = pg_temp.id('cc', 220)$q$, '42501');
SELECT pg_temp.expect('D7-37 api no inserta started_at ni has_prior_session',
 $q$INSERT INTO nukyro.sessions (participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session)
    VALUES (pg_temp.id('bb', 125), '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000041', true, false)$q$, '42501');
SELECT pg_temp.expect('D7-38 api no inserta facts_written_at',
 $q$INSERT INTO nukyro.sessions (participant_id, scenario_version_id, current_node_id, self_reported_first, facts_written_at)
    VALUES (pg_temp.id('bb', 125), '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000041', true, now())$q$, '42501');
SELECT pg_temp.allow('D7-39 api avanza la sesión con las columnas permitidas',
 $q$UPDATE nukyro.sessions SET current_node_id = '00000000-0000-0000-0000-000000000044', pretest_completed_at = now(),
        outcome_node_id = '00000000-0000-0000-0000-000000000044', outcome_reached_at = now(), completed_at = now(),
        last_activity_at = now(), survey_answered = true WHERE id = pg_temp.id('cc', 220)$q$);
SELECT pg_temp.allow('D7-40 api inicia una sesión con las columnas permitidas (sin has_prior_session)',
 $q$INSERT INTO nukyro.sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first)
    VALUES (pg_temp.id('cc', 225), pg_temp.id('bb', 125), '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000041', true)$q$);
SELECT pg_temp.chk('D9-02 la base calcula la primera sesión de quien la inicia',
 $q$SELECT is_first_session AND NOT has_prior_session FROM nukyro.sessions WHERE id = pg_temp.id('cc', 225)$q$);
-- decisiones y demás tablas de la simulación: solo SELECT e INSERT
SELECT pg_temp.allow('D7-41 api registra una decisión, su paso y una razón',
 $q$INSERT INTO nukyro.session_steps (session_id, scenario_version_id, node_id, seq)
        VALUES (pg_temp.id('cc', 225), '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000041', 1);
    INSERT INTO nukyro.session_decisions (id, session_id, scenario_version_id, node_id, option_id)
        VALUES (pg_temp.id('dd', 225), pg_temp.id('cc', 225), '00000000-0000-0000-0000-000000000011',
                '00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000051');
    INSERT INTO nukyro.session_decision_reasons (session_decision_id, node_id, reason_id)
        VALUES (pg_temp.id('dd', 225), '00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000061')$q$);
SELECT pg_temp.expect('D7-42 api no cambia una decisión', $q$UPDATE nukyro.session_decisions SET option_id = '00000000-0000-0000-0000-000000000052'$q$, '42501');
SELECT pg_temp.expect('D7-43 api no borra una decisión', $q$DELETE FROM nukyro.session_decisions$q$, '42501');
SELECT pg_temp.expect('D7-44 api no cambia un paso', $q$UPDATE nukyro.session_steps SET seq = 2$q$, '42501');
SELECT pg_temp.expect('D7-45 api no cambia las razones', $q$UPDATE nukyro.session_decision_reasons SET reason_id = reason_id$q$, '42501');
SELECT pg_temp.expect('D7-46 api no cambia efectos', $q$UPDATE nukyro.session_effects SET new_value = 0$q$, '42501');
SELECT pg_temp.expect('D7-47 api no cambia eventos', $q$UPDATE nukyro.session_events SET rule_id = rule_id$q$, '42501');
SELECT pg_temp.expect('D7-48 api no cambia causas', $q$UPDATE nukyro.session_event_causes SET session_id = session_id$q$, '42501');
SELECT pg_temp.expect('D7-49 api no cambia aceptaciones', $q$UPDATE nukyro.document_acceptances SET document_version = '9'$q$, '42501');
-- variables, intentos y respuestas
SELECT pg_temp.allow('D7-50 api actualiza el valor de una variable',
 $q$UPDATE nukyro.session_variables SET value = 2, updated_at = now() WHERE session_id = pg_temp.id('cc', 220)$q$);
SELECT pg_temp.expect('D7-51 api no cambia la variable de la fila',
 $q$UPDATE nukyro.session_variables SET variable_id = '00000000-0000-0000-0000-000000000032' WHERE session_id = pg_temp.id('cc', 220)$q$, '42501');
SELECT pg_temp.allow('D7-52 api cambia una respuesta antes de enviar el intento',
 $q$UPDATE nukyro.assessment_answers SET option_id = '00000000-0000-0000-0000-0000000000b1', answered_at = now() WHERE attempt_id = pg_temp.id('a1', 220)$q$);
SELECT pg_temp.expect('D7-53 api no cambia la pregunta de una respuesta',
 $q$UPDATE nukyro.assessment_answers SET question_id = question_id WHERE attempt_id = pg_temp.id('a1', 220)$q$, '42501');
SELECT pg_temp.allow('D7-54 api envía el intento',
 $q$UPDATE nukyro.assessment_attempts SET submitted_at = now(), answered_count = 1, correct_count = 1, score = 100 WHERE id = pg_temp.id('a1', 220)$q$);
SELECT pg_temp.expect('D7-55 tras el envío no se cambian las respuestas',
 $q$UPDATE nukyro.assessment_answers SET option_id = '00000000-0000-0000-0000-0000000000b2' WHERE attempt_id = pg_temp.id('a1', 220)$q$, '23514');
SELECT pg_temp.expect('D7-55b un intento enviado no se reabre',
 $q$UPDATE nukyro.assessment_attempts SET submitted_at = NULL, score = NULL WHERE id = pg_temp.id('a1', 220)$q$, '23514');
SELECT pg_temp.allow('D7-55c api crea y envía otro intento sin respuestas',
 $q$WITH i AS (INSERT INTO nukyro.assessment_attempts (id, session_id, scenario_version_id, question_set_id, submitted_at)
    VALUES (pg_temp.id('a9', 220), pg_temp.id('cc', 220), '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000092', now()) RETURNING 1) SELECT 1 FROM i$q$);
SELECT pg_temp.expect('D7-55d tras el envío no se agregan respuestas',
 $q$INSERT INTO nukyro.assessment_answers (attempt_id, question_set_id, question_id, option_id)
    VALUES (pg_temp.id('a9', 220), '00000000-0000-0000-0000-000000000092', '00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-0000000000b4')$q$, '23514');
SELECT pg_temp.expect('D7-56 api no cambia el conjunto de preguntas del intento',
 $q$UPDATE nukyro.assessment_attempts SET question_set_id = question_set_id WHERE id = pg_temp.id('a1', 220)$q$, '42501');
SELECT pg_temp.expect('D7-57 api no cambia la versión del intento',
 $q$UPDATE nukyro.assessment_attempts SET scenario_version_id = scenario_version_id WHERE id = pg_temp.id('a1', 220)$q$, '42501');
RESET ROLE;
SELECT pg_temp.chk('D7-58 api no tiene UPDATE de tabla ni DELETE en la simulación (solo SELECT e INSERT donde se indica)',
 $q$SELECT NOT EXISTS (
      SELECT 1 FROM unnest(ARRAY['document_acceptances', 'session_steps', 'session_decisions', 'session_decision_reasons',
                                 'session_effects', 'session_events', 'session_event_causes']) t(tabla),
                    unnest(ARRAY['UPDATE', 'DELETE']) p(priv)
       WHERE has_table_privilege('nukyro_api', 'nukyro.' || t.tabla, p.priv))
      AND NOT EXISTS (
      SELECT 1 FROM unnest(ARRAY['accounts', 'participants', 'sessions', 'session_variables',
                                 'assessment_attempts', 'assessment_answers']) t(tabla)
       WHERE has_table_privilege('nukyro_api', 'nukyro.' || t.tabla, 'UPDATE') OR has_table_privilege('nukyro_api', 'nukyro.' || t.tabla, 'DELETE'))
      AND (SELECT count(*) FROM unnest(ARRAY['document_acceptances', 'session_steps', 'session_decisions', 'session_decision_reasons',
                                 'session_effects', 'session_events', 'session_event_causes']) t(tabla)
            WHERE has_table_privilege('nukyro_api', 'nukyro.' || t.tabla, 'SELECT')
              AND has_table_privilege('nukyro_api', 'nukyro.' || t.tabla, 'INSERT')) = 7$q$);

SET ROLE nukyro_admin;
SELECT pg_temp.allow('D7-60 admin rectifica los datos de la cuenta',
 $q$UPDATE nukyro.accounts SET email = 'rectificado@example.test', nickname = 'rect', newsletter_opt_in = false, surveys_opt_in = false
    WHERE id = pg_temp.id('ac', 320)$q$);
SELECT pg_temp.expect('D7-61 admin no cambia el estado de la cuenta', $q$UPDATE nukyro.accounts SET status = 'blocked' WHERE id = pg_temp.id('ac', 320)$q$, '42501');
SELECT pg_temp.expect('D7-62 admin no cambia cognito_sub', $q$UPDATE nukyro.accounts SET cognito_sub = 'x' WHERE id = pg_temp.id('ac', 320)$q$, '42501');
SELECT pg_temp.expect('D7-63 admin no crea cuentas',
 $q$INSERT INTO nukyro.accounts (cognito_sub, email, nickname) VALUES ('sub-adm', 'a@example.test', 'a')$q$, '42501');
SELECT pg_temp.allow('D7-64 admin registra la oposición (exclude_from_stats)',
 $q$UPDATE nukyro.participants SET exclude_from_stats = true WHERE id = pg_temp.id('bb', 120)$q$);
SELECT pg_temp.expect('D7-65 admin no cambia account_id', $q$UPDATE nukyro.participants SET account_id = NULL WHERE id = pg_temp.id('bb', 120)$q$, '42501');
SELECT pg_temp.expect('D7-66 admin no cambia secret_hash', $q$UPDATE nukyro.participants SET secret_hash = NULL WHERE id = pg_temp.id('bb', 122)$q$, '42501');
SELECT pg_temp.expect('D7-67 admin no borra participantes', $q$DELETE FROM nukyro.participants$q$, '42501');
SELECT pg_temp.expect('D7-68 admin no borra cuentas', $q$DELETE FROM nukyro.accounts$q$, '42501');
RESET ROLE;

-- =====================================================================
-- F · Defecto 9: primera sesión calculada por la base
-- =====================================================================
SELECT pg_temp.mk_anon(130);
SELECT pg_temp.mk_session(230, 130, now() - interval '3 hours', true);
SELECT pg_temp.mk_session(231, 130, now() - interval '2 hours', true);
SELECT pg_temp.chk('D9-03 la base ignora has_prior_session=false enviado en la segunda sesión',
 $q$SELECT (SELECT is_first_session AND NOT has_prior_session FROM sessions WHERE id = pg_temp.id('cc', 230))
        AND (SELECT NOT is_first_session AND has_prior_session FROM sessions WHERE id = pg_temp.id('cc', 231))$q$);
SELECT pg_temp.mk_anon(131);
INSERT INTO sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session)
VALUES (pg_temp.id('cc', 232), pg_temp.id('bb', 131), '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000042', true, true);
SELECT pg_temp.chk('D9-04 la base ignora has_prior_session=true enviado en la primera sesión',
 $q$SELECT is_first_session AND NOT has_prior_session FROM sessions WHERE id = pg_temp.id('cc', 232)$q$);
SELECT pg_temp.mk_anon(132);
SELECT pg_temp.mk_session(233, 132, now() - interval '3 hours', false);
SELECT pg_temp.mk_session(234, 132, now() - interval '2 hours', true);
SELECT pg_temp.chk('D9-05 quien dice no ser primera vez nunca cuenta como primera sesión',
 $q$SELECT NOT (SELECT is_first_session FROM sessions WHERE id = pg_temp.id('cc', 233))
        AND NOT (SELECT is_first_session FROM sessions WHERE id = pg_temp.id('cc', 234))$q$);
-- «Mismo escenario, cualquier versión»: la segunda sesión es en otra versión del escenario
INSERT INTO scenarios (id, key, title) VALUES (pg_temp.id('50', 9), 'D9', 'Escenario del defecto 9');
INSERT INTO scenario_versions (id, scenario_id, version_number, title) VALUES (pg_temp.id('51', 91), pg_temp.id('50', 9), 1, 'D9 v1');
INSERT INTO nodes (id, version_id, key, node_type, title, body) VALUES (pg_temp.id('52', 91), pg_temp.id('51', 91), 'N', 'info', 't', 'b');
UPDATE scenario_versions SET status = 'published', published_at = now() WHERE id = pg_temp.id('51', 91);
SELECT pg_temp.mk_anon(133);
INSERT INTO sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session)
VALUES (pg_temp.id('cc', 235), pg_temp.id('bb', 133), pg_temp.id('51', 91), pg_temp.id('52', 91), true, false);
INSERT INTO scenario_versions (id, scenario_id, version_number, title) VALUES (pg_temp.id('51', 92), pg_temp.id('50', 9), 2, 'D9 v2');
INSERT INTO nodes (id, version_id, key, node_type, title, body) VALUES (pg_temp.id('52', 92), pg_temp.id('51', 92), 'N', 'info', 't', 'b');
UPDATE scenario_versions SET status = 'retired', retired_at = now() WHERE id = pg_temp.id('51', 91);
UPDATE scenario_versions SET status = 'published', published_at = now() WHERE id = pg_temp.id('51', 92);
INSERT INTO sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session)
VALUES (pg_temp.id('cc', 236), pg_temp.id('bb', 133), pg_temp.id('51', 92), pg_temp.id('52', 92), true, false);
SELECT pg_temp.chk('D9-06 una sesión previa en otra versión del mismo escenario cuenta',
 $q$SELECT (SELECT is_first_session FROM sessions WHERE id = pg_temp.id('cc', 235))
        AND (SELECT has_prior_session AND NOT is_first_session FROM sessions WHERE id = pg_temp.id('cc', 236))$q$);
-- Una sesión en otro escenario no cuenta como previa
INSERT INTO sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session)
VALUES (pg_temp.id('cc', 237), pg_temp.id('bb', 130), pg_temp.id('51', 92), pg_temp.id('52', 92), true, true);
SELECT pg_temp.chk('D9-07 una sesión previa en OTRO escenario no cuenta',
 $q$SELECT is_first_session AND NOT has_prior_session FROM sessions WHERE id = pg_temp.id('cc', 237)$q$);

-- Reescritura: xmin común y orden físico distinto del de llegada (T-10, auditoría de E2)
DELETE FROM decision_facts;
INSERT INTO decision_facts (scenario_version_id, week_start, decision_key, option_key, is_first_session)
SELECT '00000000-0000-0000-0000-000000000011', date '2026-11-16', 'D01', lpad(i::text, 3, '0'), true FROM generate_series(1, 20) i;
INSERT INTO decision_facts (scenario_version_id, week_start, decision_key, option_key, is_first_session)
SELECT '00000000-0000-0000-0000-000000000011', date '2026-11-16', 'D01', lpad(i::text, 3, '0'), true FROM generate_series(21, 40) i;
SELECT pg_temp.chk('D2-30 antes de reescribir el xmin separa las dos llegadas',
 $q$SELECT count(DISTINCT xmin::text) = 2 FROM decision_facts$q$);
SELECT rewrite_facts();
SELECT pg_temp.chk('D2-31 tras reescribir, las dos llegadas comparten xmin',
 $q$SELECT count(*) = 40 AND count(DISTINCT xmin::text) = 1 FROM decision_facts$q$);
SELECT pg_temp.chk('D2-32 tras reescribir, el orden físico no es el de llegada',
 $q$SELECT array_agg(option_key ORDER BY ctid) <> array_agg(option_key ORDER BY option_key) FROM decision_facts$q$);

-- ---------------------------------------------------------------------
-- T-14 · Hitos de la sesión de una sola escritura (RF-005, RF-061)
-- Cada hito pasa una vez de NULL a un valor; después ni se reescribe ni se borra.
-- ---------------------------------------------------------------------
SELECT pg_temp.mk_anon(140);
SELECT pg_temp.mk_session(240, 140);
SELECT pg_temp.allow('H-01 el pre-test pasa de NULL a una fecha',
 $q$UPDATE sessions SET pretest_completed_at = now() WHERE id = pg_temp.id('cc', 240)$q$);
SELECT pg_temp.expect('H-02 el pre-test no se reescribe',
 $q$UPDATE sessions SET pretest_completed_at = now() + interval '1 minute' WHERE id = pg_temp.id('cc', 240)$q$, '23514');
SELECT pg_temp.expect('H-03 el pre-test no se borra',
 $q$UPDATE sessions SET pretest_completed_at = NULL WHERE id = pg_temp.id('cc', 240)$q$, '23514');
SELECT pg_temp.allow('H-04 el desenlace y su nodo se escriben juntos una vez',
 $q$UPDATE sessions SET outcome_reached_at = now(), outcome_node_id = '00000000-0000-0000-0000-000000000044' WHERE id = pg_temp.id('cc', 240)$q$);
SELECT pg_temp.expect('H-05 el nodo del desenlace no cambia',
 $q$UPDATE sessions SET outcome_node_id = '00000000-0000-0000-0000-000000000045' WHERE id = pg_temp.id('cc', 240)$q$, '23514');
SELECT pg_temp.expect('H-06 la fecha del desenlace no cambia',
 $q$UPDATE sessions SET outcome_reached_at = outcome_reached_at + interval '1 minute' WHERE id = pg_temp.id('cc', 240)$q$, '23514');
SELECT pg_temp.expect('H-07 el desenlace no se borra',
 $q$UPDATE sessions SET outcome_reached_at = NULL, outcome_node_id = NULL WHERE id = pg_temp.id('cc', 240)$q$, '23514');
SELECT pg_temp.allow('H-08 completed_at pasa de NULL a una fecha',
 $q$UPDATE sessions SET completed_at = now() WHERE id = pg_temp.id('cc', 240)$q$);
SELECT pg_temp.expect('H-09 completed_at no se reescribe',
 $q$UPDATE sessions SET completed_at = completed_at + interval '1 minute' WHERE id = pg_temp.id('cc', 240)$q$, '23514');
SELECT pg_temp.expect('H-10 completed_at no se borra',
 $q$UPDATE sessions SET completed_at = NULL WHERE id = pg_temp.id('cc', 240)$q$, '23514');
SELECT pg_temp.allow('H-11 repetir el mismo valor no es una reescritura',
 $q$UPDATE sessions SET pretest_completed_at = pretest_completed_at, completed_at = completed_at WHERE id = pg_temp.id('cc', 240)$q$);
SELECT pg_temp.allow('H-12 las demás columnas se siguen actualizando (actividad, archivo)',
 $q$UPDATE sessions SET last_activity_at = now(), survey_answered = true, facts_written_at = now() WHERE id = pg_temp.id('cc', 240)$q$);
SELECT pg_temp.allow('H-13 borrar al participante borra la sesión con sus hitos (cascada)',
 $q$DELETE FROM participants WHERE id = pg_temp.id('bb', 140)$q$);
SELECT pg_temp.chk('H-14 la sesión borrada ya no existe',
 $q$SELECT NOT EXISTS (SELECT 1 FROM sessions WHERE id = pg_temp.id('cc', 240))$q$);

-- G · T-16: submit_survey (D-29, ADR-007)
-- ---------------------------------------------------------------------
SELECT pg_temp.mk_anon(401); SELECT pg_temp.mk_rich_session(401, 401);   -- terminada, responde
SELECT pg_temp.mk_anon(402); SELECT pg_temp.mk_session(402, 402);        -- sin terminar
SELECT pg_temp.mk_anon(403); SELECT pg_temp.mk_rich_session(403, 403);   -- se opone
UPDATE participants SET exclude_from_stats = true WHERE id = pg_temp.id('bb', 403);
SELECT set_config('nukyro_t.last', (SELECT last_activity_at::text FROM sessions WHERE id = pg_temp.id('cc', 401)), false);

SELECT pg_temp.chk('S-01 submit_survey: definer, search_path fijo, EXECUTE a api y a nadie más',
 $q$SELECT p.prosecdef AND p.proconfig IS NOT NULL AND p.proconfig::text LIKE '%search_path%'
        AND has_function_privilege('nukyro_api', p.oid, 'EXECUTE')
        AND NOT has_function_privilege('nukyro_jobs', p.oid, 'EXECUTE')
        AND NOT has_function_privilege('nukyro_analytics', p.oid, 'EXECUTE')
        AND NOT has_function_privilege('nukyro_admin', p.oid, 'EXECUTE')
        AND NOT EXISTS (SELECT 1 FROM aclexplode(p.proacl) a WHERE a.grantee = 0)
      FROM pg_proc p WHERE p.proname = 'submit_survey' AND p.pronamespace = 'nukyro'::regnamespace$q$);
SET ROLE nukyro_api;
SELECT pg_temp.expect('S-02 una sesión sin terminar se rechaza (55000)',
 $q$SELECT nukyro.submit_survey(pg_temp.id('cc', 402), 4::smallint)$q$, '55000');
SELECT pg_temp.expect('S-03 el participante opuesto se rechaza (42501)',
 $q$SELECT nukyro.submit_survey(pg_temp.id('cc', 403), 4::smallint)$q$, '42501');
SELECT pg_temp.expect('S-04 una sesión inexistente se rechaza (P0002)',
 $q$SELECT nukyro.submit_survey(pg_temp.id('cc', 499), 4::smallint)$q$, 'P0002');
SELECT pg_temp.expect('S-05 una escala fuera de 1 a 5 se rechaza (23514)',
 $q$SELECT nukyro.submit_survey(pg_temp.id('cc', 401), 4::smallint, 9::smallint)$q$, '23514');
SELECT pg_temp.allow('S-06 la sesión terminada responde',
 $q$SELECT nukyro.submit_survey(pg_temp.id('cc', 401), 4::smallint, 3::smallint)$q$);
SELECT pg_temp.expect('S-07 solo se responde una vez (23505)',
 $q$SELECT nukyro.submit_survey(pg_temp.id('cc', 401), 5::smallint)$q$, '23505');
RESET ROLE;
SELECT pg_temp.chk('S-08 queda survey_answered y la actividad de la sesión no cambia',
 $q$SELECT survey_answered AND last_activity_at::text = current_setting('nukyro_t.last')
      FROM sessions WHERE id = pg_temp.id('cc', 401)$q$);
SELECT pg_temp.chk('S-09 lo rechazado no dejó nada: sin terminar y opuesto siguen sin marca',
 $q$SELECT NOT EXISTS (SELECT 1 FROM sessions WHERE id IN (pg_temp.id('cc', 402), pg_temp.id('cc', 403)) AND survey_answered)
        AND (SELECT count(*) FROM survey_responses WHERE clarity = 3) = 1$q$);
SELECT pg_temp.chk('S-10 la semana es la UTC de inicio de la sesión (lunes 2026-11-30)',
 $q$SELECT week_start = DATE '2026-11-30' FROM survey_responses WHERE clarity = 3$q$);
SELECT set_config('nukyro_t.sx1', (SELECT xmin::text FROM survey_responses LIMIT 1), false);

-- Diez envíos más, cada uno en su transacción (\gexec): arribo con (claridad, impacto) = índice 0 a 9
SELECT pg_temp.mk_anon(410 + g), pg_temp.mk_rich_session(410 + g, 410 + g) FROM generate_series(0, 9) g;
SELECT format('SET ROLE nukyro_api; SELECT nukyro.submit_survey(%L, 3::smallint, %s::smallint, %s::smallint); RESET ROLE;',
              pg_temp.id('cc', 410 + g), g / 5 + 1, g % 5 + 1)
  FROM generate_series(0, 9) g ORDER BY g \gexec
SELECT pg_temp.chk('S-11 tras varios envíos todas las filas comparten xmin, distinto del primero',
 $q$SELECT (SELECT count(DISTINCT xmin::text) FROM survey_responses) = 1
        AND (SELECT xmin::text FROM survey_responses LIMIT 1) <> current_setting('nukyro_t.sx1')$q$);
SELECT pg_temp.chk('S-12 el orden físico no es el de llegada',
 $q$SELECT array_agg((clarity - 1) * 5 + decision_impact ORDER BY ctid)
        <> array_agg((clarity - 1) * 5 + decision_impact ORDER BY (clarity - 1) * 5 + decision_impact)
      FROM survey_responses WHERE decision_impact IS NOT NULL$q$);
SELECT pg_temp.chk('S-13 hay once encuestas con claridad y las sesiones quedan marcadas',
 $q$SELECT (SELECT count(*) FROM survey_responses WHERE clarity IS NOT NULL) = 11
        AND (SELECT count(*) FROM sessions WHERE survey_answered AND id IN
             (SELECT pg_temp.id('cc', 410 + g) FROM generate_series(0, 9) g)) = 10$q$);

-- ---------------------------------------------------------------------
-- T-18 · Vincular el progreso de un navegador con una cuenta (P10, RF-076, defecto 9)
-- link_participant: función del owner, solo para api. La API no puede borrar participantes
-- ni mover sesiones por su cuenta.
-- ---------------------------------------------------------------------
-- L-01..L-03: la cuenta no tiene participante, el del navegador pasa a ser suyo
SELECT pg_temp.mk_anon(500);
SELECT pg_temp.mk_session(500, 500, now() - interval '2 hours');
SELECT pg_temp.mk_account(500);
SET ROLE nukyro_api;
SELECT pg_temp.chk('L-01 sin participante en la cuenta, el del navegador pasa a ser suyo',
 $q$SELECT nukyro.link_participant(pg_temp.id('ac', 500), sha256(convert_to('secreto-500', 'UTF8'))) = 'linked'$q$);
RESET ROLE;
SELECT pg_temp.chk('L-02 queda ligado a la cuenta, sin secreto, y conserva su sesión',
 $q$SELECT p.account_id = pg_temp.id('ac', 500) AND p.secret_hash IS NULL AND p.id = pg_temp.id('bb', 500)
        AND (SELECT participant_id FROM sessions WHERE id = pg_temp.id('cc', 500)) = p.id
      FROM participants p WHERE p.id = pg_temp.id('bb', 500)$q$);
SET ROLE nukyro_api;
SELECT pg_temp.chk('L-03 repetirla no hace nada: el secreto ya no existe',
 $q$SELECT nukyro.link_participant(pg_temp.id('ac', 500), sha256(convert_to('secreto-500', 'UTF8'))) = 'none'$q$);
RESET ROLE;

-- L-04..L-08: la cuenta ya tenía participante y sesión; el navegador también (el más reciente)
SELECT pg_temp.mk_account(501, 501);
SELECT pg_temp.mk_session(501, 501, now() - interval '5 hours');
SELECT pg_temp.mk_anon(502);
SELECT pg_temp.mk_session(502, 502, now() - interval '2 hours');
-- el navegador acepta un documento que la cuenta no tiene, y los dos aceptaron la edad
INSERT INTO document_acceptances (participant_id, document_type, document_version) VALUES
  (pg_temp.id('bb', 501), 'age_18_plus', NULL), (pg_temp.id('bb', 502), 'age_18_plus', NULL),
  (pg_temp.id('bb', 502), 'terms', 'T-B');
UPDATE participants SET exclude_from_stats = true WHERE id = pg_temp.id('bb', 502);
SELECT pg_temp.chk('L-04 antes de vincular hay dos primeras sesiones (el defecto 9)',
 $q$SELECT (SELECT count(*) FROM sessions WHERE id IN (pg_temp.id('cc', 501), pg_temp.id('cc', 502)) AND is_first_session) = 2$q$);
SET ROLE nukyro_api;
SELECT pg_temp.chk('L-05 con participante en la cuenta, se trasladan las sesiones',
 $q$SELECT nukyro.link_participant(pg_temp.id('ac', 501), sha256(convert_to('secreto-502', 'UTF8'))) = 'merged'$q$);
RESET ROLE;
SELECT pg_temp.chk('L-06 el del navegador se borra y las dos sesiones son de la cuenta',
 $q$SELECT NOT EXISTS (SELECT 1 FROM participants WHERE id = pg_temp.id('bb', 502))
        AND (SELECT count(*) FROM sessions WHERE participant_id = pg_temp.id('bb', 501)
               AND id IN (pg_temp.id('cc', 501), pg_temp.id('cc', 502))) = 2$q$);
SELECT pg_temp.chk('L-07 queda una sola primera sesión: la más antigua; la otra tiene previa',
 $q$SELECT (SELECT is_first_session AND NOT has_prior_session FROM sessions WHERE id = pg_temp.id('cc', 501))
        AND (SELECT has_prior_session AND NOT is_first_session FROM sessions WHERE id = pg_temp.id('cc', 502))$q$);
SELECT pg_temp.chk('L-08 las aceptaciones se copian sin duplicar y la exclusión se conserva (OR)',
 $q$SELECT (SELECT count(*) FROM document_acceptances WHERE participant_id = pg_temp.id('bb', 501)) = 2
        AND EXISTS (SELECT 1 FROM document_acceptances WHERE participant_id = pg_temp.id('bb', 501)
                      AND document_type = 'terms' AND document_version = 'T-B')
        AND (SELECT exclude_from_stats FROM participants WHERE id = pg_temp.id('bb', 501))$q$);

-- L-09: al revés, la sesión del navegador es la más antigua y pasa a ser la primera
SELECT pg_temp.mk_account(503, 503);
SELECT pg_temp.mk_session(503, 503, now() - interval '2 hours');
SELECT pg_temp.mk_anon(504);
SELECT pg_temp.mk_session(504, 504, now() - interval '6 hours');
SET ROLE nukyro_api;
SELECT nukyro.link_participant(pg_temp.id('ac', 503), sha256(convert_to('secreto-504', 'UTF8')));
RESET ROLE;
SELECT pg_temp.chk('L-09 si la del navegador es más antigua, es ella la primera',
 $q$SELECT (SELECT is_first_session FROM sessions WHERE id = pg_temp.id('cc', 504))
        AND (SELECT has_prior_session FROM sessions WHERE id = pg_temp.id('cc', 503))$q$);

-- L-10: otro escenario no se mezcla (la versión 92 del defecto 9 es de otro escenario)
SELECT pg_temp.mk_account(505, 505);
SELECT pg_temp.mk_session(505, 505, now() - interval '5 hours');
SELECT pg_temp.mk_anon(506);
INSERT INTO sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first, started_at, last_activity_at)
VALUES (pg_temp.id('cc', 506), pg_temp.id('bb', 506), pg_temp.id('51', 92), pg_temp.id('52', 92), true,
        now() - interval '1 hour', now() - interval '1 hour');
SET ROLE nukyro_api;
SELECT nukyro.link_participant(pg_temp.id('ac', 505), sha256(convert_to('secreto-506', 'UTF8')));
RESET ROLE;
SELECT pg_temp.chk('L-10 dos escenarios distintos: cada uno conserva su primera sesión',
 $q$SELECT (SELECT is_first_session FROM sessions WHERE id = pg_temp.id('cc', 505))
        AND (SELECT is_first_session FROM sessions WHERE id = pg_temp.id('cc', 506))$q$);

-- L-11, L-12: cuenta bloqueada o inexistente
SELECT pg_temp.mk_account(507, 507);
SELECT pg_temp.mk_anon(508);
SELECT pg_temp.mk_session(508, 508);
UPDATE accounts SET status = 'blocked', blocked_at = now(), block_reason = 'user_request',
       deletion_due_at = now() + interval '1 day' WHERE id = pg_temp.id('ac', 507);
SET ROLE nukyro_api;
SELECT pg_temp.expect('L-11 una cuenta bloqueada no recibe progreso (23514)',
 $q$SELECT nukyro.link_participant(pg_temp.id('ac', 507), sha256(convert_to('secreto-508', 'UTF8')))$q$, '23514');
SELECT pg_temp.expect('L-12 una cuenta inexistente se rechaza (P0002)',
 $q$SELECT nukyro.link_participant(pg_temp.id('ac', 599), sha256(convert_to('secreto-508', 'UTF8')))$q$, 'P0002');
RESET ROLE;
SELECT pg_temp.chk('L-13 lo rechazado no movió nada: el del navegador sigue con su secreto',
 $q$SELECT secret_hash IS NOT NULL AND account_id IS NULL FROM participants WHERE id = pg_temp.id('bb', 508)$q$);

-- L-14: un secreto de alguien que ya tiene cuenta no se puede vincular a otra
SELECT pg_temp.mk_account(509, 509, true);
SELECT pg_temp.mk_account(510);
SET ROLE nukyro_api;
SELECT pg_temp.chk('L-14 solo se vincula a un participante sin cuenta',
 $q$SELECT nukyro.link_participant(pg_temp.id('ac', 510), sha256(convert_to('secreto-509', 'UTF8'))) = 'none'$q$);
SELECT pg_temp.chk('L-15 un hash nulo no hace nada',
 $q$SELECT nukyro.link_participant(pg_temp.id('ac', 510), NULL) = 'none'$q$);
RESET ROLE;

-- L-16..L-19: permisos. Solo api ejecuta la función, y api no hace el traslado por su cuenta
SELECT pg_temp.chk('L-16 api puede ejecutarla; analytics, jobs y PUBLIC no',
 $q$SELECT has_function_privilege('nukyro_api', 'nukyro.link_participant(uuid, bytea)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_analytics', 'nukyro.link_participant(uuid, bytea)', 'EXECUTE')
        AND NOT has_function_privilege('nukyro_jobs', 'nukyro.link_participant(uuid, bytea)', 'EXECUTE')
        AND NOT EXISTS (SELECT 1 FROM pg_proc p, aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
                         WHERE p.proname = 'link_participant' AND a.grantee = 0)$q$);
SET ROLE nukyro_api;
SELECT pg_temp.expect('L-17 api no borra participantes', $q$DELETE FROM nukyro.participants WHERE id = pg_temp.id('bb', 508)$q$, '42501');
SELECT pg_temp.expect('L-18 api no cambia el participante de una sesión',
 $q$UPDATE nukyro.sessions SET participant_id = pg_temp.id('bb', 501) WHERE id = pg_temp.id('cc', 508)$q$, '42501');
RESET ROLE;
SELECT pg_temp.chk('L-19 la función es del owner, SECURITY DEFINER y con search_path fijo',
 $q$SELECT p.prosecdef AND p.proowner = 'nukyro_owner'::regrole
        AND EXISTS (SELECT 1 FROM unnest(p.proconfig) c WHERE c LIKE 'search_path=%')
      FROM pg_proc p WHERE p.proname = 'link_participant'$q$);

SELECT pg_temp.finish();
