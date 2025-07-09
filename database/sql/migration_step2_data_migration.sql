-- MIGRACIÓN PASO 2: Migrar datos de estructura actual a nueva estructura
-- Fecha: 2025-07-09
-- Propósito: Transferir datos manteniendo integridad y UUIDs originales

-- 1. Crear subtemas basados en categorías existentes
INSERT INTO ai_subthemes (id, name, description, created_at)
SELECT 
    gen_random_uuid(),
    COALESCE(category, 'General') as name,
    CASE 
        WHEN category IS NOT NULL THEN 'Subtema migrado automáticamente: ' || category
        ELSE 'Subtema general para cursos sin categoría específica'
    END as description,
    NOW() as created_at
FROM (
    SELECT DISTINCT COALESCE(category, 'General') as category 
    FROM courses 
) t
ON CONFLICT DO NOTHING;

-- 2. Migrar cursos manteniendo UUIDs originales
INSERT INTO ai_courses (
    id, subtheme_id, name, short_description, long_description,
    session_count, total_duration_min, price, currency, course_url,
    purchase_url, level, language, audience_category, status,
    max_enrollees, created_at
)
SELECT 
    c.id,  -- Mantener UUID original
    st.id as subtheme_id,
    c.name,
    COALESCE(c.short_description, 'Descripción no disponible') as short_description,
    COALESCE(c.long_description, 'Descripción detallada no disponible') as long_description,
    COALESCE((SELECT COUNT(*) FROM course_modules WHERE course_id = c.id), 0) as session_count,
    COALESCE(
        CASE 
            WHEN c.total_duration IS NOT NULL THEN EXTRACT(EPOCH FROM c.total_duration) / 60
            ELSE 0
        END, 0
    ) as total_duration_min,
    COALESCE(c.price_usd, 0) as price,
    COALESCE(c.currency, 'USD') as currency,
    c.course_link as course_url,
    c.purchase_link as purchase_url,
    COALESCE(c.level, 'básico') as level,
    COALESCE(c.language, 'es') as language,
    COALESCE(c.category, 'general') as audience_category,
    CASE 
        WHEN c.published = true THEN 'publicado'
        ELSE 'borrador'
    END as status,
    COALESCE(c.max_students, 0) as max_enrollees,
    COALESCE(c.created_at, NOW()) as created_at
FROM courses c
LEFT JOIN ai_subthemes st ON st.name = COALESCE(c.category, 'General')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    short_description = EXCLUDED.short_description,
    long_description = EXCLUDED.long_description,
    session_count = EXCLUDED.session_count,
    total_duration_min = EXCLUDED.total_duration_min,
    price = EXCLUDED.price,
    currency = EXCLUDED.currency,
    course_url = EXCLUDED.course_url,
    purchase_url = EXCLUDED.purchase_url,
    level = EXCLUDED.level,
    language = EXCLUDED.language,
    audience_category = EXCLUDED.audience_category,
    status = EXCLUDED.status,
    max_enrollees = EXCLUDED.max_enrollees;

-- 3. Migrar módulos a sesiones manteniendo UUIDs originales
INSERT INTO ai_course_sessions (
    id, course_id, session_index, title, objective,
    duration_minutes, display_order, modality, resources_url, created_at
)
SELECT 
    cm.id,  -- Mantener UUID original
    cm.course_id,
    COALESCE(cm.module_index, 1) as session_index,
    COALESCE(cm.name, 'Sesión sin título') as title,
    COALESCE(cm.description, 'Objetivo no especificado') as objective,
    COALESCE(
        CASE 
            WHEN cm.duration IS NOT NULL THEN EXTRACT(EPOCH FROM cm.duration) / 60
            ELSE 0
        END, 0
    ) as duration_minutes,
    COALESCE(cm.module_index, 1) as display_order,
    'online' as modality,
    NULL as resources_url,
    COALESCE(cm.created_at, NOW()) as created_at
