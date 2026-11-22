-- =====================================================================
-- Nukyro · DDL de referencia · PostgreSQL 16
-- Modelo: bd/modelo-datos.md · Decisiones: context/adr/ADR-001..005
-- Este archivo es la referencia del esquema; en el proyecto se traduce
-- a migraciones de Alembic. Ejecutar como nukyro_owner (o superusuario
-- en local).
-- =====================================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS nukyro;
SET search_path = nukyro, public;

-- ---------------------------------------------------------------------
-- Administración
-- ---------------------------------------------------------------------
CREATE TABLE admin_users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_sub   text NOT NULL UNIQUE,
    email         text NOT NULL,
    display_name  text NOT NULL,
    is_active     boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Contenido versionado (ADR-001)
-- Las referencias internas entre elementos de una versión (siguiente nodo,
-- objetivo, reglas, preguntas) son DEFERRABLE INITIALLY DEFERRED: se
-- verifican al COMMIT. Así el borrado en cascada de un borrador no depende
-- del orden de las cascadas, y un nodo referenciado no se borra en silencio
-- (plan H-11).
-- ---------------------------------------------------------------------
CREATE TABLE scenarios (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    key         text NOT NULL UNIQUE,
    title       text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE scenario_versions (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id          uuid NOT NULL REFERENCES scenarios (id) ON DELETE RESTRICT,
    version_number       integer NOT NULL CHECK (version_number > 0),
    status               text NOT NULL DEFAULT 'draft'
                         CHECK (status IN ('draft', 'published', 'retired')),
    based_on_version_id  uuid REFERENCES scenario_versions (id) ON DELETE SET NULL,
    title                text NOT NULL,
    introduction         text NOT NULL DEFAULT '',
    rubric_version       text NOT NULL DEFAULT '1',
    created_by           uuid REFERENCES admin_users (id) ON DELETE SET NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    published_at         timestamptz,
    published_by         uuid REFERENCES admin_users (id) ON DELETE SET NULL,
    retired_at           timestamptz,
    UNIQUE (scenario_id, version_number),
    CHECK ((status = 'draft') = (published_at IS NULL)),
    CHECK ((status = 'retired') = (retired_at IS NOT NULL))
);
-- RN-16: una sola versión publicada y un solo borrador por escenario
CREATE UNIQUE INDEX ux_scenario_versions_one_published
    ON scenario_versions (scenario_id) WHERE status = 'published';
CREATE UNIQUE INDEX ux_scenario_versions_one_draft
    ON scenario_versions (scenario_id) WHERE status = 'draft';

CREATE TABLE learning_objectives (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id   uuid NOT NULL REFERENCES scenario_versions (id) ON DELETE CASCADE,
    key          text NOT NULL,
    description  text NOT NULL,
    position     integer NOT NULL DEFAULT 0,
    UNIQUE (version_id, key),
    UNIQUE (version_id, id)
);

CREATE TABLE state_variables (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id       uuid NOT NULL REFERENCES scenario_versions (id) ON DELETE CASCADE,
    key              text NOT NULL,
    label            text NOT NULL,
    indicator_label  text,            -- indicador narrativo visible (RF-035); nulo = interno
    initial_value    integer NOT NULL,
    min_value        integer,
    max_value        integer,
    UNIQUE (version_id, key),
    UNIQUE (version_id, id),
    CHECK (min_value IS NULL OR initial_value >= min_value),
    CHECK (max_value IS NULL OR initial_value <= max_value)
);

CREATE TABLE nodes (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id            uuid NOT NULL REFERENCES scenario_versions (id) ON DELETE CASCADE,
    key                   text NOT NULL,
    node_type             text NOT NULL
                          CHECK (node_type IN ('intro', 'info', 'decision', 'event', 'outcome')),
    title                 text NOT NULL,
    body                  text NOT NULL,
    project_phase         text CHECK (project_phase IN ('requirements', 'design', 'development',
                                                        'testing', 'delivery', 'incident_response')),
    default_next_node_id  uuid,
    position              integer NOT NULL DEFAULT 0,
    UNIQUE (version_id, key),
    UNIQUE (version_id, id),
    FOREIGN KEY (version_id, default_next_node_id) REFERENCES nodes (version_id, id) DEFERRABLE INITIALLY DEFERRED,
    CHECK (node_type <> 'outcome' OR default_next_node_id IS NULL)
);

CREATE TABLE decision_points (
    node_id                 uuid PRIMARY KEY,
    version_id              uuid NOT NULL,
    requires_justification  boolean NOT NULL DEFAULT false,
    evaluated_for_h05       boolean NOT NULL DEFAULT false,
    min_correct_reasons     smallint NOT NULL DEFAULT 1 CHECK (min_correct_reasons >= 0),
    learning_objective_id   uuid NOT NULL,
    affected_parties        text NOT NULL,          -- OR-05
    UNIQUE (version_id, node_id),
    FOREIGN KEY (version_id, node_id) REFERENCES nodes (version_id, id) ON DELETE CASCADE,
    FOREIGN KEY (version_id, learning_objective_id) REFERENCES learning_objectives (version_id, id) DEFERRABLE INITIALLY DEFERRED,
    CHECK (NOT evaluated_for_h05 OR requires_justification)
);

CREATE TABLE options (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id    uuid NOT NULL,
    node_id       uuid NOT NULL,
    key           text NOT NULL,
    label         text NOT NULL,
    description   text NOT NULL DEFAULT '',
    effects       jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(effects) = 'array'),
    next_node_id  uuid,
    position      integer NOT NULL DEFAULT 0,
    UNIQUE (version_id, key),
    UNIQUE (version_id, id),
    UNIQUE (node_id, id),
    FOREIGN KEY (version_id, node_id) REFERENCES decision_points (version_id, node_id) ON DELETE CASCADE,
    FOREIGN KEY (version_id, next_node_id) REFERENCES nodes (version_id, id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE justification_reasons (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id  uuid NOT NULL,
    node_id     uuid NOT NULL,
    key         text NOT NULL,
    label       text NOT NULL,
    is_correct  boolean NOT NULL,
    position    integer NOT NULL DEFAULT 0,
    UNIQUE (version_id, key),
    UNIQUE (node_id, id),
    FOREIGN KEY (version_id, node_id) REFERENCES decision_points (version_id, node_id) ON DELETE CASCADE
);

CREATE TABLE rules (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id      uuid NOT NULL REFERENCES scenario_versions (id) ON DELETE CASCADE,
    key             text NOT NULL,
    rule_type       text NOT NULL CHECK (rule_type IN ('transition', 'event')),
    from_node_id    uuid NOT NULL,
    condition       jsonb NOT NULL CHECK (jsonb_typeof(condition) = 'object'),
    target_node_id  uuid NOT NULL,
    relation_type   text NOT NULL CHECK (relation_type IN ('causal', 'risk')),
    priority        integer NOT NULL DEFAULT 100,
    explanation     text NOT NULL DEFAULT '',
    UNIQUE (version_id, key),
    UNIQUE (version_id, id),
    FOREIGN KEY (version_id, from_node_id) REFERENCES nodes (version_id, id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (version_id, target_node_id) REFERENCES nodes (version_id, id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE educational_references (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id     uuid NOT NULL REFERENCES scenario_versions (id) ON DELETE CASCADE,
    key            text NOT NULL,
    ref_category   text NOT NULL CHECK (ref_category IN ('ethical', 'professional', 'normative', 'legal')),
    title          text NOT NULL,
    source         text NOT NULL,
    url            text,
    section        text,
    version_label  text,
    jurisdiction   text,
    consulted_on   date,
    valid_from     date,
    UNIQUE (version_id, key),
    UNIQUE (version_id, id),
    CHECK (ref_category <> 'legal' OR jurisdiction IS NOT NULL)   -- RN-08
);

CREATE TABLE decision_references (
    version_id    uuid NOT NULL,
    node_id       uuid NOT NULL,
    reference_id  uuid NOT NULL,
    PRIMARY KEY (node_id, reference_id),
    FOREIGN KEY (version_id, node_id) REFERENCES decision_points (version_id, node_id) ON DELETE CASCADE,
    FOREIGN KEY (version_id, reference_id) REFERENCES educational_references (version_id, id) ON DELETE CASCADE
);

CREATE TABLE feedback_items (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id  uuid NOT NULL,
    node_id     uuid NOT NULL,
    option_id   uuid,
    category    text NOT NULL CHECK (category IN ('ethical', 'professional', 'normative', 'legal')),
    body        text NOT NULL,
    position    integer NOT NULL DEFAULT 0,
    FOREIGN KEY (version_id, node_id) REFERENCES nodes (version_id, id) ON DELETE CASCADE,
    FOREIGN KEY (version_id, option_id) REFERENCES options (version_id, id) ON DELETE CASCADE
);

CREATE TABLE question_sets (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id            uuid NOT NULL REFERENCES scenario_versions (id) ON DELETE CASCADE,
    set_type              text NOT NULL CHECK (set_type IN ('pretest', 'posttest', 'transfer', 'causal')),
    requires_all_answers  boolean NOT NULL DEFAULT true,
    UNIQUE (version_id, set_type),
    UNIQUE (version_id, id)
);

CREATE TABLE questions (
    id                         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id                 uuid NOT NULL,
    question_set_id            uuid NOT NULL,
    key                        text NOT NULL,
    prompt                     text NOT NULL,
    topic                      text NOT NULL,
    learning_objective_id      uuid NOT NULL,      -- RN-11
    assesses_decision_node_id  uuid,               -- OR-05
    requires_node_id           uuid,               -- RF-058: pregunta causal condicionada
    position                   integer NOT NULL DEFAULT 0,
    UNIQUE (version_id, key),
    UNIQUE (version_id, id),
    UNIQUE (question_set_id, id),
    FOREIGN KEY (version_id, question_set_id) REFERENCES question_sets (version_id, id) ON DELETE CASCADE,
    FOREIGN KEY (version_id, learning_objective_id) REFERENCES learning_objectives (version_id, id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (version_id, assesses_decision_node_id) REFERENCES decision_points (version_id, node_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (version_id, requires_node_id) REFERENCES nodes (version_id, id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE question_options (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id   uuid NOT NULL,
    question_id  uuid NOT NULL,
    key          text NOT NULL,
    label        text NOT NULL,
    is_correct   boolean NOT NULL DEFAULT false,
    position     integer NOT NULL DEFAULT 0,
    UNIQUE (question_id, key),
    UNIQUE (question_id, id),
    FOREIGN KEY (version_id, question_id) REFERENCES questions (version_id, id) ON DELETE CASCADE
);
-- RF-009: exactamente una opción correcta como máximo por pregunta
CREATE UNIQUE INDEX ux_question_options_one_correct
    ON question_options (question_id) WHERE is_correct;

-- Inmutabilidad del contenido fuera de borrador (ADR-001, RN-15, RN-17)
CREATE FUNCTION guard_content_version() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_status text;
BEGIN
    SELECT status INTO v_status
      FROM nukyro.scenario_versions
     WHERE id = CASE WHEN TG_OP = 'DELETE' THEN OLD.version_id ELSE NEW.version_id END;
    -- NULL: la versión se está borrando en cascada (solo posible en borrador)
    IF v_status IS NOT NULL AND v_status <> 'draft' THEN
        RAISE EXCEPTION 'La versión % está %; solo se edita contenido en borrador (RN-15/ADR-001)',
            CASE WHEN TG_OP = 'DELETE' THEN OLD.version_id ELSE NEW.version_id END, v_status
            USING ERRCODE = 'check_violation';
    END IF;
    IF TG_OP = 'UPDATE' AND NEW.version_id <> OLD.version_id THEN
        RAISE EXCEPTION 'No se puede mover contenido entre versiones' USING ERRCODE = 'check_violation';
    END IF;
    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;

DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['learning_objectives', 'state_variables', 'nodes', 'decision_points',
                             'options', 'justification_reasons', 'rules', 'educational_references',
                             'decision_references', 'feedback_items', 'question_sets', 'questions',
                             'question_options']
    LOOP
        EXECUTE format('CREATE TRIGGER trg_guard_%1$s BEFORE INSERT OR UPDATE OR DELETE ON nukyro.%1$I
                        FOR EACH ROW EXECUTE FUNCTION nukyro.guard_content_version()', t);
    END LOOP;
END $$;

-- Transiciones válidas de la versión (draft → published → retired)
CREATE FUNCTION guard_version_status() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.status <> 'draft' THEN
            RAISE EXCEPTION 'Solo se puede borrar una versión en borrador (RN-17)' USING ERRCODE = 'check_violation';
        END IF;
        RETURN OLD;
    END IF;
    IF OLD.status = 'draft' THEN
        RETURN NEW;                                   -- borrador: editable o publicable
    ELSIF OLD.status = 'published' AND NEW.status = 'retired'
          AND (NEW.title, NEW.introduction, NEW.rubric_version, NEW.version_number, NEW.published_at)
              IS NOT DISTINCT FROM (OLD.title, OLD.introduction, OLD.rubric_version, OLD.version_number, OLD.published_at) THEN
        RETURN NEW;                                   -- retirar sin cambiar contenido
    END IF;
    RAISE EXCEPTION 'Transición o cambio no permitido en versión % (%→%)', OLD.id, OLD.status, NEW.status
        USING ERRCODE = 'check_violation';
END $$;

CREATE TRIGGER trg_guard_version_status
    BEFORE UPDATE OR DELETE ON scenario_versions
    FOR EACH ROW EXECUTE FUNCTION guard_version_status();

-- ---------------------------------------------------------------------
-- Identidad (ADR-002)
-- ---------------------------------------------------------------------
CREATE TABLE accounts (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_sub        text NOT NULL UNIQUE,
    email              text NOT NULL,
    nickname           text NOT NULL CHECK (char_length(nickname) BETWEEN 1 AND 40),
    newsletter_opt_in  boolean NOT NULL DEFAULT false,
    surveys_opt_in     boolean NOT NULL DEFAULT false,
    status             text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked')),
    blocked_at         timestamptz,
    block_reason       text CHECK (block_reason IN ('user_request', 'inactivity', 'underage', 'terms_breach')),
    deletion_due_at    timestamptz,
    last_login_at      timestamptz NOT NULL DEFAULT now(),
    created_at         timestamptz NOT NULL DEFAULT now(),
    CHECK ((status = 'blocked') = (blocked_at IS NOT NULL AND block_reason IS NOT NULL AND deletion_due_at IS NOT NULL))
);
CREATE INDEX ix_accounts_inactivity ON accounts (last_login_at) WHERE status = 'active';
CREATE INDEX ix_accounts_deletion_due ON accounts (deletion_due_at) WHERE status = 'blocked';

CREATE TABLE participants (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id          uuid UNIQUE REFERENCES accounts (id) ON DELETE CASCADE,
    secret_hash         bytea UNIQUE CHECK (secret_hash IS NULL OR octet_length(secret_hash) = 32),
    exclude_from_stats  boolean NOT NULL DEFAULT false,
    created_at          timestamptz NOT NULL DEFAULT now(),
    last_activity_at    timestamptz NOT NULL DEFAULT now(),
    CHECK (account_id IS NOT NULL OR secret_hash IS NOT NULL)
);
-- RF-080: caducidad de participantes sin cuenta
CREATE INDEX ix_participants_anonymous_activity
    ON participants (last_activity_at) WHERE account_id IS NULL;

CREATE TABLE document_acceptances (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id    uuid NOT NULL REFERENCES participants (id) ON DELETE CASCADE,
    document_type     text NOT NULL CHECK (document_type IN ('age_18_plus', 'privacy_notice', 'terms')),
    document_version  text,
    accepted_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE NULLS NOT DISTINCT (participant_id, document_type, document_version),
    CHECK (document_type = 'age_18_plus' OR document_version IS NOT NULL)
);

-- Historial de consentimientos opcionales (boletín y encuestas): fecha de
-- cada otorgamiento y revocación. accounts guarda solo el valor vigente.
CREATE TABLE consent_events (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id    uuid NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
    consent_type  text NOT NULL CHECK (consent_type IN ('newsletter', 'surveys')),
    granted       boolean NOT NULL,
    source        text NOT NULL CHECK (source IN ('registration', 'settings', 'unsubscribe_link', 'arco_request')),
    occurred_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_consent_events_account ON consent_events (account_id, consent_type, occurred_at);

CREATE TABLE arco_requests (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id               uuid REFERENCES accounts (id) ON DELETE SET NULL,
    requester_email          text NOT NULL,
    right_type               text NOT NULL CHECK (right_type IN ('access', 'rectification', 'cancellation',
                                                                  'opposition', 'revocation', 'limitation')),
    description              text NOT NULL,
    status                   text NOT NULL DEFAULT 'received'
                             CHECK (status IN ('received', 'awaiting_info', 'in_review', 'accepted',
                                               'denied', 'executed', 'withdrawn')),
    received_at              timestamptz NOT NULL DEFAULT now(),
    info_requested_at        timestamptz,
    info_due_on              date,
    response_due_on          date NOT NULL,
    extended                 boolean NOT NULL DEFAULT false,
    extension_reason         text,
    responded_at             timestamptz,
    execution_due_on         date,
    executed_at              timestamptz,
    denial_reason            text,
    identity_doc_key         text,
    identity_doc_deleted_at  timestamptz,
    assigned_admin_id        uuid REFERENCES admin_users (id) ON DELETE SET NULL,
    closed_at                timestamptz,
    CHECK (NOT extended OR extension_reason IS NOT NULL),
    CHECK (status <> 'awaiting_info' OR info_due_on IS NOT NULL),
    CHECK (status <> 'denied' OR denial_reason IS NOT NULL),
    CHECK (status <> 'executed' OR executed_at IS NOT NULL),
    CHECK ((status IN ('denied', 'executed', 'withdrawn')) = (closed_at IS NOT NULL)),
    CHECK (closed_at IS NULL OR identity_doc_key IS NULL)          -- RF-086
);
CREATE INDEX ix_arco_requests_open ON arco_requests (status, response_due_on) WHERE closed_at IS NULL;
CREATE INDEX ix_arco_requests_closed ON arco_requests (closed_at) WHERE closed_at IS NOT NULL;   -- purga a 12 meses

-- ---------------------------------------------------------------------
-- Simulación (ADR-003)
-- ---------------------------------------------------------------------
CREATE TABLE sessions (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id        uuid NOT NULL REFERENCES participants (id) ON DELETE CASCADE,
    scenario_version_id   uuid NOT NULL REFERENCES scenario_versions (id) ON DELETE RESTRICT,
    current_node_id       uuid NOT NULL,
    outcome_node_id       uuid,
    started_at            timestamptz NOT NULL DEFAULT now(),
    pretest_completed_at  timestamptz,
    outcome_reached_at    timestamptz,
    completed_at          timestamptz,
    last_activity_at      timestamptz NOT NULL DEFAULT now(),
    self_reported_first   boolean NOT NULL,
    has_prior_session     boolean NOT NULL,
    is_first_session      boolean GENERATED ALWAYS AS (self_reported_first AND NOT has_prior_session) STORED,
    survey_answered       boolean NOT NULL DEFAULT false,
    facts_written_at      timestamptz,
    UNIQUE (id, scenario_version_id),
    FOREIGN KEY (scenario_version_id, current_node_id) REFERENCES nodes (version_id, id),
    FOREIGN KEY (scenario_version_id, outcome_node_id) REFERENCES nodes (version_id, id),
    CHECK (pretest_completed_at IS NULL OR pretest_completed_at >= started_at),
    CHECK (outcome_reached_at IS NULL OR (pretest_completed_at IS NOT NULL AND outcome_reached_at >= pretest_completed_at)),
    CHECK (completed_at IS NULL OR (outcome_reached_at IS NOT NULL AND completed_at >= outcome_reached_at)),
    CHECK ((outcome_reached_at IS NULL) = (outcome_node_id IS NULL))
);
CREATE INDEX ix_sessions_participant ON sessions (participant_id, scenario_version_id, started_at);

-- Las sesiones nuevas solo usan la versión publicada (RN-15)
CREATE FUNCTION guard_session_version() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF (SELECT status FROM nukyro.scenario_versions WHERE id = NEW.scenario_version_id) <> 'published' THEN
        RAISE EXCEPTION 'Una sesión nueva solo puede usar la versión publicada (RN-15)'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_guard_session_version
    BEFORE INSERT ON sessions FOR EACH ROW EXECUTE FUNCTION guard_session_version();

CREATE TABLE session_steps (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id           uuid NOT NULL,
    scenario_version_id  uuid NOT NULL,
    node_id              uuid NOT NULL,
    seq                  integer NOT NULL CHECK (seq > 0),
    entered_at           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (session_id, seq),
    FOREIGN KEY (session_id, scenario_version_id) REFERENCES sessions (id, scenario_version_id) ON DELETE CASCADE,
    FOREIGN KEY (scenario_version_id, node_id) REFERENCES nodes (version_id, id)
);

CREATE TABLE session_decisions (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id             uuid NOT NULL,
    scenario_version_id    uuid NOT NULL,
    node_id                uuid NOT NULL,
    option_id              uuid NOT NULL,
    decided_at             timestamptz NOT NULL DEFAULT now(),
    justification_correct  boolean,
    UNIQUE (session_id, node_id),                                   -- RN-14
    UNIQUE (id, node_id),
    UNIQUE (id, session_id),
    FOREIGN KEY (session_id, scenario_version_id) REFERENCES sessions (id, scenario_version_id) ON DELETE CASCADE,
    FOREIGN KEY (scenario_version_id, node_id) REFERENCES decision_points (version_id, node_id),   -- RN-02
    FOREIGN KEY (node_id, option_id) REFERENCES options (node_id, id)                              -- RN-03
);

CREATE TABLE session_decision_reasons (
    session_decision_id  uuid NOT NULL,
    node_id              uuid NOT NULL,
    reason_id            uuid NOT NULL,
    PRIMARY KEY (session_decision_id, reason_id),
    FOREIGN KEY (session_decision_id, node_id) REFERENCES session_decisions (id, node_id) ON DELETE CASCADE,
    FOREIGN KEY (node_id, reason_id) REFERENCES justification_reasons (node_id, id)
);

CREATE TABLE session_variables (
    session_id           uuid NOT NULL,
    scenario_version_id  uuid NOT NULL,
    variable_id          uuid NOT NULL,
    value                integer NOT NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, variable_id),
    FOREIGN KEY (session_id, scenario_version_id) REFERENCES sessions (id, scenario_version_id) ON DELETE CASCADE,
    FOREIGN KEY (scenario_version_id, variable_id) REFERENCES state_variables (version_id, id)
);

CREATE TABLE session_effects (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_decision_id  uuid NOT NULL,
    session_id           uuid NOT NULL,
    variable_id          uuid NOT NULL,
    old_value            integer NOT NULL,
    new_value            integer NOT NULL,
    FOREIGN KEY (session_decision_id, session_id) REFERENCES session_decisions (id, session_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id, variable_id) REFERENCES session_variables (session_id, variable_id) ON DELETE CASCADE
);

CREATE TABLE session_events (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id           uuid NOT NULL,
    scenario_version_id  uuid NOT NULL,
    rule_id              uuid NOT NULL,
    triggered_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (session_id, rule_id),
    UNIQUE (id, session_id),
    FOREIGN KEY (session_id, scenario_version_id) REFERENCES sessions (id, scenario_version_id) ON DELETE CASCADE,
    FOREIGN KEY (scenario_version_id, rule_id) REFERENCES rules (version_id, id)
);

CREATE TABLE session_event_causes (
    session_event_id     uuid NOT NULL,
    session_id           uuid NOT NULL,
    session_decision_id  uuid NOT NULL,
    PRIMARY KEY (session_event_id, session_decision_id),
    FOREIGN KEY (session_event_id, session_id) REFERENCES session_events (id, session_id) ON DELETE CASCADE,
    FOREIGN KEY (session_decision_id, session_id) REFERENCES session_decisions (id, session_id) ON DELETE CASCADE
);

CREATE TABLE assessment_attempts (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id           uuid NOT NULL,
    scenario_version_id  uuid NOT NULL,
    question_set_id      uuid NOT NULL,
    started_at           timestamptz NOT NULL DEFAULT now(),
    submitted_at         timestamptz,
    answered_count       smallint NOT NULL DEFAULT 0 CHECK (answered_count >= 0),
    correct_count        smallint NOT NULL DEFAULT 0 CHECK (correct_count >= 0),
    score                numeric(5,2) CHECK (score BETWEEN 0 AND 100),
    UNIQUE (session_id, question_set_id),                            -- RN-19
    UNIQUE (id, question_set_id),
    FOREIGN KEY (session_id, scenario_version_id) REFERENCES sessions (id, scenario_version_id) ON DELETE CASCADE,
    FOREIGN KEY (scenario_version_id, question_set_id) REFERENCES question_sets (version_id, id),
    CHECK (correct_count <= answered_count),
    CHECK (score IS NULL OR submitted_at IS NOT NULL)
);

CREATE TABLE assessment_answers (
    attempt_id       uuid NOT NULL,
    question_set_id  uuid NOT NULL,
    question_id      uuid NOT NULL,
    option_id        uuid NOT NULL,
    answered_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (attempt_id, question_id),
    FOREIGN KEY (attempt_id, question_set_id) REFERENCES assessment_attempts (id, question_set_id) ON DELETE CASCADE,
    FOREIGN KEY (question_set_id, question_id) REFERENCES questions (question_set_id, id),
    FOREIGN KEY (question_id, option_id) REFERENCES question_options (question_id, id)
);

-- ---------------------------------------------------------------------
-- Estadísticas anónimas (ADR-004): sin sesión, participante ni cuenta
-- ---------------------------------------------------------------------
CREATE TABLE session_facts (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_version_id    uuid NOT NULL REFERENCES scenario_versions (id) ON DELETE RESTRICT,
    week_start             date NOT NULL CHECK (extract(isodow FROM week_start) = 1),
    closure_reason         text NOT NULL CHECK (closure_reason IN ('completed', 'expired', 'account_deleted',
                                                                   'self_deleted', 'arco')),
    is_first_session       boolean NOT NULL,
    pretest_score          numeric(5,2) CHECK (pretest_score BETWEEN 0 AND 100),
    posttest_score         numeric(5,2) CHECK (posttest_score BETWEEN 0 AND 100),
    transfer_correct       smallint,
    transfer_total         smallint,
    causal_correct         smallint,
    causal_total           smallint,
    justification_correct  smallint,
    justification_total    smallint,
    outcome_reached        boolean NOT NULL,
    outcome_key            text,
    evaluations_completed  boolean NOT NULL,
    duration_bucket_min    smallint CHECK (duration_bucket_min >= 0 AND duration_bucket_min % 5 = 0),
    CHECK (transfer_correct IS NULL OR transfer_correct <= transfer_total),
    CHECK (causal_correct IS NULL OR causal_correct <= causal_total),
    CHECK (justification_correct IS NULL OR justification_correct <= justification_total)
);

CREATE TABLE decision_facts (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_version_id  uuid NOT NULL REFERENCES scenario_versions (id) ON DELETE RESTRICT,
    week_start           date NOT NULL CHECK (extract(isodow FROM week_start) = 1),
    decision_key         text NOT NULL,
    option_key           text NOT NULL,
    is_first_session     boolean NOT NULL
);

CREATE TABLE survey_responses (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_version_id   uuid NOT NULL REFERENCES scenario_versions (id) ON DELETE RESTRICT,
    week_start            date NOT NULL CHECK (extract(isodow FROM week_start) = 1),
    is_first_session      boolean NOT NULL,
    usefulness            smallint NOT NULL CHECK (usefulness BETWEEN 1 AND 5),       -- H07
    clarity               smallint CHECK (clarity BETWEEN 1 AND 5),
    decision_impact       smallint CHECK (decision_impact BETWEEN 1 AND 5),
    causal_understanding  smallint CHECK (causal_understanding BETWEEN 1 AND 5),
    summary_usefulness    smallint CHECK (summary_usefulness BETWEEN 1 AND 5),
    would_repeat          smallint CHECK (would_repeat BETWEEN 1 AND 5)
);

-- ---------------------------------------------------------------------
-- Bitácora del panel (RF-087): sin llaves foráneas, solo inserción
-- ---------------------------------------------------------------------
CREATE TABLE admin_audit_log (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at    timestamptz NOT NULL DEFAULT now(),
    admin_user_id  uuid NOT NULL,
    action         text NOT NULL,
    entity_type    text NOT NULL,
    entity_id      uuid,
    detail         jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX ix_admin_audit_log_occurred ON admin_audit_log (occurred_at);

COMMIT;

-- ---------------------------------------------------------------------
-- Roles y privilegios (§6 del modelo). Roles de grupo sin LOGIN; los
-- usuarios de conexión se crean por entorno y heredan de ellos.
-- nukyro_api (participantes) y nukyro_admin (panel) están separados.
-- ---------------------------------------------------------------------
BEGIN;
DO $$
DECLARE r text;
BEGIN
    FOREACH r IN ARRAY ARRAY['nukyro_api', 'nukyro_admin', 'nukyro_jobs', 'nukyro_analytics'] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN', r);
        END IF;
    END LOOP;
END $$;

REVOKE ALL ON SCHEMA nukyro FROM PUBLIC;
GRANT USAGE ON SCHEMA nukyro TO nukyro_api, nukyro_admin, nukyro_jobs, nukyro_analytics;

-- API de participantes: contenido de solo lectura; identidad y simulación propias
GRANT SELECT ON
    nukyro.scenarios, nukyro.scenario_versions, nukyro.learning_objectives, nukyro.state_variables,
    nukyro.nodes, nukyro.decision_points, nukyro.options, nukyro.justification_reasons, nukyro.rules,
    nukyro.educational_references, nukyro.decision_references, nukyro.feedback_items,
    nukyro.question_sets, nukyro.questions, nukyro.question_options
TO nukyro_api;
GRANT SELECT, INSERT, UPDATE, DELETE ON
    nukyro.accounts, nukyro.participants, nukyro.document_acceptances, nukyro.sessions,
    nukyro.session_steps, nukyro.session_decisions, nukyro.session_decision_reasons,
    nukyro.session_variables, nukyro.session_effects, nukyro.session_events,
    nukyro.session_event_causes, nukyro.assessment_attempts, nukyro.assessment_answers
TO nukyro_api;
GRANT SELECT, INSERT ON nukyro.consent_events TO nukyro_api;
GRANT INSERT ON nukyro.session_facts, nukyro.decision_facts, nukyro.survey_responses TO nukyro_api;

-- Panel de administración: contenido, ARCO y bitácora; datos de participantes
-- solo para atender ARCO (consultar, rectificar, oponerse, bloquear)
GRANT SELECT, INSERT, UPDATE, DELETE ON
    nukyro.admin_users, nukyro.scenarios, nukyro.scenario_versions, nukyro.learning_objectives,
    nukyro.state_variables, nukyro.nodes, nukyro.decision_points, nukyro.options,
    nukyro.justification_reasons, nukyro.rules, nukyro.educational_references,
    nukyro.decision_references, nukyro.feedback_items, nukyro.question_sets, nukyro.questions,
    nukyro.question_options
TO nukyro_admin;
GRANT SELECT, INSERT, UPDATE ON nukyro.arco_requests TO nukyro_admin;
GRANT SELECT, UPDATE ON nukyro.accounts, nukyro.participants TO nukyro_admin;
GRANT SELECT, INSERT ON nukyro.consent_events TO nukyro_admin;
GRANT SELECT ON
    nukyro.document_acceptances, nukyro.sessions, nukyro.session_steps, nukyro.session_decisions,
    nukyro.session_decision_reasons, nukyro.session_variables, nukyro.session_effects,
    nukyro.session_events, nukyro.session_event_causes, nukyro.assessment_attempts,
    nukyro.assessment_answers
TO nukyro_admin;
GRANT SELECT, INSERT ON nukyro.admin_audit_log TO nukyro_admin;

-- Tareas programadas (caducidad, purga de cuentas, solicitudes ARCO y bitácora)
GRANT SELECT ON ALL TABLES IN SCHEMA nukyro TO nukyro_jobs;
GRANT UPDATE ON nukyro.accounts, nukyro.sessions TO nukyro_jobs;
GRANT DELETE ON nukyro.participants, nukyro.accounts, nukyro.admin_audit_log, nukyro.arco_requests TO nukyro_jobs;
GRANT INSERT ON nukyro.session_facts TO nukyro_jobs;

-- Analítica: solo hechos anónimos y catálogo de versiones
GRANT SELECT ON nukyro.session_facts, nukyro.decision_facts, nukyro.survey_responses,
                nukyro.scenarios, nukyro.scenario_versions TO nukyro_analytics;
COMMIT;
