-- GENERADO por scripts/freeze_schema.py desde bd/schema.sql. No editar a mano.
-- =====================================================================
-- Nukyro · DDL de referencia · PostgreSQL 16
-- Modelo: bd/modelo-datos.md · Decisiones: context/adr/ADR-001..007
-- Este archivo es la referencia del esquema; en el proyecto se traduce
-- a migraciones de Alembic. Se aplica como nukyro_owner, que NO necesita
-- SUPERUSER ni CREATEROLE: si los cuatro roles de grupo ya existen, no los
-- crea; si faltan y quien aplica es superusuario, los crea (idempotente).
-- Etapa 2 (T-09): corrige los defectos 2 a 9; ver bd/pruebas/.
-- =====================================================================


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
    created_by           uuid REFERENCES admin_users (id) ON DELETE RESTRICT,
    created_at           timestamptz NOT NULL DEFAULT now(),
    published_at         timestamptz,
    published_by         uuid REFERENCES admin_users (id) ON DELETE RESTRICT,
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
-- La versión se lee con FOR SHARE: editar y publicar se ordenan. Si otra
-- transacción publica a la vez, la edición espera, relee el estado y falla;
-- si la edición va primero, la publicación espera a que termine. También se
-- valida la versión de origen (OLD) en un UPDATE.
CREATE FUNCTION guard_content_version() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_status text;
    v_old    uuid;
    v_new    uuid;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN v_old := OLD.version_id; END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN v_new := NEW.version_id; END IF;
    IF TG_OP = 'UPDATE' AND v_new <> v_old THEN
        RAISE EXCEPTION 'No se puede mover contenido entre versiones' USING ERRCODE = 'check_violation';
    END IF;
    SELECT status INTO v_status
      FROM nukyro.scenario_versions
     WHERE id = coalesce(v_old, v_new)
       FOR SHARE;
    -- NULL: la versión se está borrando en cascada (solo posible en borrador)
    IF v_status IS NOT NULL AND v_status <> 'draft' THEN
        RAISE EXCEPTION 'La versión % está %; solo se edita contenido en borrador (RN-15/ADR-001)',
            coalesce(v_old, v_new), v_status
            USING ERRCODE = 'check_violation';
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

-- Ciclo de vida de la versión (draft → published → retired), defecto 5:
--  · INSERT: solo borrador, sin fechas ni responsable de publicación o retiro.
--  · draft: pasa a draft o a published y no cambia de escenario.
--  · published → retired: la fila completa debe ser igual salvo status y retired_at.
--  · retired: no cambia (ni una actualización vacía).
CREATE FUNCTION guard_version_status() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.status <> 'draft' OR NEW.published_at IS NOT NULL
           OR NEW.published_by IS NOT NULL OR NEW.retired_at IS NOT NULL THEN
            RAISE EXCEPTION 'Una versión nace en borrador, sin fechas ni responsable de publicación o retiro'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        IF OLD.status <> 'draft' THEN
            RAISE EXCEPTION 'Solo se puede borrar una versión en borrador (RN-17)' USING ERRCODE = 'check_violation';
        END IF;
        RETURN OLD;
    END IF;
    IF OLD.status = 'draft' THEN
        IF NEW.status IN ('draft', 'published') AND NEW.scenario_id = OLD.scenario_id THEN
            RETURN NEW;                               -- borrador: editable o publicable
        END IF;
    ELSIF OLD.status = 'published' AND NEW.status = 'retired'
          AND (to_jsonb(NEW) - 'status' - 'retired_at') = (to_jsonb(OLD) - 'status' - 'retired_at') THEN
        RETURN NEW;                                   -- retirar sin cambiar nada más
    END IF;
    RAISE EXCEPTION 'Transición o cambio no permitido en versión % (%→%)', OLD.id, OLD.status, NEW.status
        USING ERRCODE = 'check_violation';
END $$;

CREATE TRIGGER trg_guard_version_status
    BEFORE INSERT OR UPDATE OR DELETE ON scenario_versions
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

-- Una cuenta bloqueada es terminal (D-20): no se modifica ni se reactiva, y
-- cognito_sub nunca cambia. El bloqueo mismo (active → blocked) lo hace block_account.
CREATE FUNCTION guard_account_update() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'blocked' THEN
        RAISE EXCEPTION 'La cuenta % está bloqueada: no se modifica ni se reactiva (D-20)', OLD.id
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.cognito_sub IS DISTINCT FROM OLD.cognito_sub THEN
        RAISE EXCEPTION 'cognito_sub es inmutable' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_guard_account_update
    BEFORE UPDATE ON accounts FOR EACH ROW EXECUTE FUNCTION guard_account_update();

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

