-- Preparación de las pruebas de caja negra de la simulación (T-07). SOLO se usa con el perfil test.
-- Siembra dos escenarios ficticios con el mismo contenido (variable p entre 0 y 5, valor inicial 3):
--   T07-NEGRO          el pre-test se marca completado al crear la sesión (E4 lo califica; aquí no).
--   T07-NEGRO-PRETEST  el pre-test queda pendiente (RF-016).
-- Recorrido: intro, INFO, D1 (A: p-2, B: p+1; razones R1 correcta y R2 incorrecta), D2 (C: p-2,
-- D: p+1), EVR (evento en la ruta) y BUENO. Al salir de D2: evento EV si p<2; MALO si p<=1.
-- Idempotente. Como owner, tras migrar y sembrar la entrada.
CREATE OR REPLACE FUNCTION nukyro.t07_negro_mark_pretest() RETURNS trigger
LANGUAGE plpgsql AS $f$
BEGIN
    NEW.pretest_completed_at := NEW.started_at;
    RETURN NEW;
END $f$;

DO $$
DECLARE
    v_key       text;
    v_scenario  uuid;
    v_version   uuid;
    v_objective uuid;
    n           jsonb;
    k           text;
    t           text;
    d           uuid;
BEGIN
    FOREACH v_key IN ARRAY ARRAY['T07-NEGRO', 'T07-NEGRO-PRETEST'] LOOP
        IF EXISTS (SELECT 1 FROM nukyro.scenarios WHERE key = v_key) THEN CONTINUE; END IF;
        INSERT INTO nukyro.scenarios (key, title) VALUES (v_key, v_key || ' DEMOSTRACIÓN')
        RETURNING id INTO v_scenario;
        INSERT INTO nukyro.scenario_versions (scenario_id, version_number, title, introduction)
        VALUES (v_scenario, 1, v_key || ' DEMOSTRACIÓN', 'DEMOSTRACIÓN, sin validez legal')
        RETURNING id INTO v_version;
        INSERT INTO nukyro.learning_objectives (version_id, key, description)
        VALUES (v_version, 'LO', 'DEMOSTRACIÓN: objetivo ficticio') RETURNING id INTO v_objective;
        INSERT INTO nukyro.state_variables (version_id, key, label, initial_value, min_value, max_value)
        VALUES (v_version, 'p', 'P', 3, 0, 5);

        n := '{}';
        FOREACH k IN ARRAY ARRAY['intro', 'INFO', 'D1', 'D2', 'EVR', 'EV', 'MALO', 'BUENO'] LOOP
            t := CASE k WHEN 'intro' THEN 'intro' WHEN 'INFO' THEN 'info'
                        WHEN 'D1' THEN 'decision' WHEN 'D2' THEN 'decision'
                        WHEN 'EVR' THEN 'event' WHEN 'EV' THEN 'event' ELSE 'outcome' END;
            INSERT INTO nukyro.nodes (version_id, key, node_type, title, body)
            VALUES (v_version, k, t, 'Título ' || k, 'Texto narrativo ' || k) RETURNING id INTO d;
            n := n || jsonb_build_object(k, d);
        END LOOP;

        UPDATE nukyro.nodes x SET default_next_node_id = (n ->> m.nxt)::uuid
          FROM (VALUES ('intro', 'INFO'), ('INFO', 'D1'), ('D1', 'D2'), ('D2', 'EVR'),
                       ('EVR', 'BUENO')) AS m (cur, nxt)
         WHERE x.version_id = v_version AND x.key = m.cur;

        INSERT INTO nukyro.decision_points
            (node_id, version_id, requires_justification, learning_objective_id, affected_parties)
        VALUES ((n ->> 'D1')::uuid, v_version, true, v_objective, 'DEMOSTRACIÓN'),
               ((n ->> 'D2')::uuid, v_version, false, v_objective, 'DEMOSTRACIÓN');

        INSERT INTO nukyro.options (version_id, node_id, key, label, effects, position)
        VALUES (v_version, (n ->> 'D1')::uuid, 'A', 'Alternativa A',
                '[{"variable_key":"p","op":"add","value":-2}]', 1),
               (v_version, (n ->> 'D1')::uuid, 'B', 'Alternativa B',
                '[{"variable_key":"p","op":"add","value":1}]', 2),
               (v_version, (n ->> 'D2')::uuid, 'C', 'Alternativa C',
                '[{"variable_key":"p","op":"add","value":-2}]', 1),
               (v_version, (n ->> 'D2')::uuid, 'D', 'Alternativa D',
                '[{"variable_key":"p","op":"add","value":1}]', 2);

        INSERT INTO nukyro.justification_reasons (version_id, node_id, key, label, is_correct, position)
        VALUES (v_version, (n ->> 'D1')::uuid, 'R1', 'Razón R1', true, 1),
               (v_version, (n ->> 'D1')::uuid, 'R2', 'Razón R2', false, 2);

        INSERT INTO nukyro.rules (version_id, key, rule_type, from_node_id, condition,
                                  target_node_id, relation_type, priority, explanation)
        VALUES (v_version, 'RULE-EV', 'event', (n ->> 'D2')::uuid,
                '{"var":"p","op":"lt","value":2}', (n ->> 'EV')::uuid, 'causal', 100,
                'Explicación interna'),
               (v_version, 'RULE-MALO', 'transition', (n ->> 'D2')::uuid,
                '{"var":"p","op":"lte","value":1}', (n ->> 'MALO')::uuid, 'causal', 10,
                'Explicación interna');

        INSERT INTO nukyro.question_sets (version_id, set_type) VALUES (v_version, 'pretest');
        UPDATE nukyro.scenario_versions
           SET status = 'published', published_at = now() WHERE id = v_version;

        IF v_key = 'T07-NEGRO' THEN
            -- Solo esta versión: la sesión nace con el pre-test completado (no lo hace la API)
            EXECUTE format(
                'CREATE TRIGGER trg_t07_negro_pretest BEFORE INSERT ON nukyro.sessions '
                'FOR EACH ROW WHEN (NEW.scenario_version_id = %L) '
                'EXECUTE FUNCTION nukyro.t07_negro_mark_pretest()', v_version);
        END IF;
    END LOOP;
END $$;

-- T-13: DEMO-BECAS (la siembra la publica por P12). Para recorrerla por HTTPS sin E4, las sesiones que se
-- declaran de quien ya jugó (self_reported_first = false) nacen con el pre-test completado; las demás no.
DO $$
DECLARE
    v_version uuid;
BEGIN
    SELECT v.id INTO v_version FROM nukyro.scenarios s
      JOIN nukyro.scenario_versions v ON v.scenario_id = s.id
     WHERE s.key = 'DEMO-BECAS' AND v.status = 'published';
    IF v_version IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_t13_becas_pretest') THEN
        EXECUTE format(
            'CREATE TRIGGER trg_t13_becas_pretest BEFORE INSERT ON nukyro.sessions '
            'FOR EACH ROW WHEN (NEW.scenario_version_id = %L AND NOT NEW.self_reported_first) '
            'EXECUTE FUNCTION nukyro.t07_negro_mark_pretest()', v_version);
    END IF;
END $$;
