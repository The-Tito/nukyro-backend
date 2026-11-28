-- =====================================================================
-- Nukyro · Pruebas de las reglas que garantiza la base (§5 del modelo)
-- Requiere: bd/schema.sql y bd/seed-prueba.sql. Ejecutar como superusuario
-- en una base desechable:
--   psql -v ON_ERROR_STOP=1 -f bd/pruebas/pruebas-reglas.sql
-- Cada prueba imprime PASS; cualquier FAIL detiene el script.
-- =====================================================================
\set ON_ERROR_STOP 1
SET search_path = nukyro, public;
SET client_min_messages = notice;

-- expect(nombre, sql, sqlstate esperado): la sentencia debe fallar con ese código
CREATE FUNCTION pg_temp.expect(p_name text, p_sql text, p_state text) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        EXECUTE p_sql;
    EXCEPTION WHEN OTHERS THEN
        IF SQLSTATE = p_state THEN
            RAISE NOTICE 'PASS %  (% %)', p_name, SQLSTATE, left(SQLERRM, 90);
            RETURN;
        END IF;
        RAISE EXCEPTION 'FAIL %: se esperaba %, llegó % %', p_name, p_state, SQLSTATE, SQLERRM;
    END;
    RAISE EXCEPTION 'FAIL %: no falló (se esperaba %)', p_name, p_state;
END $$;

CREATE FUNCTION pg_temp.ok(p_name text, p_cond boolean) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    IF p_cond THEN RAISE NOTICE 'PASS %', p_name;
    ELSE RAISE EXCEPTION 'FAIL %', p_name; END IF;
END $$;

-- ------------------------- Contenido ---------------------------------
-- Etapa 2 (defecto 5): ya no se inserta una versión publicada; se publica un borrador
-- teniendo otra publicada. Insertar publicado se prueba aparte (pruebas-defectos.sql).
SELECT pg_temp.expect('T01 RN-16 una sola versión publicada (publicar un borrador con otra publicada)',
 $q$UPDATE scenario_versions SET status = 'published', published_at = now()
    WHERE id = '00000000-0000-0000-0000-000000000012'$q$, '23505');

SELECT pg_temp.expect('T02 RN-16/H-10 un solo borrador',
 $q$INSERT INTO scenario_versions (scenario_id, version_number, title) VALUES ('00000000-0000-0000-0000-000000000001', 9, 'otro borrador')$q$, '23505');

SELECT pg_temp.expect('T03 ADR-001 contenido publicado inmutable (UPDATE)',
 $q$UPDATE nodes SET title = 'cambio' WHERE id = '00000000-0000-0000-0000-000000000042'$q$, '23514');

SELECT pg_temp.expect('T04 ADR-001 contenido publicado inmutable (INSERT)',
 $q$INSERT INTO nodes (version_id, key, node_type, title, body)
    VALUES ('00000000-0000-0000-0000-000000000011', 'NEW', 'info', 'x', 'y')$q$, '23514');

SELECT pg_temp.expect('T05 RN-17 no borrar versión publicada',
 $q$DELETE FROM scenario_versions WHERE id = '00000000-0000-0000-0000-000000000011'$q$, '23514');

SELECT pg_temp.expect('T06 transición published → draft prohibida',
 $q$UPDATE scenario_versions SET status = 'draft', published_at = NULL WHERE id = '00000000-0000-0000-0000-000000000011'$q$, '23514');

SELECT pg_temp.expect('T07 retirar cambiando el título prohibido',
 $q$UPDATE scenario_versions SET status = 'retired', retired_at = now(), title = 'x' WHERE id = '00000000-0000-0000-0000-000000000011'$q$, '23514');

SELECT pg_temp.expect('T08 RN-08 referencia legal sin jurisdicción',
 $q$INSERT INTO educational_references (version_id, key, ref_category, title, source)
    VALUES ('00000000-0000-0000-0000-000000000012', 'L1', 'legal', 'Ley', 'DOF')$q$, '23514');