-- account_id es inmutable una vez asignado; secret_hash solo puede quedarse
-- igual o pasar a NULL (al vincular el navegador con una cuenta).
CREATE FUNCTION guard_participant_update() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.account_id IS NOT NULL AND NEW.account_id IS DISTINCT FROM OLD.account_id THEN
        RAISE EXCEPTION 'account_id es inmutable una vez asignado' USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.secret_hash IS NOT NULL AND NEW.secret_hash IS DISTINCT FROM OLD.secret_hash THEN
        RAISE EXCEPTION 'secret_hash solo puede quedarse igual o pasar a NULL' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_guard_participant_update
    BEFORE UPDATE ON participants FOR EACH ROW EXECUTE FUNCTION guard_participant_update();

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
    has_prior_session     boolean NOT NULL DEFAULT false,   -- lo fija el trigger trg_session_prior
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

-- Defecto 9: la base decide si hay sesión previa. Bloquea la fila del participante
-- (dos inicios simultáneos se ordenan aquí), rechaza cuentas bloqueadas y calcula
-- has_prior_session (otra sesión del participante en el mismo escenario, de cualquier
-- versión). El valor enviado por el cliente se ignora. Orden de bloqueo (cuenta,
-- participante, sesiones): este trigger toma solo el participante.
CREATE FUNCTION compute_session_prior() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_scenario uuid;
BEGIN
    PERFORM 1 FROM nukyro.participants WHERE id = NEW.participant_id FOR NO KEY UPDATE;
    IF EXISTS (SELECT 1 FROM nukyro.participants p JOIN nukyro.accounts a ON a.id = p.account_id
                WHERE p.id = NEW.participant_id AND a.status = 'blocked') THEN
        RAISE EXCEPTION 'Una cuenta bloqueada no inicia sesiones nuevas (D-20)' USING ERRCODE = 'check_violation';
    END IF;
    SELECT scenario_id INTO v_scenario FROM nukyro.scenario_versions WHERE id = NEW.scenario_version_id;
    NEW.has_prior_session := EXISTS (
        SELECT 1 FROM nukyro.sessions s
          JOIN nukyro.scenario_versions v ON v.id = s.scenario_version_id
         WHERE s.participant_id = NEW.participant_id AND v.scenario_id = v_scenario);
    RETURN NEW;
END $$;
CREATE TRIGGER trg_session_prior
    BEFORE INSERT ON sessions FOR EACH ROW EXECUTE FUNCTION compute_session_prior();

-- Hitos de una sola escritura (RF-005, RF-061): pretest_completed_at, outcome_reached_at,
-- outcome_node_id y completed_at pasan una vez de NULL a un valor; después no se reescriben
-- ni se borran. Solo dispara con UPDATE de esas columnas: el archivo (facts_written_at) y las
-- cascadas de borrado no lo tocan. Repetir el mismo valor no es una reescritura.
CREATE FUNCTION guard_session_milestones() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF (OLD.pretest_completed_at IS NOT NULL AND NEW.pretest_completed_at IS DISTINCT FROM OLD.pretest_completed_at)
       OR (OLD.outcome_reached_at IS NOT NULL AND NEW.outcome_reached_at IS DISTINCT FROM OLD.outcome_reached_at)
       OR (OLD.outcome_node_id IS NOT NULL AND NEW.outcome_node_id IS DISTINCT FROM OLD.outcome_node_id)
       OR (OLD.completed_at IS NOT NULL AND NEW.completed_at IS DISTINCT FROM OLD.completed_at) THEN
        RAISE EXCEPTION 'Un hito de la sesión % no se reescribe ni se borra (RF-005)', OLD.id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_guard_session_milestones
    BEFORE UPDATE OF pretest_completed_at, outcome_reached_at, outcome_node_id, completed_at
    ON sessions FOR EACH ROW EXECUTE FUNCTION guard_session_milestones();

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

-- Tras enviar el intento (submitted_at) las respuestas no cambian. Es un trigger
-- AFTER (corre tras las comprobaciones de llaves foráneas, que son AFTER con nombre
-- RI_…) y lee el intento con FOR SHARE: enviar y responder a la vez se ordenan.
CREATE FUNCTION guard_answer_after_submit() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM 1 FROM nukyro.assessment_attempts
     WHERE id = NEW.attempt_id AND submitted_at IS NOT NULL FOR SHARE;
    IF FOUND THEN
        RAISE EXCEPTION 'El intento % ya se envió: sus respuestas no cambian', NEW.attempt_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END $$;
CREATE TRIGGER trg_guard_answer_after_submit
    AFTER INSERT OR UPDATE ON assessment_answers FOR EACH ROW EXECUTE FUNCTION guard_answer_after_submit();

