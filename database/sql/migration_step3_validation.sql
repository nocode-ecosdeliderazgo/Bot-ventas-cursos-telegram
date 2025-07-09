-- MIGRACIÓN PASO 3: Validación completa de migración de datos
-- Fecha: 2025-07-09
-- Propósito: Verificar integridad y completitud de la migración

-- 1. Comparar conteos de registros
SELECT 
    'COMPARACIÓN DE REGISTROS' as seccion,
    '' as detalle,
    '' as resultado,
    '' as status;

SELECT 
    'courses vs ai_courses' as seccion,
    'Cursos originales' as detalle,
    COUNT(*)::TEXT as resultado,
    'ORIGINAL' as status
FROM courses
UNION ALL
SELECT 
    'courses vs ai_courses' as seccion,
    'Cursos migrados' as detalle,
    COUNT(*)::TEXT as resultado,
    CASE 
        WHEN COUNT(*) = (SELECT COUNT(*) FROM courses) THEN 'OK'
        ELSE 'ERROR'
    END as status
FROM ai_courses;

-- 2. Verificar módulos/sesiones
SELECT 
    'course_modules vs ai_course_sessions' as seccion,
    'Módulos originales' as detalle,
    COUNT(*)::TEXT as resultado,
    'ORIGINAL' as status
FROM course_modules
UNION ALL
SELECT 
    'course_modules vs ai_course_sessions' as seccion,
    'Sesiones migradas' as detalle,
    COUNT(*)::TEXT as resultado,
    CASE 
        WHEN COUNT(*) = (SELECT COUNT(*) FROM course_modules) THEN 'OK'
        ELSE 'ERROR'
    END as status
FROM ai_course_sessions;

-- 3. Verificar ejercicios/prácticas
SELECT 
    'module_exercises vs ai_session_practices' as seccion,
    'Ejercicios originales' as detalle,
    COUNT(*)::TEXT as resultado,
    'ORIGINAL' as status
FROM module_exercises
UNION ALL
SELECT 
    'module_exercises vs ai_session_practices' as seccion,
    'Prácticas migradas' as detalle,
    COUNT(*)::TEXT as resultado,
    CASE 
        WHEN COUNT(*) >= (SELECT COUNT(*) FROM module_exercises) THEN 'OK'
        ELSE 'REVISAR'
    END as status
FROM ai_session_practices;

-- 4. Verificar recursos/entregables
SELECT 
    'free_resources vs ai_session_deliverables' as seccion,
    'Recursos originales' as detalle,
    COUNT(*)::TEXT as resultado,
    'ORIGINAL' as status
FROM free_resources
UNION ALL
SELECT 
    'free_resources vs ai_session_deliverables' as seccion,
    'Entregables migrados' as detalle,
    COUNT(*)::TEXT as resultado,
    CASE 
        WHEN COUNT(*) >= (SELECT COUNT(*) FROM free_resources) THEN 'OK'
        ELSE 'REVISAR'
    END as status
FROM ai_session_deliverables;

-- 5. Verificar integridad referencial
SELECT 
    'INTEGRIDAD REFERENCIAL' as seccion,
    '' as detalle,
    '' as resultado,
    '' as status;

-- Verificar que todos los cursos tienen subtema
SELECT 
    'ai_courses sin subtema' as seccion,
    'Cursos sin subtema_id' as detalle,
    COUNT(*)::TEXT as resultado,
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK'
        ELSE 'ERROR'
    END as status
FROM ai_courses 
WHERE subtheme_id IS NULL;

-- Verificar que todas las sesiones tienen curso válido
SELECT 
    'ai_course_sessions sin curso' as seccion,
    'Sesiones sin curso válido' as detalle,
    COUNT(*)::TEXT as resultado,
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK'
        ELSE 'ERROR'
    END as status
FROM ai_course_sessions acs
WHERE NOT EXISTS (SELECT 1 FROM ai_courses ac WHERE ac.id = acs.course_id);

-- Verificar que todas las prácticas tienen sesión válida
SELECT 
    'ai_session_practices sin sesión' as seccion,
    'Prácticas sin sesión válida' as detalle,
    COUNT(*)::TEXT as resultado,
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK'
        ELSE 'ERROR'
    END as status
FROM ai_session_practices asp
WHERE NOT EXISTS (SELECT 1 FROM ai_course_sessions acs WHERE acs.id = asp.session_id);

-- Verificar que todos los entregables tienen sesión válida
SELECT 
    'ai_session_deliverables sin sesión' as seccion,
    'Entregables sin sesión válida' as detalle,
    COUNT(*)::TEXT as resultado,
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK'
        ELSE 'ERROR'
    END as status
FROM ai_session_deliverables asd
WHERE NOT EXISTS (SELECT 1 FROM ai_course_sessions acs WHERE acs.id = asd.session_id);

-- 6. Verificar contadores actualizados
SELECT 
    'CONTADORES ACTUALIZADOS' as seccion,
    '' as detalle,
    '' as resultado,
    '' as status;

SELECT 
    'session_count' as seccion,
    'Cursos con contador incorrecto' as detalle,
    COUNT(*)::TEXT as resultado,
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK'
        ELSE 'ERROR'
    END as status
FROM ai_courses c
WHERE c.session_count != (
    SELECT COUNT(*) 
    FROM ai_course_sessions s 
    WHERE s.course_id = c.id
);

-- 7. Verificar UUIDs preservados
SELECT 
    'PRESERVACIÓN DE UUIDs' as seccion,
    '' as detalle,
    '' as resultado,
    '' as status;

SELECT 
    'UUIDs cursos preservados' as seccion,
    'Cursos con UUID diferente' as detalle,
    COUNT(*)::TEXT as resultado,
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK'
        ELSE 'ERROR'
    END as status
FROM courses c
WHERE NOT EXISTS (SELECT 1 FROM ai_courses ac WHERE ac.id = c.id);

SELECT 
    'UUIDs módulos preservados' as seccion,
    'Módulos con UUID diferente' as detalle,
    COUNT(*)::TEXT as resultado,
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK'
        ELSE 'ERROR'
    END as status
FROM course_modules cm
WHERE NOT EXISTS (SELECT 1 FROM ai_course_sessions acs WHERE acs.id = cm.id);

-- 8. Resumen final de validación
SELECT 
    'RESUMEN FINAL' as seccion,
    'Estado general de migración' as detalle,
    CASE 
        WHEN (SELECT COUNT(*) FROM courses) = (SELECT COUNT(*) FROM ai_courses)
        AND (SELECT COUNT(*) FROM course_modules) = (SELECT COUNT(*) FROM ai_course_sessions)
        AND (SELECT COUNT(*) FROM ai_courses WHERE subtheme_id IS NULL) = 0
        THEN 'MIGRACIÓN EXITOSA'
        ELSE 'MIGRACIÓN CON PROBLEMAS'
    END as resultado,
    'FINAL' as status;