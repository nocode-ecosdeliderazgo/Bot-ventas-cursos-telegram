# PLAN DE MIGRACIÓN - BASE DE DATOS DEL BOT BRENDA

## RESUMEN EJECUTIVO

**Objetivo**: Migrar completamente la base de datos del bot de ventas "Brenda" de la estructura actual (15 tablas) a una nueva estructura optimizada (5 tablas core + estructura jerárquica).

**Impacto**: Esta migración afectará **TODAS** las funcionalidades del bot, incluyendo:
- 35+ herramientas de conversión del agente
- Todos los flujos de interacción (ads, course, contact, FAQ)
- Sistema de memoria y scoring de leads
- Integración con OpenAI GPT-4o-mini
- Servicios de base de datos y consultas SQL

**Criticidad**: ALTA - El bot depende 100% de acceso a información de base de datos

---

## ANÁLISIS DE ESTRUCTURAS

### ESTRUCTURA ACTUAL (15 Tablas Principales)
```sql
courses                     -- Información de cursos
course_modules              -- Módulos de cada curso  
course_prompts              -- Prompts específicos por curso
course_sales                -- Ventas completadas
course_interactions         -- Interacciones usuario-curso
user_leads                  -- Información de leads
conversations               -- Historial de conversaciones
limited_time_bonuses        -- Bonos por tiempo limitado
bonus_claims                -- Reclamaciones de bonos
free_resources              -- Recursos gratuitos
module_exercises            -- Ejercicios por módulo
promotions                  -- Promociones activas
```

### ESTRUCTURA NUEVA (5 Tablas Core)
```sql
ai_subthemes               -- Subtemas de AI (NUEVA)
ai_courses                 -- Cursos (EQUIVALENTE a courses)
ai_course_sessions         -- Sesiones (EQUIVALENTE a course_modules)
ai_session_practices       -- Prácticas (NUEVA)
ai_session_deliverables    -- Entregables (NUEVA)
```

### TABLAS SIN EQUIVALENCIA DIRECTA EN NUEVA ESTRUCTURA
⚠️ **CRÍTICO**: Estas tablas NO tienen equivalencia directa:
- `user_leads` → **MANTENER** (esencial para memoria de usuarios)
- `course_interactions` → **MANTENER** (tracking de interacciones)
- `conversations` → **MANTENER** (historial de chat)
- `limited_time_bonuses` → **MANTENER** (promociones activas)
- `bonus_claims` → **MANTENER** (reclamaciones de bonos)
- `free_resources` → **MANTENER** (recursos gratuitos)
- `promotions` → **MANTENER** (promociones)
- `course_sales` → **MANTENER** (ventas completadas)

---

## ESTRATEGIA DE MIGRACIÓN

### FASE 1: PREPARACIÓN (Pre-migración)
1. **Backup completo** de base de datos actual
2. **Análisis de datos** existentes para mapeo
3. **Creación de scripts** de migración
4. **Ambiente de testing** con estructura dual

### FASE 2: MIGRACIÓN DE DATOS (Core)
1. **Migrar `courses` → `ai_courses`**
   - Crear registros en `ai_subthemes` 
   - Mapear campos existentes
   - Mantener UUIDs para compatibilidad

2. **Migrar `course_modules` → `ai_course_sessions`**
   - Convertir módulos a sesiones
   - Mapear índices y duración
   - Mantener relaciones FK

3. **Crear datos complementarios**
   - Generar `ai_session_practices` basado en `module_exercises`
   - Crear `ai_session_deliverables` basado en `free_resources`

### FASE 3: ADAPTACIÓN DE CÓDIGO (Crítico)
1. **Servicios de base de datos**
2. **Herramientas de agente (35+)**
3. **Handlers y flujos**
4. **Plantillas y utilidades**

### FASE 4: TESTING Y VALIDACIÓN
1. **Testing de funcionalidades**
2. **Validación de herramientas**
3. **Pruebas de regresión**
4. **Testing de memoria de usuarios**

---

## MAPEO DETALLADO DE TABLAS