-- Un intento enviado es definitivo: no se reabre ni se vuelve a puntuar (RN-19)
CREATE FUNCTION guard_attempt_submitted() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.submitted_at IS NOT NULL THEN
        RAISE EXCEPTION 'El intento % ya se envió: no cambia', OLD.id USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_guard_attempt_submitted
    BEFORE UPDATE ON assessment_attempts FOR EACH ROW EXECUTE FUNCTION guard_attempt_submitted();

-- ---------------------------------------------------------------------
-- Estadísticas anónimas (ADR-004, ADR-007): sin sesión, participante ni cuenta.
-- Ningún rol de conexión lee ni escribe estas tablas: las llena y las
-- reescribe solo el owner, mediante las funciones de más abajo.
-- ---------------------------------------------------------------------
CREATE TABLE session_facts (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_version_id    uuid NOT NULL REFERENCES scenario_versions (id) ON DELETE RESTRICT,
    week_start             date NOT NULL CHECK (extract(isodow FROM week_start) = 1),
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
    stopped_at_key         text,            -- clave del nodo actual si no llegó al desenlace
    evaluations_completed  boolean NOT NULL,
    duration_bucket_min    smallint CHECK (duration_bucket_min >= 0 AND duration_bucket_min % 5 = 0),
    CHECK (transfer_correct IS NULL OR transfer_correct <= transfer_total),
    CHECK (causal_correct IS NULL OR causal_correct <= causal_total),
    CHECK (justification_correct IS NULL OR justification_correct <= justification_total),
    CHECK (outcome_reached OR outcome_key IS NULL),
    CHECK (NOT outcome_reached OR stopped_at_key IS NULL)
);

CREATE TABLE decision_facts (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_version_id  uuid NOT NULL REFERENCES scenario_versions (id) ON DELETE RESTRICT,
    week_start           date NOT NULL CHECK (extract(isodow FROM week_start) = 1),
    decision_key         text NOT NULL,
    option_key           text NOT NULL,
    is_first_session     boolean NOT NULL
);