SELECT pg_temp.expect('T09 RF-009 una sola opción correcta',
 $q$INSERT INTO question_sets (id, version_id, set_type) VALUES ('00000000-0000-0000-0000-000000000191', '00000000-0000-0000-0000-000000000012', 'pretest');
    INSERT INTO questions (id, version_id, question_set_id, key, prompt, topic, learning_objective_id)
    VALUES ('00000000-0000-0000-0000-0000000001a1', '00000000-0000-0000-0000-000000000012', '00000000-0000-0000-0000-000000000191', 'P', '?', 't', '00000000-0000-0000-0000-000000000121');
    INSERT INTO question_options (version_id, question_id, key, label, is_correct) VALUES
    ('00000000-0000-0000-0000-000000000012', '00000000-0000-0000-0000-0000000001a1', 'A', 'a', true),
    ('00000000-0000-0000-0000-000000000012', '00000000-0000-0000-0000-0000000001a1', 'B', 'b', true)$q$, '23505');

SELECT pg_temp.expect('T10 opción de otra versión no puede ser "siguiente nodo"',
 $q$SET CONSTRAINTS ALL IMMEDIATE;
    UPDATE options SET next_node_id = '00000000-0000-0000-0000-000000000043' WHERE id = '00000000-0000-0000-0000-000000000151'$q$, '23503');

-- T10b: la referencia diferida también falla en un COMMIT real (H-11)
\set ON_ERROR_STOP 0
BEGIN;
UPDATE options SET next_node_id = '00000000-0000-0000-0000-000000000043' WHERE id = '00000000-0000-0000-0000-000000000151';
COMMIT;
\set ON_ERROR_STOP 1
SELECT pg_temp.ok('T10b referencia diferida rechazada al COMMIT',
 (SELECT next_node_id IS NULL FROM options WHERE id = '00000000-0000-0000-0000-000000000151'));

-- ------------------------- Identidad ---------------------------------
SELECT pg_temp.expect('T11 participante sin cuenta ni secreto',
 $q$INSERT INTO participants DEFAULT VALUES$q$, '23514');

SELECT pg_temp.expect('T12 hash del secreto de 32 bytes',
 $q$INSERT INTO participants (secret_hash) VALUES ('\x01'::bytea)$q$, '23514');

INSERT INTO accounts (id, cognito_sub, email, nickname)
VALUES ('00000000-0000-0000-0000-00000000ac01', 'cognito-user-1', 'u1@example.test', 'nick');
INSERT INTO participants (id, secret_hash) VALUES
 ('00000000-0000-0000-0000-00000000aa01', sha256('secreto-navegador-1')),
 ('00000000-0000-0000-0000-00000000aa02', sha256('secreto-navegador-2'));
INSERT INTO participants (id, account_id) VALUES ('00000000-0000-0000-0000-00000000aa03', '00000000-0000-0000-0000-00000000ac01');

SELECT pg_temp.expect('T13 una cuenta, un participante',
 $q$INSERT INTO participants (account_id) VALUES ('00000000-0000-0000-0000-00000000ac01')$q$, '23505');

INSERT INTO document_acceptances (participant_id, document_type, document_version) VALUES
 ('00000000-0000-0000-0000-00000000aa01', 'age_18_plus', NULL),
 ('00000000-0000-0000-0000-00000000aa01', 'privacy_notice', '2.1'),
 ('00000000-0000-0000-0000-00000000aa01', 'terms', '1.0');
SELECT pg_temp.expect('T14 aceptación duplicada (NULLS NOT DISTINCT)',
 $q$INSERT INTO document_acceptances (participant_id, document_type, document_version)
    VALUES ('00000000-0000-0000-0000-00000000aa01', 'age_18_plus', NULL)$q$, '23505');

SELECT pg_temp.expect('T15 RF-086 solicitud cerrada con documento de identidad',
 $q$INSERT INTO arco_requests (requester_email, right_type, description, status, response_due_on, executed_at, closed_at, identity_doc_key)
    VALUES ('u1@example.test', 'cancellation', 'Borrar', 'executed', current_date + 20, now(), now(), 's3://doc')$q$, '23514');

SELECT pg_temp.expect('T16 bloqueo sin motivo ni fecha de borrado',
 $q$UPDATE accounts SET status = 'blocked' WHERE id = '00000000-0000-0000-0000-00000000ac01'$q$, '23514');

