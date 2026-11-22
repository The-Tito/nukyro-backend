-- Escenario DEMO-ENTRADA, ficticio, solo para el recorrido de entrada (T-10, RF-071).
-- Se aplica como owner tras migrar. Idempotente. No es una migración ni contenido real.
DO $$
DECLARE
    v_scenario  uuid;
    v_version   uuid;
    v_intro     uuid;
    v_decision  uuid;
    v_outcome   uuid;
    v_objective uuid;
BEGIN
    IF EXISTS (SELECT 1 FROM nukyro.scenarios WHERE key = 'DEMO-ENTRADA') THEN
        RETURN;
    END IF;

    INSERT INTO nukyro.scenarios (key, title)
    VALUES ('DEMO-ENTRADA', 'DEMOSTRACIÓN: escenario de entrada')
    RETURNING id INTO v_scenario;

    -- Nace como borrador y se publica al final (el trigger solo admite ese ciclo)
    INSERT INTO nukyro.scenario_versions (scenario_id, version_number, title, introduction)
    VALUES (v_scenario, 1, 'DEMOSTRACIÓN: escenario de entrada', 'DEMOSTRACIÓN, sin validez legal')
    RETURNING id INTO v_version;

    INSERT INTO nukyro.state_variables (version_id, key, label, initial_value, min_value, max_value)
    VALUES (v_version, 'demo_trust', 'Confianza (demostración)', 50, 0, 100);

    INSERT INTO nukyro.learning_objectives (version_id, key, description)
    VALUES (v_version, 'demo_objective', 'DEMOSTRACIÓN: objetivo ficticio')
    RETURNING id INTO v_objective;

    INSERT INTO nukyro.nodes (version_id, key, node_type, title, body, position)
    VALUES (v_version, 'intro', 'intro', 'DEMOSTRACIÓN: inicio', 'Texto ficticio de inicio.', 1)
    RETURNING id INTO v_intro;
    INSERT INTO nukyro.nodes (version_id, key, node_type, title, body, position)
    VALUES (v_version, 'decision', 'decision', 'DEMOSTRACIÓN: decisión', 'Texto ficticio de decisión.', 2)
    RETURNING id INTO v_decision;
    INSERT INTO nukyro.nodes (version_id, key, node_type, title, body, position)
    VALUES (v_version, 'outcome', 'outcome', 'DEMOSTRACIÓN: desenlace', 'Texto ficticio de desenlace.', 3)
    RETURNING id INTO v_outcome;

    UPDATE nukyro.nodes SET default_next_node_id = v_decision WHERE id = v_intro;

    INSERT INTO nukyro.decision_points (node_id, version_id, learning_objective_id, affected_parties)
    VALUES (v_decision, v_version, v_objective, 'DEMOSTRACIÓN: partes ficticias');

    INSERT INTO nukyro.options (version_id, node_id, key, label, next_node_id, position)
    VALUES (v_version, v_decision, 'demo_option', 'DEMOSTRACIÓN: única opción', v_outcome, 1);

    UPDATE nukyro.scenario_versions
       SET status = 'published', published_at = now()
     WHERE id = v_version;
END $$;