### 1. COURSES → AI_COURSES
```sql
-- MAPEO DIRECTO
courses.id                  → ai_courses.id
courses.name                → ai_courses.name
courses.short_description   → ai_courses.short_description
courses.long_description    → ai_courses.long_description
courses.price_usd           → ai_courses.price
courses.currency            → ai_courses.currency
courses.course_link         → ai_courses.course_url
courses.purchase_link       → ai_courses.purchase_url
courses.level               → ai_courses.level
courses.language            → ai_courses.language

-- CAMPOS NUEVOS (requeridos)
NULL                        → ai_courses.subtheme_id (FK a ai_subthemes)
0                           → ai_courses.session_count (calcular)
0                           → ai_courses.total_duration_min (calcular)
'básico'                    → ai_courses.level (por defecto)
'draft'                     → ai_courses.status (por defecto)
'general'                   → ai_courses.audience_category (por defecto)
NULL                        → ai_courses.start_date
NULL                        → ai_courses.end_date
0                           → ai_courses.max_enrollees

-- CAMPOS PERDIDOS (sin equivalencia)
courses.total_duration      → Convertir a minutos
courses.thumbnail_url       → Eliminado
courses.rating              → Eliminado
courses.reviews_count       → Eliminado
courses.published           → Usar en status
courses.tools_used          → Eliminado
courses.schedule            → Eliminado
courses.original_price_usd  → Eliminado
courses.discount_percentage → Eliminado
courses.discount_end_date   → Eliminado
courses.min_students        → Eliminado
courses.max_students        → Usar en max_enrollees
courses.prerequisites       → Eliminado
courses.requirements        → Eliminado
courses.meta_keywords       → Eliminado
courses.meta_description    → Eliminado
courses.syllabus_url        → Eliminado
courses.preview_url         → Eliminado
courses.resources_url       → Eliminado
```

### 2. COURSE_MODULES → AI_COURSE_SESSIONS
```sql
-- MAPEO DIRECTO
course_modules.id           → ai_course_sessions.id
course_modules.course_id    → ai_course_sessions.course_id
course_modules.module_index → ai_course_sessions.session_index
course_modules.name         → ai_course_sessions.title
course_modules.description  → ai_course_sessions.objective
course_modules.duration     → ai_course_sessions.duration_minutes (convertir)

-- CAMPOS NUEVOS (requeridos)
NULL                        → ai_course_sessions.scheduled_at
course_modules.module_index → ai_course_sessions.display_order
'online'                    → ai_course_sessions.modality (por defecto)
NULL                        → ai_course_sessions.resources_url
```

### 3. NUEVAS TABLAS A CREAR

#### AI_SUBTHEMES
```sql
-- Crear subtemas basados en categorías existentes
INSERT INTO ai_subthemes (name, description)
SELECT DISTINCT category, 'Subtema generado automáticamente'
FROM courses 
WHERE category IS NOT NULL;
```

#### AI_SESSION_PRACTICES
```sql
-- Migrar desde module_exercises
INSERT INTO ai_session_practices (session_id, practice_index, title, description)
SELECT 
    cm.id,                    -- session_id (módulo → sesión)
    me.order_idx,             -- practice_index
    'Práctica ' || me.order_idx, -- title
    me.description            -- description
FROM module_exercises me
JOIN course_modules cm ON me.module_id = cm.id;
```

#### AI_SESSION_DELIVERABLES
```sql
-- Crear desde free_resources
INSERT INTO ai_session_deliverables (session_id, name, type, resource_url)
SELECT 
    cm.id,                    -- session_id
    fr.resource_name,         -- name
    fr.resource_type,         -- type
    fr.resource_url           -- resource_url
FROM free_resources fr
JOIN course_modules cm ON fr.course_id = cm.course_id;
```

---

## ADAPTACIÓN DE CÓDIGO

### 1. SERVICIOS DE BASE DE DATOS

#### A. **core/services/database.py**
**Cambios requeridos:**
- `get_course_details()` → Actualizar JOIN con `ai_courses`, `ai_course_sessions`
- `get_lead_profile()` → Mantener (no cambia)
- `register_interaction()` → Mantener (no cambia)
- `update_lead_score()` → Mantener (no cambia)

#### B. **core/services/courseService.py**
**Cambios críticos:**
- `getCourseDetails()` → Cambiar tabla `courses` por `ai_courses`
- `getCourseModules()` → Cambiar tabla `course_modules` por `ai_course_sessions`
- `searchCourses()` → Actualizar campos de búsqueda
- `getCoursePrompts()` → ELIMINAR (tabla no existe en nueva estructura)
- `getModuleExercises()` → Cambiar por `ai_session_practices`

### 2. HERRAMIENTAS DE AGENTE (35+ TOOLS)

#### **core/agents/agent_tools.py**
**Herramientas afectadas:**

