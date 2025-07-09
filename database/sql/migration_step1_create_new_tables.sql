-- MIGRACIÓN PASO 1: Crear nuevas tablas para estructura optimizada
-- Fecha: 2025-07-09
-- Propósito: Crear estructura nueva junto con la existente para migración gradual

-- 1. Crear tabla de subtemas
CREATE TABLE IF NOT EXISTS ai_subthemes (
  id            UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  name          TEXT      NOT NULL,
  description   TEXT,
  created_at    TIMESTAMP DEFAULT NOW()
);

-- 2. Crear tabla de cursos optimizada
CREATE TABLE IF NOT EXISTS ai_courses (
  id                  UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  subtheme_id         UUID      NOT NULL REFERENCES ai_subthemes(id) ON DELETE RESTRICT,
  name                TEXT      NOT NULL,
  short_description   TEXT      NOT NULL,
  long_description    TEXT      NOT NULL,
  session_count       INTEGER   NOT NULL DEFAULT 0,
  total_duration_min  INTEGER   NOT NULL DEFAULT 0,
  price               NUMERIC(10,2) DEFAULT 0.00,
  currency            VARCHAR(3)     DEFAULT 'USD',
  course_url          TEXT,
  purchase_url        TEXT,
  level               TEXT      DEFAULT 'básico',
  language            TEXT      DEFAULT 'es',
  audience_category   TEXT,
  status              TEXT      DEFAULT 'borrador',
  start_date          DATE,
  end_date            DATE,
  max_enrollees       INTEGER   DEFAULT 0,
  created_at          TIMESTAMP DEFAULT NOW()
);

-- 3. Crear tabla de sesiones de curso
CREATE TABLE IF NOT EXISTS ai_course_sessions (
  id               UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id        UUID      NOT NULL REFERENCES ai_courses(id) ON DELETE CASCADE,
  session_index    INTEGER   NOT NULL,
  title            TEXT      NOT NULL,
  objective        TEXT,
  duration_minutes INTEGER,
  scheduled_at     TIMESTAMP,
  display_order    INTEGER,
  modality         TEXT      DEFAULT 'online',
  resources_url    TEXT,
  created_at       TIMESTAMP DEFAULT NOW(),
  UNIQUE(course_id, session_index)
);

-- 4. Crear tabla de prácticas por sesión
CREATE TABLE IF NOT EXISTS ai_session_practices (
  id                    UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id            UUID      NOT NULL REFERENCES ai_course_sessions(id) ON DELETE CASCADE,
  practice_index        INTEGER   NOT NULL,
  title                 TEXT      NOT NULL,
  description           TEXT      NOT NULL,
  notes                 TEXT,
  estimated_duration_min INTEGER   DEFAULT 0,
  resource_type         TEXT,
  is_mandatory          BOOLEAN   DEFAULT TRUE,
  created_at            TIMESTAMP DEFAULT NOW(),
  UNIQUE(session_id, practice_index)
);

-- 5. Crear tabla de entregables por sesión
CREATE TABLE IF NOT EXISTS ai_session_deliverables (
  id                    UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id            UUID      NOT NULL REFERENCES ai_course_sessions(id) ON DELETE CASCADE,
  name                  TEXT      NOT NULL,
  type                  TEXT      NOT NULL,
  resource_url          TEXT,
  estimated_duration_min INTEGER   DEFAULT 0,
  resource_type         TEXT,
  is_mandatory          BOOLEAN   DEFAULT TRUE,
  created_at            TIMESTAMP DEFAULT NOW(),
  UNIQUE(session_id, name)
);

-- 6. Crear índices para acelerar consultas
CREATE INDEX IF NOT EXISTS idx_ai_courses_subtheme   ON ai_courses(subtheme_id);
CREATE INDEX IF NOT EXISTS idx_ai_sessions_course    ON ai_course_sessions(course_id);
CREATE INDEX IF NOT EXISTS idx_ai_practices_session  ON ai_session_practices(session_id);
CREATE INDEX IF NOT EXISTS idx_ai_deliverables_sess  ON ai_session_deliverables(session_id);

-- 7. Verificar que las tablas se crearon correctamente
SELECT 
    'ai_subthemes' as tabla, 
    COUNT(*) as registros,
    'CREADA' as status
FROM ai_subthemes
UNION ALL
SELECT 
    'ai_courses' as tabla, 
    COUNT(*) as registros,
    'CREADA' as status
FROM ai_courses
UNION ALL
SELECT 
    'ai_course_sessions' as tabla, 
    COUNT(*) as registros,
    'CREADA' as status
FROM ai_course_sessions
UNION ALL
SELECT 
    'ai_session_practices' as tabla, 
    COUNT(*) as registros,
    'CREADA' as status
FROM ai_session_practices
UNION ALL
SELECT 
    'ai_session_deliverables' as tabla, 
    COUNT(*) as registros,
    'CREADA' as status
FROM ai_session_deliverables;