-- Aciertos por tema y tipo de conjunto; sin vínculo con session_facts (ADR-007)
CREATE TABLE topic_facts (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_version_id  uuid NOT NULL REFERENCES scenario_versions (id) ON DELETE RESTRICT,
    week_start           date NOT NULL CHECK (extract(isodow FROM week_start) = 1),
    set_type             text NOT NULL CHECK (set_type IN ('pretest', 'posttest', 'transfer', 'causal')),
    topic                text NOT NULL,
    is_first_session     boolean NOT NULL,
    correct              smallint NOT NULL CHECK (correct >= 0),
    total                smallint NOT NULL CHECK (total > 0),
    CHECK (correct <= total)
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

-- ---------------------------------------------------------------------
-- Funciones del owner (ADR-007). SECURITY DEFINER: corren con los permisos del
-- dueño, por eso fijan search_path, califican todos los nombres y no son
-- ejecutables por PUBLIC (más abajo). Orden de bloqueo en todas las rutas:
-- cuenta, participante, sesiones, y al final las tablas de hechos (siempre en el
-- mismo orden: decision_facts, session_facts, topic_facts). El bloqueo de los
-- hechos se toma ANTES de copiar (no después): dos archivos simultáneos que
-- insertaran primero y bloquearan después se interbloquearían.
-- ---------------------------------------------------------------------

-- Interna (sin GRANT). El llamador ya bloqueó la cuenta y el participante.
-- Copia a los hechos, por cada sesión con facts_written_at nulo, los datos de
-- sesión (puntuaciones, aciertos, desenlace, duración por tramos de 5 min), de
-- decisión y por tema, y fija facts_written_at. No copia nada si el participante
-- se opuso (exclude_from_stats) o su cuenta está bloqueada por menor de edad.
-- La semana es la del inicio de la sesión, en UTC. Devuelve las sesiones copiadas.
CREATE FUNCTION archive_participant(p_participant uuid) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, nukyro, pg_temp
AS $$
DECLARE
    v_excluded boolean;
    v_account  uuid;
    v_ids      uuid[];
BEGIN
    SELECT p.exclude_from_stats, p.account_id INTO v_excluded, v_account
      FROM nukyro.participants p WHERE p.id = p_participant FOR NO KEY UPDATE;
    IF NOT FOUND OR v_excluded THEN RETURN 0; END IF;
    IF v_account IS NOT NULL AND EXISTS (
           SELECT 1 FROM nukyro.accounts a
            WHERE a.id = v_account AND a.status = 'blocked' AND a.block_reason = 'underage') THEN
        RETURN 0;
    END IF;

    SELECT array_agg(l.id) INTO v_ids
      FROM (SELECT s.id FROM nukyro.sessions s
             WHERE s.participant_id = p_participant AND s.facts_written_at IS NULL
             ORDER BY s.id FOR UPDATE) l;
    IF v_ids IS NULL THEN RETURN 0; END IF;

    LOCK TABLE nukyro.decision_facts, nukyro.session_facts, nukyro.topic_facts IN ACCESS EXCLUSIVE MODE;

    INSERT INTO nukyro.session_facts (
        scenario_version_id, week_start, is_first_session, pretest_score, posttest_score,
        transfer_correct, transfer_total, causal_correct, causal_total,
        justification_correct, justification_total, outcome_reached, outcome_key, stopped_at_key,
        evaluations_completed, duration_bucket_min)
    SELECT s.scenario_version_id,
           date_trunc('week', s.started_at AT TIME ZONE 'UTC')::date,
           s.is_first_session,
           pre.score, post.score,
           tr.correct_count, tr.answered_count, ca.correct_count, ca.answered_count,
           CASE WHEN j.t > 0 THEN j.c END, CASE WHEN j.t > 0 THEN j.t END,
           s.outcome_reached_at IS NOT NULL,
           CASE WHEN s.outcome_reached_at IS NOT NULL THEN o.key END,
           CASE WHEN s.outcome_reached_at IS NULL THEN c.key END,
           -- supuesto: evaluaciones completas = todos los conjuntos de la versión enviados
           NOT EXISTS (SELECT 1 FROM nukyro.question_sets q
                        WHERE q.version_id = s.scenario_version_id
                          AND NOT EXISTS (SELECT 1 FROM nukyro.assessment_attempts a
                                           WHERE a.session_id = s.id AND a.question_set_id = q.id
                                             AND a.submitted_at IS NOT NULL)),
           (greatest(0, floor(extract(epoch FROM
               coalesce(s.completed_at, s.outcome_reached_at, s.last_activity_at) - s.started_at) / 300)) * 5)::smallint
      FROM nukyro.sessions s
      LEFT JOIN LATERAL (SELECT a.score, a.correct_count, a.answered_count
                           FROM nukyro.assessment_attempts a JOIN nukyro.question_sets q ON q.id = a.question_set_id
                          WHERE a.session_id = s.id AND q.set_type = 'pretest' AND a.submitted_at IS NOT NULL) pre ON true
      LEFT JOIN LATERAL (SELECT a.score, a.correct_count, a.answered_count
                           FROM nukyro.assessment_attempts a JOIN nukyro.question_sets q ON q.id = a.question_set_id
                          WHERE a.session_id = s.id AND q.set_type = 'posttest' AND a.submitted_at IS NOT NULL) post ON true
      LEFT JOIN LATERAL (SELECT a.score, a.correct_count, a.answered_count
                           FROM nukyro.assessment_attempts a JOIN nukyro.question_sets q ON q.id = a.question_set_id
                          WHERE a.session_id = s.id AND q.set_type = 'transfer' AND a.submitted_at IS NOT NULL) tr ON true
      LEFT JOIN LATERAL (SELECT a.score, a.correct_count, a.answered_count
                           FROM nukyro.assessment_attempts a JOIN nukyro.question_sets q ON q.id = a.question_set_id
                          WHERE a.session_id = s.id AND q.set_type = 'causal' AND a.submitted_at IS NOT NULL) ca ON true
      LEFT JOIN LATERAL (SELECT (count(*) FILTER (WHERE d.justification_correct))::smallint AS c, count(*)::smallint AS t
                           FROM nukyro.session_decisions d
                           JOIN nukyro.decision_points dp ON dp.version_id = d.scenario_version_id AND dp.node_id = d.node_id
                          WHERE d.session_id = s.id AND dp.evaluated_for_h05 AND d.justification_correct IS NOT NULL) j ON true
      LEFT JOIN nukyro.nodes o ON o.id = s.outcome_node_id
      LEFT JOIN nukyro.nodes c ON c.id = s.current_node_id
     WHERE s.id = ANY (v_ids);

    INSERT INTO nukyro.decision_facts (scenario_version_id, week_start, decision_key, option_key, is_first_session)
    SELECT s.scenario_version_id, date_trunc('week', s.started_at AT TIME ZONE 'UTC')::date,
           n.key, o.key, s.is_first_session
      FROM nukyro.sessions s
      JOIN nukyro.session_decisions d ON d.session_id = s.id
      JOIN nukyro.nodes n ON n.id = d.node_id
      JOIN nukyro.options o ON o.id = d.option_id
     WHERE s.id = ANY (v_ids);

    INSERT INTO nukyro.topic_facts (scenario_version_id, week_start, set_type, topic, is_first_session, correct, total)
    SELECT s.scenario_version_id, date_trunc('week', s.started_at AT TIME ZONE 'UTC')::date,
           qs.set_type, q.topic, s.is_first_session,
           (count(*) FILTER (WHERE qo.is_correct))::smallint, count(*)::smallint
      FROM nukyro.sessions s
      JOIN nukyro.assessment_attempts a ON a.session_id = s.id AND a.submitted_at IS NOT NULL
      JOIN nukyro.question_sets qs ON qs.id = a.question_set_id
      JOIN nukyro.assessment_answers aa ON aa.attempt_id = a.id
      JOIN nukyro.questions q ON q.id = aa.question_id
      JOIN nukyro.question_options qo ON qo.id = aa.option_id
     WHERE s.id = ANY (v_ids)
     GROUP BY s.id, s.scenario_version_id, s.started_at, s.is_first_session, qs.set_type, q.topic;

    UPDATE nukyro.sessions SET facts_written_at = now() WHERE id = ANY (v_ids);
    RETURN cardinality(v_ids);
END $$;

-- Interna (sin GRANT). Tras archivar, reescribe TODAS las filas de las tres tablas
-- con id nuevo y en orden aleatorio (DELETE ... RETURNING + INSERT en una sentencia):
-- todas comparten xmin y el orden físico no sigue al de llegada. Si se agrega una
-- columna a un hecho, hay que agregarla aquí.
CREATE FUNCTION rewrite_facts() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, nukyro, pg_temp
AS $$
BEGIN
    LOCK TABLE nukyro.decision_facts, nukyro.session_facts, nukyro.topic_facts IN ACCESS EXCLUSIVE MODE;

    WITH d AS (DELETE FROM nukyro.decision_facts
               RETURNING scenario_version_id, week_start, decision_key, option_key, is_first_session)
    INSERT INTO nukyro.decision_facts (scenario_version_id, week_start, decision_key, option_key, is_first_session)
    SELECT scenario_version_id, week_start, decision_key, option_key, is_first_session FROM d ORDER BY random();

    WITH d AS (DELETE FROM nukyro.session_facts
               RETURNING scenario_version_id, week_start, is_first_session, pretest_score, posttest_score,
                         transfer_correct, transfer_total, causal_correct, causal_total,
                         justification_correct, justification_total, outcome_reached, outcome_key,
                         stopped_at_key, evaluations_completed, duration_bucket_min)
    INSERT INTO nukyro.session_facts (scenario_version_id, week_start, is_first_session, pretest_score, posttest_score,
                         transfer_correct, transfer_total, causal_correct, causal_total,
                         justification_correct, justification_total, outcome_reached, outcome_key,
                         stopped_at_key, evaluations_completed, duration_bucket_min)
    SELECT scenario_version_id, week_start, is_first_session, pretest_score, posttest_score,
           transfer_correct, transfer_total, causal_correct, causal_total,
           justification_correct, justification_total, outcome_reached, outcome_key,
           stopped_at_key, evaluations_completed, duration_bucket_min
      FROM d ORDER BY random();

    WITH d AS (DELETE FROM nukyro.topic_facts
               RETURNING scenario_version_id, week_start, set_type, topic, is_first_session, correct, total)
    INSERT INTO nukyro.topic_facts (scenario_version_id, week_start, set_type, topic, is_first_session, correct, total)
    SELECT scenario_version_id, week_start, set_type, topic, is_first_session, correct, total FROM d ORDER BY random();
END $$;

-- api: borra a un participante anónimo (RF-080 por petición propia). Bloquea,
-- rechaza si tiene cuenta, archiva, reescribe y borra. false si no existe.
CREATE FUNCTION erase_anonymous_participant(p_participant uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, nukyro, pg_temp
AS $$
DECLARE
    v_account uuid;
BEGIN
    SELECT p.account_id INTO v_account FROM nukyro.participants p WHERE p.id = p_participant FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    IF v_account IS NOT NULL THEN
        RAISE EXCEPTION 'El participante % tiene cuenta: se borra con el bloqueo y la purga de la cuenta', p_participant
            USING ERRCODE = 'check_violation';
    END IF;
    IF nukyro.archive_participant(p_participant) > 0 THEN PERFORM nukyro.rewrite_facts(); END IF;
    DELETE FROM nukyro.participants WHERE id = p_participant;
    RETURN true;
END $$;

-- api: guarda la encuesta de una sesión terminada (D-29, ADR-007). Bloquea al participante y
-- luego a la sesión; rechaza al opuesto o con cuenta bloqueada (42501), la sesión sin terminar
-- (55000) y la ya respondida (23505). Marca solo survey_answered (no toca last_activity_at),
-- inserta con la semana UTC de INICIO de la sesión y reescribe la tabla entera con id nuevo y en
-- orden aleatorio: todas las filas comparten xmin y el orden físico no sigue al de llegada.
-- Si se agrega una columna a survey_responses, hay que agregarla aquí.
CREATE FUNCTION submit_survey(
    p_session uuid, p_usefulness smallint, p_clarity smallint DEFAULT NULL,
    p_decision_impact smallint DEFAULT NULL, p_causal_understanding smallint DEFAULT NULL,
    p_summary_usefulness smallint DEFAULT NULL, p_would_repeat smallint DEFAULT NULL
) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, nukyro, pg_temp
AS $$
DECLARE
    v_participant uuid;
    v_account uuid;
    v_excluded boolean;
    v_version uuid;
    v_completed timestamptz;
    v_answered boolean;
    v_week date;
    v_first boolean;
BEGIN
    SELECT s.participant_id INTO v_participant FROM nukyro.sessions s WHERE s.id = p_session;
    IF NOT FOUND THEN RAISE EXCEPTION 'La sesión % no existe', p_session USING ERRCODE = 'no_data_found'; END IF;
    SELECT p.account_id, p.exclude_from_stats INTO v_account, v_excluded
      FROM nukyro.participants p WHERE p.id = v_participant FOR UPDATE;
    SELECT s.scenario_version_id, s.completed_at, s.survey_answered,
           date_trunc('week', s.started_at AT TIME ZONE 'UTC')::date, s.is_first_session
      INTO v_version, v_completed, v_answered, v_week, v_first
      FROM nukyro.sessions s WHERE s.id = p_session FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'La sesión % no existe', p_session USING ERRCODE = 'no_data_found'; END IF;
    IF v_completed IS NULL THEN
        RAISE EXCEPTION 'La sesión % no ha terminado' , p_session USING ERRCODE = 'object_not_in_prerequisite_state';
    END IF;
    IF v_excluded OR EXISTS (SELECT 1 FROM nukyro.accounts a WHERE a.id = v_account AND a.status = 'blocked') THEN
        RAISE EXCEPTION 'La encuesta no se ofrece a quien se opuso al uso estadístico' USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF v_answered THEN
        RAISE EXCEPTION 'La sesión % ya respondió la encuesta', p_session USING ERRCODE = 'unique_violation';
    END IF;

    UPDATE nukyro.sessions SET survey_answered = true WHERE id = p_session;

    LOCK TABLE nukyro.survey_responses IN ACCESS EXCLUSIVE MODE;
    INSERT INTO nukyro.survey_responses (scenario_version_id, week_start, is_first_session, usefulness, clarity,
                                         decision_impact, causal_understanding, summary_usefulness, would_repeat)
    VALUES (v_version, v_week, v_first, p_usefulness, p_clarity, p_decision_impact, p_causal_understanding,
            p_summary_usefulness, p_would_repeat);

    WITH d AS (DELETE FROM nukyro.survey_responses
               RETURNING scenario_version_id, week_start, is_first_session, usefulness, clarity,
                         decision_impact, causal_understanding, summary_usefulness, would_repeat)
    INSERT INTO nukyro.survey_responses (scenario_version_id, week_start, is_first_session, usefulness, clarity,
                                         decision_impact, causal_understanding, summary_usefulness, would_repeat)
    SELECT scenario_version_id, week_start, is_first_session, usefulness, clarity,
           decision_impact, causal_understanding, summary_usefulness, would_repeat FROM d ORDER BY random();
END $$;

-- api, admin, jobs: bloquea una cuenta (terminal, D-20). Orden: cuenta, participante,
-- sesiones. Salvo oposición o menor de edad, archiva y reescribe. Si la cuenta ya
-- está bloqueada no hace nada y devuelve false.
CREATE FUNCTION block_account(p_account uuid, p_reason text, p_deletion_due_at timestamptz) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, nukyro, pg_temp
AS $$
DECLARE
    v_status      text;
    v_participant uuid;
BEGIN
    SELECT a.status INTO v_status FROM nukyro.accounts a WHERE a.id = p_account FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'La cuenta % no existe', p_account USING ERRCODE = 'no_data_found';
    END IF;
    IF v_status = 'blocked' THEN RETURN false; END IF;
    SELECT p.id INTO v_participant FROM nukyro.participants p WHERE p.account_id = p_account FOR UPDATE;
    UPDATE nukyro.accounts
       SET status = 'blocked', blocked_at = now(), block_reason = p_reason, deletion_due_at = p_deletion_due_at
     WHERE id = p_account;
    IF v_participant IS NOT NULL AND p_reason <> 'underage' THEN
        -- archive_participant también omite al opuesto (exclude_from_stats)
        IF nukyro.archive_participant(v_participant) > 0 THEN PERFORM nukyro.rewrite_facts(); END IF;
    END IF;
    RETURN true;
END $$;

-- jobs: caducidad de anónimos (RF-080). Bloquea y revalida last_activity_at de cada
-- candidato (alguien pudo volver mientras se esperaba el bloqueo), archiva, reescribe
-- una sola vez y borra. Devuelve cuántos participantes se borraron.
CREATE FUNCTION expire_anonymous_participants(p_cutoff timestamptz) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, nukyro, pg_temp
AS $$
DECLARE
    v_id       uuid;
    v_ids      uuid[] := '{}';
    v_archived integer := 0;
BEGIN
    FOR v_id IN SELECT p.id FROM nukyro.participants p
                 WHERE p.account_id IS NULL AND p.last_activity_at < p_cutoff ORDER BY p.id
    LOOP
        PERFORM 1 FROM nukyro.participants p
         WHERE p.id = v_id AND p.account_id IS NULL AND p.last_activity_at < p_cutoff FOR UPDATE;
        IF FOUND THEN v_ids := v_ids || v_id; END IF;
    END LOOP;
    IF cardinality(v_ids) = 0 THEN RETURN 0; END IF;
    FOREACH v_id IN ARRAY v_ids LOOP
        v_archived := v_archived + nukyro.archive_participant(v_id);
    END LOOP;
    IF v_archived > 0 THEN PERFORM nukyro.rewrite_facts(); END IF;
    DELETE FROM nukyro.participants WHERE id = ANY (v_ids);
    RETURN cardinality(v_ids);
END $$;

-- jobs: purga de cuentas bloqueadas. SOLO borra las vencidas (D-20); no archiva
-- (el archivo ocurrió al bloquear). Devuelve cuántas se borraron.
CREATE FUNCTION purge_blocked_accounts(p_now timestamptz) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, nukyro, pg_temp
AS $$
DECLARE
    v_n integer;
BEGIN
    WITH d AS (DELETE FROM nukyro.accounts
                WHERE status = 'blocked' AND deletion_due_at <= p_now RETURNING 1)
    SELECT count(*) INTO v_n FROM d;
    RETURN v_n;
END $$;

-- analytics: resumen de primeras sesiones de una versión. Con menos de 10 devuelve
-- suprimido y sin valores; con 10 o más, agregados (cada promedio exige además 10
-- valores propios, para no exponer a una sola persona).
CREATE FUNCTION report_session_summary(p_version uuid)
RETURNS TABLE (suppressed boolean, first_sessions integer, outcome_reached_count integer,
               avg_pretest_score numeric, avg_posttest_score numeric)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog, nukyro, pg_temp
AS $$
BEGIN
    RETURN QUERY
    SELECT false, count(*)::integer, (count(*) FILTER (WHERE f.outcome_reached))::integer,
           CASE WHEN count(f.pretest_score)  >= 10 THEN round(avg(f.pretest_score), 2) END,
           CASE WHEN count(f.posttest_score) >= 10 THEN round(avg(f.posttest_score), 2) END
      FROM nukyro.session_facts f
     WHERE f.scenario_version_id = p_version AND f.is_first_session
    HAVING count(*) >= 10;
    IF NOT FOUND THEN
        RETURN QUERY SELECT true, NULL::integer, NULL::integer, NULL::numeric, NULL::numeric;
    END IF;
END $$;


-- ---------------------------------------------------------------------
-- Roles y privilegios (§6 del modelo). Roles de grupo sin LOGIN; los
-- usuarios de conexión se crean por entorno y heredan de ellos.
-- nukyro_api (participantes) y nukyro_admin (panel) están separados.
-- ---------------------------------------------------------------------
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

-- Ninguna función es ejecutable por PUBLIC; solo se concede lo indicado abajo.
-- (Los triggers no necesitan EXECUTE al dispararse.)
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA nukyro FROM PUBLIC;

-- Nada de «GRANT ... ON ALL TABLES»: session_facts, decision_facts y topic_facts no
-- se conceden a ningún rol de conexión (ADR-007); solo las funciones del owner las tocan.

-- API de participantes: contenido de solo lectura; identidad y simulación con el mínimo
-- necesario, por columna (defecto 7)
GRANT SELECT ON
    nukyro.scenarios, nukyro.scenario_versions, nukyro.learning_objectives, nukyro.state_variables,
    nukyro.nodes, nukyro.decision_points, nukyro.options, nukyro.justification_reasons, nukyro.rules,
    nukyro.educational_references, nukyro.decision_references, nukyro.feedback_items,
    nukyro.question_sets, nukyro.questions, nukyro.question_options
TO nukyro_api;
GRANT SELECT ON
    nukyro.accounts, nukyro.participants, nukyro.sessions, nukyro.session_variables,
    nukyro.assessment_attempts, nukyro.assessment_answers
TO nukyro_api;
GRANT SELECT, INSERT ON
    nukyro.document_acceptances, nukyro.session_steps, nukyro.session_decisions,
    nukyro.session_decision_reasons, nukyro.session_effects, nukyro.session_events,
    nukyro.session_event_causes
TO nukyro_api;
GRANT INSERT (id, cognito_sub, email, nickname, newsletter_opt_in, surveys_opt_in, last_login_at, created_at)
    ON nukyro.accounts TO nukyro_api;
GRANT UPDATE (email, nickname, newsletter_opt_in, surveys_opt_in, last_login_at) ON nukyro.accounts TO nukyro_api;
GRANT INSERT ON nukyro.participants TO nukyro_api;
GRANT UPDATE (account_id, secret_hash, exclude_from_stats, last_activity_at) ON nukyro.participants TO nukyro_api;
GRANT INSERT (id, participant_id, scenario_version_id, current_node_id, self_reported_first)
    ON nukyro.sessions TO nukyro_api;
GRANT UPDATE (current_node_id, outcome_node_id, pretest_completed_at, outcome_reached_at, completed_at,
              last_activity_at, survey_answered) ON nukyro.sessions TO nukyro_api;
GRANT INSERT ON nukyro.session_variables, nukyro.assessment_attempts, nukyro.assessment_answers TO nukyro_api;
GRANT UPDATE (value, updated_at) ON nukyro.session_variables TO nukyro_api;
GRANT UPDATE (submitted_at, answered_count, correct_count, score) ON nukyro.assessment_attempts TO nukyro_api;
GRANT UPDATE (option_id, answered_at) ON nukyro.assessment_answers TO nukyro_api;
GRANT SELECT, INSERT ON nukyro.consent_events TO nukyro_api;
GRANT EXECUTE ON FUNCTION nukyro.submit_survey(uuid, smallint, smallint, smallint, smallint, smallint, smallint) TO nukyro_api;
GRANT EXECUTE ON FUNCTION nukyro.erase_anonymous_participant(uuid) TO nukyro_api;
GRANT EXECUTE ON FUNCTION nukyro.block_account(uuid, text, timestamptz) TO nukyro_api;

-- Panel de administración: contenido, ARCO y bitácora; datos de participantes
-- solo para atender ARCO (consultar, rectificar, oponerse, bloquear). Sin DELETE de admin_users.
GRANT SELECT, INSERT, UPDATE, DELETE ON
    nukyro.scenarios, nukyro.scenario_versions, nukyro.learning_objectives,
    nukyro.state_variables, nukyro.nodes, nukyro.decision_points, nukyro.options,
    nukyro.justification_reasons, nukyro.rules, nukyro.educational_references,
    nukyro.decision_references, nukyro.feedback_items, nukyro.question_sets, nukyro.questions,
    nukyro.question_options
TO nukyro_admin;
GRANT SELECT, INSERT, UPDATE ON nukyro.admin_users TO nukyro_admin;
GRANT SELECT, INSERT, UPDATE ON nukyro.arco_requests TO nukyro_admin;
GRANT SELECT ON nukyro.accounts, nukyro.participants TO nukyro_admin;
GRANT UPDATE (email, nickname, newsletter_opt_in, surveys_opt_in) ON nukyro.accounts TO nukyro_admin;
GRANT UPDATE (exclude_from_stats) ON nukyro.participants TO nukyro_admin;
GRANT SELECT, INSERT ON nukyro.consent_events TO nukyro_admin;
GRANT SELECT ON
    nukyro.document_acceptances, nukyro.sessions, nukyro.session_steps, nukyro.session_decisions,
    nukyro.session_decision_reasons, nukyro.session_variables, nukyro.session_effects,
    nukyro.session_events, nukyro.session_event_causes, nukyro.assessment_attempts,
    nukyro.assessment_answers
TO nukyro_admin;
GRANT SELECT, INSERT ON nukyro.admin_audit_log TO nukyro_admin;
GRANT EXECUTE ON FUNCTION nukyro.block_account(uuid, text, timestamptz) TO nukyro_admin;

-- Tareas programadas (caducidad, purga de cuentas, solicitudes ARCO y bitácora): sin
-- lectura de hechos ni de encuestas, sin DELETE directo de participantes ni cuentas
-- y sin UPDATE de cuentas ni sesiones; todo eso pasa por las funciones.
GRANT SELECT, DELETE ON nukyro.admin_audit_log, nukyro.arco_requests TO nukyro_jobs;
GRANT SELECT (id, status, last_login_at, block_reason, deletion_due_at) ON nukyro.accounts TO nukyro_jobs;
GRANT EXECUTE ON FUNCTION nukyro.block_account(uuid, text, timestamptz) TO nukyro_jobs;
GRANT EXECUTE ON FUNCTION nukyro.expire_anonymous_participants(timestamptz) TO nukyro_jobs;
GRANT EXECUTE ON FUNCTION nukyro.purge_blocked_accounts(timestamptz) TO nukyro_jobs;

-- Analítica: catálogo de versiones y el resumen agregado con umbral de 10; ninguna fila de hechos
GRANT SELECT ON nukyro.scenarios, nukyro.scenario_versions TO nukyro_analytics;
GRANT EXECUTE ON FUNCTION nukyro.report_session_summary(uuid) TO nukyro_analytics;