1. **mostrar_detalles_curso()** - Línea 24
   - Cambiar: `get_course_details()` → usar nueva estructura

2. **mostrar_preview_curso()** - Línea 62
   - Cambiar: campos de `courses` → `ai_courses`

3. **mostrar_syllabus_interactivo()** - Línea 95
   - Cambiar: `course_modules` → `ai_course_sessions`
   - Usar: `ai_session_practices` para prácticas

4. **mostrar_ofertas_limitadas()** - Línea 123
   - Mantener: `limited_time_bonuses` (no cambia)

5. **obtener_recursos_gratuitos()** - Línea 339
   - Cambiar: `free_resources` → `ai_session_deliverables`

6. **mostrar_comparativa_precios()** - Línea 407
   - Cambiar: campos de precio en `ai_courses`

7. **calcular_interes_usuario()** - Línea 622
   - Mantener: `course_interactions` (no cambia)

8. **mostrar_social_proof()** - Línea 986
   - Mantener: `course_sales` (no cambia)

**Todas las herramientas** que usan `get_course_details()` necesitan adaptación.

### 3. HANDLERS Y FLUJOS

#### **core/handlers/ads_flow.py**
- `getCourseDetails()` → usar nueva estructura
- `format_course_info()` → adaptar campos

#### **core/handlers/contact_flow.py**
- Consultas SELECT a `courses` → `ai_courses`
- Mantener funcionalidad de `user_leads`

#### **core/handlers/course_flow.py**
- Todas las consultas a `courses` → `ai_courses`
- Consultas a `course_modules` → `ai_course_sessions`

### 4. PLANTILLAS Y UTILIDADES

#### **core/utils/course_templates.py**
**Cambios en campos:**
- `courses.name` → `ai_courses.name`
- `courses.short_description` → `ai_courses.short_description`
- `courses.long_description` → `ai_courses.long_description`
- `courses.price_usd` → `ai_courses.price`
- `courses.level` → `ai_courses.level`

---

## RIESGOS Y MITIGACIONES

### RIESGOS CRÍTICOS

1. **Pérdida de funcionalidad en herramientas**
   - **Mitigación**: Testing exhaustivo de cada herramienta
   - **Contingencia**: Mantener ambiente de rollback

2. **Corrupción de memoria de usuarios**
   - **Mitigación**: Backup completo antes de migración
   - **Contingencia**: Scripts de recuperación

3. **Pérdida de historial de interacciones**
   - **Mitigación**: Mantener tablas de tracking intactas
   - **Contingencia**: Doble escritura temporal

4. **Queries complejas con JOINs**
   - **Mitigación**: Reescritura cuidadosa de consultas
   - **Contingencia**: Queries de compatibilidad

### MITIGACIONES IMPLEMENTADAS

1. **Ambiente dual**: Mantener ambas estructuras temporalmente
2. **Migración gradual**: Por componentes, no todo a la vez
3. **Testing continuo**: Validar cada funcionalidad
4. **Rollback plan**: Posibilidad de volver atrás rápidamente

---

## CRONOGRAMA DE EJECUCIÓN

### SEMANA 1: PREPARACIÓN
- [ ] Backup completo de base de datos
- [ ] Creación de ambiente de testing
- [ ] Scripts de migración de datos
- [ ] Análisis de datos existentes

### SEMANA 2: MIGRACIÓN DE DATOS
- [ ] Crear nueva estructura de tablas
- [ ] Migrar datos de `courses` → `ai_courses`
- [ ] Migrar datos de `course_modules` → `ai_course_sessions`
- [ ] Crear datos complementarios

### SEMANA 3: ADAPTACIÓN DE SERVICIOS
- [ ] Actualizar `database.py`
- [ ] Actualizar `courseService.py`
- [ ] Adaptar `supabase_service.py`
- [ ] Testing de servicios básicos

### SEMANA 4: ADAPTACIÓN DE HERRAMIENTAS
- [ ] Actualizar herramientas de agente (35+)
- [ ] Testing individual de cada herramienta
- [ ] Validar flujos de conversación
- [ ] Probar integración con OpenAI

### SEMANA 5: ADAPTACIÓN DE HANDLERS
- [ ] Actualizar ads_flow.py
- [ ] Actualizar contact_flow.py
- [ ] Actualizar course_flow.py
- [ ] Testing de flujos completos