FROM course_modules cm
WHERE EXISTS (SELECT 1 FROM ai_courses ac WHERE ac.id = cm.course_id)
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    objective = EXCLUDED.objective,
    duration_minutes = EXCLUDED.duration_minutes,
    display_order = EXCLUDED.display_order;

-- 4. Migrar ejercicios a prácticas
INSERT INTO ai_session_practices (
    session_id, practice_index, title, description, notes,
    estimated_duration_min, resource_type, is_mandatory, created_at
)
SELECT 
    cm.id as session_id,  -- Usar ID del módulo como session_id
    COALESCE(me.order_idx, 1) as practice_index,
    COALESCE('Práctica ' || me.order_idx, 'Práctica sin título') as title,
    COALESCE(me.description, 'Práctica sin descripción') as description,
    me.instructions as notes,
    COALESCE(me.estimated_duration, 0) as estimated_duration_min,
    COALESCE(me.exercise_type, 'práctica') as resource_type,
    COALESCE(me.is_required, true) as is_mandatory,
    COALESCE(me.created_at, NOW()) as created_at
FROM module_exercises me
JOIN course_modules cm ON me.module_id = cm.id
WHERE EXISTS (SELECT 1 FROM ai_course_sessions acs WHERE acs.id = cm.id)
ON CONFLICT (session_id, practice_index) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    notes = EXCLUDED.notes,
    estimated_duration_min = EXCLUDED.estimated_duration_min,
    resource_type = EXCLUDED.resource_type,
    is_mandatory = EXCLUDED.is_mandatory;

-- 5. Migrar recursos gratuitos a entregables
INSERT INTO ai_session_deliverables (
    session_id, name, type, resource_url, estimated_duration_min,
    resource_type, is_mandatory, created_at
)
SELECT 
    cm.id as session_id,  -- Usar ID del módulo como session_id
    COALESCE(fr.resource_name, 'Recurso sin nombre') as name,
    COALESCE(fr.resource_type, 'documento') as type,
    fr.resource_url,
    COALESCE(fr.estimated_duration, 0) as estimated_duration_min,
    COALESCE(fr.resource_type, 'documento') as resource_type,
    COALESCE(fr.is_required, false) as is_mandatory,
    COALESCE(fr.created_at, NOW()) as created_at
FROM free_resources fr
JOIN course_modules cm ON fr.course_id = cm.course_id
WHERE EXISTS (SELECT 1 FROM ai_course_sessions acs WHERE acs.id = cm.id)
ON CONFLICT (session_id, name) DO UPDATE SET
    type = EXCLUDED.type,
    resource_url = EXCLUDED.resource_url,
    estimated_duration_min = EXCLUDED.estimated_duration_min,
    resource_type = EXCLUDED.resource_type,
    is_mandatory = EXCLUDED.is_mandatory;

-- 6. Actualizar contadores de sesiones en cursos
UPDATE ai_courses 
SET session_count = (
    SELECT COUNT(*) 
    FROM ai_course_sessions 
    WHERE course_id = ai_courses.id
);

-- 7. Verificar integridad de migración
SELECT 
    'MIGRACIÓN COMPLETADA' as status,
    'Original: ' || (SELECT COUNT(*) FROM courses) || ' cursos' as cursos_original,
    'Migrado: ' || (SELECT COUNT(*) FROM ai_courses) || ' cursos' as cursos_migrados,
    'Original: ' || (SELECT COUNT(*) FROM course_modules) || ' módulos' as modulos_original,
    'Migrado: ' || (SELECT COUNT(*) FROM ai_course_sessions) || ' sesiones' as sesiones_migradas,
    'Prácticas: ' || (SELECT COUNT(*) FROM ai_session_practices) as practicas_creadas,
    'Entregables: ' || (SELECT COUNT(*) FROM ai_session_deliverables) as entregables_creados;