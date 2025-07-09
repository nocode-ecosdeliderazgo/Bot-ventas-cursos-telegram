-- Script de backup para migración de base de datos
-- Ejecutar antes de iniciar migración

-- Crear backup de tablas existentes
CREATE TABLE backup_courses AS SELECT * FROM courses;
CREATE TABLE backup_course_modules AS SELECT * FROM course_modules;
CREATE TABLE backup_user_leads AS SELECT * FROM user_leads;
CREATE TABLE backup_course_interactions AS SELECT * FROM course_interactions;
CREATE TABLE backup_conversations AS SELECT * FROM conversations;
CREATE TABLE backup_limited_time_bonuses AS SELECT * FROM limited_time_bonuses;
CREATE TABLE backup_bonus_claims AS SELECT * FROM bonus_claims;
CREATE TABLE backup_free_resources AS SELECT * FROM free_resources;
CREATE TABLE backup_module_exercises AS SELECT * FROM module_exercises;
CREATE TABLE backup_promotions AS SELECT * FROM promotions;
CREATE TABLE backup_course_sales AS SELECT * FROM course_sales;
CREATE TABLE backup_course_prompts AS SELECT * FROM course_prompts;

-- Verificar que todos los backups se crearon correctamente
SELECT 
    'backup_courses' as tabla, COUNT(*) as registros FROM backup_courses
UNION ALL
SELECT 
    'backup_course_modules' as tabla, COUNT(*) as registros FROM backup_course_modules
UNION ALL
SELECT 
    'backup_user_leads' as tabla, COUNT(*) as registros FROM backup_user_leads
UNION ALL
SELECT 
    'backup_course_interactions' as tabla, COUNT(*) as registros FROM backup_course_interactions
UNION ALL
SELECT 
    'backup_conversations' as tabla, COUNT(*) as registros FROM backup_conversations
UNION ALL
SELECT 
    'backup_limited_time_bonuses' as tabla, COUNT(*) as registros FROM backup_limited_time_bonuses
UNION ALL
SELECT 
    'backup_bonus_claims' as tabla, COUNT(*) as registros FROM backup_bonus_claims
UNION ALL
SELECT 
    'backup_free_resources' as tabla, COUNT(*) as registros FROM backup_free_resources
UNION ALL
SELECT 
    'backup_module_exercises' as tabla, COUNT(*) as registros FROM backup_module_exercises
UNION ALL
SELECT 
    'backup_promotions' as tabla, COUNT(*) as registros FROM backup_promotions
UNION ALL
SELECT 
    'backup_course_sales' as tabla, COUNT(*) as registros FROM backup_course_sales
UNION ALL
SELECT 
    'backup_course_prompts' as tabla, COUNT(*) as registros FROM backup_course_prompts;