### SEMANA 6: TESTING Y VALIDACIÓN
- [ ] Testing de regresión completo
- [ ] Validar memoria de usuarios
- [ ] Probar scoring de leads
- [ ] Testing de performance

### SEMANA 7: DEPLOYMENT
- [ ] Migración a producción
- [ ] Monitoring intensivo
- [ ] Ajustes finales
- [ ] Documentación actualizada

---

## CONSIDERACIONES ESPECIALES

### DATOS A PRESERVAR ABSOLUTAMENTE
1. **user_leads**: Memoria completa de usuarios
2. **conversations**: Historial de conversaciones
3. **course_interactions**: Tracking de interacciones
4. **course_sales**: Ventas completadas
5. **limited_time_bonuses**: Promociones activas

### FUNCIONALIDADES CRÍTICAS
1. **Hashtag detection**: `#CURSO_IA_CHATGPT` → mapeo a curso
2. **Memory system**: Auto-corrección de IDs de curso
3. **AI integration**: OpenAI GPT-4o-mini con context
4. **Lead scoring**: Scoring dinámico basado en interacciones
5. **Conversion tools**: 35+ herramientas funcionando

### COMPATIBILIDAD CON EXISTENTE
- Mantener UUIDs de cursos para compatibilidad
- Preservar estructura de `user_leads` intacta
- Mantener APIs de servicios existentes
- Conservar formato de memoria JSON

---

## SCRIPTS DE MIGRACIÓN

### 1. MIGRACIÓN DE DATOS
```sql
-- Crear subtemas
INSERT INTO ai_subthemes (id, name, description)
SELECT gen_random_uuid(), 
       COALESCE(category, 'General'), 
       'Subtema migrado automáticamente'
FROM (SELECT DISTINCT category FROM courses WHERE category IS NOT NULL) t;

-- Migrar cursos
INSERT INTO ai_courses (
    id, subtheme_id, name, short_description, long_description,
    session_count, total_duration_min, price, currency, course_url,
    purchase_url, level, language, audience_category, status,
    max_enrollees, created_at
)
SELECT 
    c.id,
    st.id,
    c.name,
    c.short_description,
    c.long_description,
    COALESCE((SELECT COUNT(*) FROM course_modules WHERE course_id = c.id), 0),
    COALESCE(EXTRACT(EPOCH FROM c.total_duration)/60, 0),
    c.price_usd,
    c.currency,
    c.course_link,
    c.purchase_link,
    c.level,
    c.language,
    COALESCE(c.category, 'general'),
    CASE WHEN c.published THEN 'publicado' ELSE 'borrador' END,
    c.max_students,
    c.created_at
FROM courses c
LEFT JOIN ai_subthemes st ON st.name = COALESCE(c.category, 'General');

-- Migrar sesiones
INSERT INTO ai_course_sessions (
    id, course_id, session_index, title, objective,
    duration_minutes, display_order, modality, created_at
)
SELECT 
    id,
    course_id,
    module_index,
    name,
    description,
    COALESCE(EXTRACT(EPOCH FROM duration)/60, 0),
    module_index,
    'online',
    created_at
FROM course_modules;
```

### 2. VALIDACIÓN DE MIGRACIÓN
```sql
-- Verificar integridad de datos
SELECT 
    (SELECT COUNT(*) FROM courses) as courses_orig,
    (SELECT COUNT(*) FROM ai_courses) as courses_new,
    (SELECT COUNT(*) FROM course_modules) as modules_orig,
    (SELECT COUNT(*) FROM ai_course_sessions) as sessions_new;

-- Verificar FKs
SELECT c.id, c.name, s.session_count, actual.cnt
FROM ai_courses c
LEFT JOIN (
    SELECT course_id, COUNT(*) as cnt 
    FROM ai_course_sessions 
    GROUP BY course_id
) actual ON c.id = actual.course_id
WHERE c.session_count != COALESCE(actual.cnt, 0);
```

---

## CONCLUSIÓN

Esta migración es **crítica y compleja**, afectando todos los componentes del bot. La estrategia propuesta minimiza riesgos mediante:

1. **Migración gradual** por componentes
2. **Preservación de datos críticos** (user_leads, interactions)
3. **Testing exhaustivo** de cada funcionalidad
4. **Plan de rollback** completo
5. **Monitoring intensivo** post-migración

**Estimación total**: 7 semanas de trabajo intensivo con equipo dedicado.

**Recomendación**: Ejecutar en ambiente de desarrollo primero, con testing extensivo antes de producción.