-- =============================================================================
--  ATTENDANCE SYSTEM — POSTGRES SCHEMA (Supabase)
--  Run once in the Supabase SQL Editor (or via psql).
-- =============================================================================

-- ---------------------------------------------------------------------------
--  STATUS ENUM  (Postgres has real enum types, unlike MySQL's inline ENUM)
-- ---------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE attendance_status AS ENUM ('Present', 'Exit');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ---------------------------------------------------------------------------
--  EMPLOYEES  — roster (source of truth for "who is registered")
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employees (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(150) NOT NULL UNIQUE,
    department  VARCHAR(100) DEFAULT NULL,
    designation VARCHAR(100) DEFAULT NULL,
    photo_path  VARCHAR(255) DEFAULT NULL,   -- profile photo (relative to /photos)
    active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
--  CAMERAS  — optional registry of RTSP entry/exit points
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cameras (
    id          VARCHAR(50) PRIMARY KEY,      -- e.g. "Entry-1"
    location    VARCHAR(150) DEFAULT NULL,
    rtsp_url    VARCHAR(255) DEFAULT NULL,
    active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
--  ATTENDANCE  — every recognized-and-marked event
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    id           BIGSERIAL PRIMARY KEY,
    employee_id  INT          NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    name         VARCHAR(150) NOT NULL,        -- denormalised copy, fast reads
    att_date     DATE         NOT NULL,
    att_time     TIME         NOT NULL,
    status       attendance_status NOT NULL DEFAULT 'Present',
    camera_id    VARCHAR(50)  DEFAULT NULL,
    confidence   REAL         DEFAULT NULL,
    photo_path   VARCHAR(255) DEFAULT NULL,    -- captured snapshot for this event
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_att_date         ON attendance (att_date);
CREATE INDEX IF NOT EXISTS idx_att_name_date     ON attendance (name, att_date);
CREATE INDEX IF NOT EXISTS idx_att_employee_date ON attendance (employee_id, att_date);

-- ---------------------------------------------------------------------------
--  FACE EMBEDDINGS  — optional: move embeddings.pkl into Postgres too.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS face_embeddings (
    id          SERIAL PRIMARY KEY,
    employee_id INT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    embedding   BYTEA NOT NULL,     -- serialized float32[512] vector
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
