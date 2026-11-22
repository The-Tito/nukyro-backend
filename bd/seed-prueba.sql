-- =====================================================================
-- Nukyro · Datos mínimos de prueba (no son contenido real del escenario)
-- v1 publicada con 1 decisión; v2 en borrador para pruebas entre versiones.
-- UUID fijos para que las pruebas los referencien.
-- =====================================================================
BEGIN;
SET search_path = nukyro, public;

INSERT INTO admin_users (id, cognito_sub, email, display_name)
VALUES ('00000000-0000-0000-0000-00000000ad01', 'cognito-admin-1', 'admin@example.test', 'Admin de prueba');

INSERT INTO scenarios (id, key, title)
VALUES ('00000000-0000-0000-0000-000000000001', 'BECAS', 'Plataforma de becas universitarias');

-- ---------------- Versión 1 (se publica al final) ----------------
INSERT INTO scenario_versions (id, scenario_id, version_number, title, introduction, created_by)
VALUES ('00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000001', 1,
        'Becas v1', 'Introducción de prueba', '00000000-0000-0000-0000-00000000ad01');

INSERT INTO learning_objectives (id, version_id, key, description)
VALUES ('00000000-0000-0000-0000-000000000021', '00000000-0000-0000-0000-000000000011', 'OBJ-1',
        'Identificar riesgos de privacidad en datos de aspirantes');

INSERT INTO state_variables (id, version_id, key, label, indicator_label, initial_value, min_value, max_value) VALUES
('00000000-0000-0000-0000-000000000031', '00000000-0000-0000-0000-000000000011', 'privacy',  'Privacidad', 'Confianza de los aspirantes', 3, 0, 5),
('00000000-0000-0000-0000-000000000032', '00000000-0000-0000-0000-000000000011', 'delivery', 'Entrega',    'Avance del proyecto',         3, 0, 5);

INSERT INTO nodes (id, version_id, key, node_type, title, body, project_phase) VALUES
('00000000-0000-0000-0000-000000000041', '00000000-0000-0000-0000-000000000011', 'INTRO', 'intro',    'Inicio',       'Contexto', 'requirements'),
('00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000011', 'D01',   'decision', 'Datos reales', 'Dilema',   'development'),
('00000000-0000-0000-0000-000000000043', '00000000-0000-0000-0000-000000000011', 'EV1',   'event',    'Fuga',         'Evento',   'incident_response'),
('00000000-0000-0000-0000-000000000044', '00000000-0000-0000-0000-000000000011', 'OUT1',  'outcome',  'Desenlace 1',  'Final 1',  'delivery'),
('00000000-0000-0000-0000-000000000045', '00000000-0000-0000-0000-000000000011', 'OUT2',  'outcome',  'Desenlace 2',  'Final 2',  'delivery');
UPDATE nodes SET default_next_node_id = '00000000-0000-0000-0000-000000000042' WHERE id = '00000000-0000-0000-0000-000000000041';
UPDATE nodes SET default_next_node_id = '00000000-0000-0000-0000-000000000044' WHERE id = '00000000-0000-0000-0000-000000000043';
UPDATE nodes SET default_next_node_id = '00000000-0000-0000-0000-000000000045' WHERE id = '00000000-0000-0000-0000-000000000042';

INSERT INTO decision_points (node_id, version_id, requires_justification, evaluated_for_h05, min_correct_reasons,
                             learning_objective_id, affected_parties)
VALUES ('00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000011', true, true, 1,
        '00000000-0000-0000-0000-000000000021', 'Aspirantes a beca; equipo de desarrollo');

INSERT INTO options (id, version_id, node_id, key, label, effects, next_node_id) VALUES
('00000000-0000-0000-0000-000000000051', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000042',
 'D01-A', 'Usar datos reales para probar', '[{"variable_key":"privacy","op":"add","value":-2},{"variable_key":"delivery","op":"add","value":1}]', NULL),
('00000000-0000-0000-0000-000000000052', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000042',
 'D01-B', 'Generar datos ficticios', '[{"variable_key":"privacy","op":"add","value":1}]', NULL);