-- ------------------------- Simulación --------------------------------
SELECT pg_temp.expect('T17 RN-15 sesión sobre versión en borrador',
 $q$INSERT INTO sessions (participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session)
    VALUES ('00000000-0000-0000-0000-00000000aa01', '00000000-0000-0000-0000-000000000012', '00000000-0000-0000-0000-000000000142', true, false)$q$, '23514');

SELECT pg_temp.expect('T18 nodo actual de otra versión',
 $q$INSERT INTO sessions (participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session)
    VALUES ('00000000-0000-0000-0000-00000000aa01', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000142', true, false)$q$, '23503');

-- Preparación (defecto 9): has_prior_session lo calcula la base e ignora el valor enviado.
-- Para que 5e03 siga siendo «no primera sesión», aa03 tiene antes otra sesión (5e04).
INSERT INTO sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session, pretest_completed_at) VALUES
 ('00000000-0000-0000-0000-000000005e04', '00000000-0000-0000-0000-00000000aa03', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000042', false, false, now());
INSERT INTO sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session, pretest_completed_at) VALUES
 ('00000000-0000-0000-0000-000000005e01', '00000000-0000-0000-0000-00000000aa01', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000042', true,  false, now()),
 ('00000000-0000-0000-0000-000000005e02', '00000000-0000-0000-0000-00000000aa02', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000042', false, false, now()),
 ('00000000-0000-0000-0000-000000005e03', '00000000-0000-0000-0000-00000000aa03', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000042', true,  true,  now());
SELECT pg_temp.ok('T19 RN-18 is_first_session generada',
 (SELECT array_agg(is_first_session ORDER BY id) FROM sessions
   WHERE id IN ('00000000-0000-0000-0000-000000005e01', '00000000-0000-0000-0000-000000005e02',
                '00000000-0000-0000-0000-000000005e03')) = ARRAY[true, false, false]);

INSERT INTO session_variables (session_id, scenario_version_id, variable_id, value)
SELECT s.id, s.scenario_version_id, v.id, v.initial_value
  FROM sessions s JOIN state_variables v ON v.version_id = s.scenario_version_id;

SELECT pg_temp.expect('T20 variable de otra versión',
 $q$INSERT INTO session_variables (session_id, scenario_version_id, variable_id, value)
    VALUES ('00000000-0000-0000-0000-000000005e01', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000131', 1)$q$, '23503');

-- Primera confirmación y reintento (RN-14)
INSERT INTO session_decisions (id, session_id, scenario_version_id, node_id, option_id, justification_correct)
VALUES ('00000000-0000-0000-0000-00000000de01', '00000000-0000-0000-0000-000000005e01', '00000000-0000-0000-0000-000000000011',
        '00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000051', true);
WITH retry AS (
    INSERT INTO session_decisions (session_id, scenario_version_id, node_id, option_id)
    VALUES ('00000000-0000-0000-0000-000000005e01', '00000000-0000-0000-0000-000000000011',
            '00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000052')
    ON CONFLICT (session_id, node_id) DO NOTHING RETURNING id)
SELECT pg_temp.ok('T21 RN-14 reintento no crea otra decisión (ON CONFLICT DO NOTHING)',
 (SELECT count(*) FROM retry) = 0
 AND (SELECT option_id FROM session_decisions WHERE session_id = '00000000-0000-0000-0000-000000005e01')
     = '00000000-0000-0000-0000-000000000051');

SELECT pg_temp.expect('T22 RN-03 alternativa que no pertenece al nodo',
 $q$INSERT INTO session_decisions (session_id, scenario_version_id, node_id, option_id)
    VALUES ('00000000-0000-0000-0000-000000005e02', '00000000-0000-0000-0000-000000000011',
            '00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000151')$q$, '23503');

SELECT pg_temp.expect('T23 RN-02 nodo de otra versión en la sesión',
 $q$INSERT INTO session_decisions (session_id, scenario_version_id, node_id, option_id)
    VALUES ('00000000-0000-0000-0000-000000005e02', '00000000-0000-0000-0000-000000000012',
            '00000000-0000-0000-0000-000000000142', '00000000-0000-0000-0000-000000000151')$q$, '23503');

INSERT INTO session_decision_reasons (session_decision_id, node_id, reason_id)
VALUES ('00000000-0000-0000-0000-00000000de01', '00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000061');
SELECT pg_temp.expect('T24 razón de otro nodo',
 $q$INSERT INTO session_decision_reasons (session_decision_id, node_id, reason_id)
    VALUES ('00000000-0000-0000-0000-00000000de01', '00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000161')$q$, '23503');

INSERT INTO session_effects (session_decision_id, session_id, variable_id, old_value, new_value)
VALUES ('00000000-0000-0000-0000-00000000de01', '00000000-0000-0000-0000-000000005e01', '00000000-0000-0000-0000-000000000031', 3, 1);
UPDATE session_variables SET value = 1 WHERE session_id = '00000000-0000-0000-0000-000000005e01' AND variable_id = '00000000-0000-0000-0000-000000000031';

INSERT INTO session_events (id, session_id, scenario_version_id, rule_id)
VALUES ('00000000-0000-0000-0000-00000000e701', '00000000-0000-0000-0000-000000005e01', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000071');
INSERT INTO session_event_causes (session_event_id, session_id, session_decision_id)
VALUES ('00000000-0000-0000-0000-00000000e701', '00000000-0000-0000-0000-000000005e01', '00000000-0000-0000-0000-00000000de01');

INSERT INTO session_decisions (id, session_id, scenario_version_id, node_id, option_id)
VALUES ('00000000-0000-0000-0000-00000000de02', '00000000-0000-0000-0000-000000005e02', '00000000-0000-0000-0000-000000000011',
        '00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000052');
SELECT pg_temp.expect('T25 RF-065 causa tomada de otra sesión',
 $q$INSERT INTO session_event_causes (session_event_id, session_id, session_decision_id)
    VALUES ('00000000-0000-0000-0000-00000000e701', '00000000-0000-0000-0000-000000005e01', '00000000-0000-0000-0000-00000000de02')$q$, '23503');

SELECT pg_temp.expect('T26 regla activada dos veces en la sesión',
 $q$INSERT INTO session_events (session_id, scenario_version_id, rule_id)
    VALUES ('00000000-0000-0000-0000-000000005e01', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000071')$q$, '23505');

-- Evaluaciones
INSERT INTO assessment_attempts (id, session_id, scenario_version_id, question_set_id)
VALUES ('00000000-0000-0000-0000-0000000a0001', '00000000-0000-0000-0000-000000005e01', '00000000-0000-0000-0000-000000000011',
        '00000000-0000-0000-0000-000000000091');
INSERT INTO assessment_answers (attempt_id, question_set_id, question_id, option_id)
VALUES ('00000000-0000-0000-0000-0000000a0001', '00000000-0000-0000-0000-000000000091', '00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000b1');
UPDATE assessment_attempts SET submitted_at = now(), answered_count = 1, correct_count = 1, score = 100
 WHERE id = '00000000-0000-0000-0000-0000000a0001';

SELECT pg_temp.expect('T27 RN-19 un intento por conjunto',
 $q$INSERT INTO assessment_attempts (session_id, scenario_version_id, question_set_id)
    VALUES ('00000000-0000-0000-0000-000000005e01', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000091')$q$, '23505');

SELECT pg_temp.expect('T28 respuesta con opción de otra pregunta',
 $q$UPDATE assessment_answers SET option_id = '00000000-0000-0000-0000-0000000000b3'
    WHERE attempt_id = '00000000-0000-0000-0000-0000000a0001'$q$, '23503');

SELECT pg_temp.expect('T29 pregunta que no es del conjunto del intento',
 $q$INSERT INTO assessment_answers (attempt_id, question_set_id, question_id, option_id)
    VALUES ('00000000-0000-0000-0000-0000000a0001', '00000000-0000-0000-0000-000000000091', '00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-0000000000b3')$q$, '23503');

-- Sesión sin pre-test (el trigger de hitos impediría borrarlo en 5e01: aquí se prueba el CHECK de orden)
INSERT INTO sessions (id, participant_id, scenario_version_id, current_node_id, self_reported_first)
VALUES ('00000000-0000-0000-0000-000000005e05', '00000000-0000-0000-0000-00000000aa01', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000042', true);
SELECT pg_temp.expect('T30 hitos fuera de orden (desenlace sin pre-test)',
 $q$UPDATE sessions SET outcome_reached_at = now(), outcome_node_id = '00000000-0000-0000-0000-000000000044'
    WHERE id = '00000000-0000-0000-0000-000000005e05'$q$, '23514');
DELETE FROM sessions WHERE id = '00000000-0000-0000-0000-000000005e05';

SELECT pg_temp.expect('T31 hechos con fecha que no es lunes',
 $q$INSERT INTO session_facts (scenario_version_id, week_start, is_first_session, outcome_reached, evaluations_completed)
    VALUES ('00000000-0000-0000-0000-000000000011', '2026-11-03', true, false, false)$q$, '23514');

-- ------------------------- Privilegios -------------------------------
SET ROLE nukyro_api;
INSERT INTO nukyro.consent_events (account_id, consent_type, granted, source)
VALUES ('00000000-0000-0000-0000-00000000ac01', 'newsletter', true, 'registration');
SELECT pg_temp.expect('T32 api no puede modificar hechos', $q$UPDATE nukyro.session_facts SET is_first_session = false$q$, '42501');
SELECT pg_temp.expect('T32b api no inserta hechos (ni con RETURNING)',
 $q$INSERT INTO nukyro.session_facts (scenario_version_id, week_start, is_first_session, outcome_reached, evaluations_completed)
    VALUES ('00000000-0000-0000-0000-000000000011', date_trunc('week', now())::date, true, true, true) RETURNING id$q$, '42501');
SELECT pg_temp.expect('T33 api no escribe la bitácora del panel', $q$INSERT INTO nukyro.admin_audit_log (admin_user_id, action, entity_type) VALUES (gen_random_uuid(), 'x', 'y')$q$, '42501');
SELECT pg_temp.expect('T34 api no puede leer hechos', $q$SELECT count(*) FROM nukyro.session_facts$q$, '42501');
SELECT pg_temp.expect('T34b F4 api no modifica contenido', $q$UPDATE nukyro.nodes SET title = 'x' WHERE version_id = '00000000-0000-0000-0000-000000000012'$q$, '42501');
SELECT pg_temp.expect('T34c F4 api no lee solicitudes ARCO', $q$SELECT count(*) FROM nukyro.arco_requests$q$, '42501');
SELECT pg_temp.expect('T34d historial de consentimientos sin edición', $q$UPDATE nukyro.consent_events SET granted = false$q$, '42501');
RESET ROLE;

SET ROLE nukyro_admin;
INSERT INTO nukyro.admin_audit_log (admin_user_id, action, entity_type) VALUES ('00000000-0000-0000-0000-00000000ad01', 'publish', 'scenario_version');
UPDATE nukyro.nodes SET title = 'editado en borrador' WHERE id = '00000000-0000-0000-0000-000000000142';
SELECT pg_temp.expect('T34e admin no borra la bitácora', $q$DELETE FROM nukyro.admin_audit_log$q$, '42501');
SELECT pg_temp.expect('T34f admin no modifica sesiones', $q$DELETE FROM nukyro.sessions$q$, '42501');
SELECT pg_temp.expect('T34g admin no lee hechos', $q$SELECT count(*) FROM nukyro.session_facts$q$, '42501');
SELECT pg_temp.ok('T34h admin lee datos para ARCO de acceso', (SELECT count(*) FROM nukyro.sessions) >= 1);
RESET ROLE;

SET ROLE nukyro_analytics;
SELECT pg_temp.expect('T35 analítica no lee datos personales', $q$SELECT count(*) FROM nukyro.participants$q$, '42501');
SELECT pg_temp.expect('T36 analítica no lee filas de hechos', $q$SELECT count(*) FROM nukyro.session_facts$q$, '42501');
SELECT pg_temp.ok('T36b analítica solo recibe el agregado, suprimido con menos de 10',
 (SELECT suppressed AND first_sessions IS NULL
    FROM nukyro.report_session_summary('00000000-0000-0000-0000-000000000011')));
RESET ROLE;

-- Cascada ejecutada por el rol de tareas (RF-080, ADR-004)
-- Etapa 2 (ADR-007): la misma cascada, ahora mediante las funciones del owner
UPDATE participants SET last_activity_at = now() - interval '40 days' WHERE id = '00000000-0000-0000-0000-00000000aa01';
SET ROLE nukyro_jobs;
SELECT pg_temp.ok('T38a caducidad: expira solo al anónimo inactivo',
 nukyro.expire_anonymous_participants(now() - interval '30 days') = 1);
SELECT pg_temp.ok('T38b bloqueo de la cuenta (archiva sus hechos)',
 nukyro.block_account('00000000-0000-0000-0000-00000000ac01', 'user_request', now() + interval '1 hour'));
SELECT pg_temp.ok('T38c purga de la cuenta vencida',
 nukyro.purge_due_account('00000000-0000-0000-0000-00000000ac01', now() + interval '1 hour'));
SELECT pg_temp.expect('T37 tareas no pueden modificar contenido',
 $q$UPDATE nukyro.nodes SET title = 'x' WHERE version_id = '00000000-0000-0000-0000-000000000012'$q$, '42501');
RESET ROLE;
SELECT pg_temp.ok('T38 cascada: sin rastro de los participantes borrados',
     NOT EXISTS (SELECT 1 FROM sessions WHERE participant_id IN ('00000000-0000-0000-0000-00000000aa01', '00000000-0000-0000-0000-00000000aa03'))
 AND NOT EXISTS (SELECT 1 FROM session_decisions WHERE session_id = '00000000-0000-0000-0000-000000005e01')
 AND NOT EXISTS (SELECT 1 FROM session_events WHERE session_id = '00000000-0000-0000-0000-000000005e01')
 AND NOT EXISTS (SELECT 1 FROM assessment_attempts WHERE session_id = '00000000-0000-0000-0000-000000005e01')
 AND NOT EXISTS (SELECT 1 FROM document_acceptances WHERE participant_id = '00000000-0000-0000-0000-00000000aa01')
 AND NOT EXISTS (SELECT 1 FROM participants WHERE account_id IS NOT NULL)
 AND NOT EXISTS (SELECT 1 FROM consent_events));
SELECT pg_temp.ok('T39 los hechos archivados por la función sobreviven a los borrados',
 (SELECT count(*) FROM session_facts) = 3 AND (SELECT count(*) FROM decision_facts) = 1);

-- ------------------------- Ciclo de versiones ------------------------
SELECT pg_temp.expect('T40 contenido publicado no se borra por cascada',
 $q$DELETE FROM scenarios WHERE id = '00000000-0000-0000-0000-000000000001'$q$, '23503');
DELETE FROM scenario_versions WHERE id = '00000000-0000-0000-0000-000000000012';
SELECT pg_temp.ok('T41 borrar un borrador elimina su contenido en cascada',
 NOT EXISTS (SELECT 1 FROM nodes WHERE version_id = '00000000-0000-0000-0000-000000000012'));
UPDATE scenario_versions SET status = 'retired', retired_at = now() WHERE id = '00000000-0000-0000-0000-000000000011';
SELECT pg_temp.ok('T42 published → retired permitido', (SELECT status FROM scenario_versions WHERE id = '00000000-0000-0000-0000-000000000011') = 'retired');
SELECT pg_temp.expect('T43 sesión nueva sobre versión retirada',
 $q$INSERT INTO sessions (participant_id, scenario_version_id, current_node_id, self_reported_first, has_prior_session)
    VALUES ('00000000-0000-0000-0000-00000000aa02', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000041', true, false)$q$, '23514');
SELECT pg_temp.ok('T44 la sesión en curso sigue en su versión retirada (RN-15)',
 EXISTS (SELECT 1 FROM sessions WHERE id = '00000000-0000-0000-0000-000000005e02' AND scenario_version_id = '00000000-0000-0000-0000-000000000011'));

\echo '== Todas las pruebas pasaron =='