INSERT INTO justification_reasons (id, version_id, node_id, key, label, is_correct) VALUES
('00000000-0000-0000-0000-000000000061', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000042', 'D01-R1', 'Protege a los aspirantes', true),
('00000000-0000-0000-0000-000000000062', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000042', 'D01-R2', 'Es más rápido', false);

INSERT INTO rules (id, version_id, key, rule_type, from_node_id, condition, target_node_id, relation_type, explanation)
VALUES ('00000000-0000-0000-0000-000000000071', '00000000-0000-0000-0000-000000000011', 'RU-1', 'transition',
        '00000000-0000-0000-0000-000000000042', '{"all":[{"var":"privacy","lt":2}]}',
        '00000000-0000-0000-0000-000000000043', 'causal', 'Usar datos reales expuso a los aspirantes');

INSERT INTO educational_references (id, version_id, key, ref_category, title, source, jurisdiction, section)
VALUES ('00000000-0000-0000-0000-000000000081', '00000000-0000-0000-0000-000000000011', 'REF-14', 'legal',
        'LFPDPPP', 'Cámara de Diputados', 'México', 'Art. 6');
INSERT INTO decision_references (version_id, node_id, reference_id)
VALUES ('00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000081');
INSERT INTO feedback_items (version_id, node_id, option_id, category, body)
VALUES ('00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000051',
        'legal', 'Tratar datos reales sin finalidad informada aumenta el riesgo.');

INSERT INTO question_sets (id, version_id, set_type) VALUES
('00000000-0000-0000-0000-000000000091', '00000000-0000-0000-0000-000000000011', 'pretest'),
('00000000-0000-0000-0000-000000000092', '00000000-0000-0000-0000-000000000011', 'causal');
INSERT INTO questions (id, version_id, question_set_id, key, prompt, topic, learning_objective_id, assesses_decision_node_id, requires_node_id) VALUES
('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000091',
 'PRE-1', '¿Qué dato es personal?', 'privacidad', '00000000-0000-0000-0000-000000000021', '00000000-0000-0000-0000-000000000042', NULL),
('00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000092',
 'CAU-1', '¿Qué causó la fuga?', 'privacidad', '00000000-0000-0000-0000-000000000021', NULL, '00000000-0000-0000-0000-000000000043');
INSERT INTO question_options (id, version_id, question_id, key, label, is_correct) VALUES
('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-0000000000a1', 'A', 'CURP', true),
('00000000-0000-0000-0000-0000000000b2', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-0000000000a1', 'B', 'Color favorito', false),
('00000000-0000-0000-0000-0000000000b3', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-0000000000a2', 'A', 'Usar datos reales', true),
('00000000-0000-0000-0000-0000000000b4', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-0000000000a2', 'B', 'El clima', false);

UPDATE scenario_versions
   SET status = 'published', published_at = now(), published_by = '00000000-0000-0000-0000-00000000ad01'
 WHERE id = '00000000-0000-0000-0000-000000000011';

-- ---------------- Versión 2 (borrador) ----------------
INSERT INTO scenario_versions (id, scenario_id, version_number, title, based_on_version_id)
VALUES ('00000000-0000-0000-0000-000000000012', '00000000-0000-0000-0000-000000000001', 2, 'Becas v2',
        '00000000-0000-0000-0000-000000000011');
INSERT INTO learning_objectives (id, version_id, key, description)
VALUES ('00000000-0000-0000-0000-000000000121', '00000000-0000-0000-0000-000000000012', 'OBJ-1', 'Objetivo v2');
INSERT INTO state_variables (id, version_id, key, label, initial_value)
VALUES ('00000000-0000-0000-0000-000000000131', '00000000-0000-0000-0000-000000000012', 'privacy', 'Privacidad v2', 3);
INSERT INTO nodes (id, version_id, key, node_type, title, body)
VALUES ('00000000-0000-0000-0000-000000000142', '00000000-0000-0000-0000-000000000012', 'D01', 'decision', 'Datos reales v2', 'Dilema v2');
INSERT INTO decision_points (node_id, version_id, learning_objective_id, affected_parties)
VALUES ('00000000-0000-0000-0000-000000000142', '00000000-0000-0000-0000-000000000012', '00000000-0000-0000-0000-000000000121', 'Aspirantes');
INSERT INTO options (id, version_id, node_id, key, label)
VALUES ('00000000-0000-0000-0000-000000000151', '00000000-0000-0000-0000-000000000012', '00000000-0000-0000-0000-000000000142', 'D01-A', 'Opción v2');
INSERT INTO justification_reasons (id, version_id, node_id, key, label, is_correct)
VALUES ('00000000-0000-0000-0000-000000000161', '00000000-0000-0000-0000-000000000012', '00000000-0000-0000-0000-000000000142', 'D01-R1', 'Razón v2', true);

COMMIT;
