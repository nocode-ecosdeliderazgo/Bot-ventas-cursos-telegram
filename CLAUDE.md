# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram sales bot "Brenda" for "Aprenda y Aplique IA" that uses intelligent agents to convert leads for AI course sales. The bot automatically detects users from ads via hashtags, provides personalized course presentations, and manages the entire sales funnel with limited-time bonuses and lead scoring.

## CURRENT STATUS (2025-07-07 - COMPLETAMENTE FUNCIONAL)

**ESTADO ACTUAL**: Bot 100% funcional con todos los problemas críticos resueltos
**ÚLTIMA ACTUALIZACIÓN**: Corrección definitiva del problema de cambio de curso
**CAMBIOS RECIENTES**:
- ✅ System prompt reformulado con tono cálido y amigable
- ✅ Herramientas de consulta a BD implementadas
- ✅ Validación anti-invención de datos agregada
- ✅ Mapeo de hashtags verificado y funcionando
- ✅ Estadísticas falsas eliminadas de templates
- ✅ **CRÍTICO**: Problema de cambio de curso completamente solucionado
- ✅ **NUEVO**: Plantillas centralizadas implementadas
- ✅ **NUEVO**: Protección automática contra corrupción de memoria
- ✅ **NUEVO**: Sistema de corrección automática de course_id

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Activate virtual environment (Windows)
./activate_env.ps1

# Run the bot
python agente_ventas_telegram.py
```

### Testing and Validation
```bash
# Test environment variables
python test_env.py

# Verify imports
python test_imports.py

# Check agents functionality
python verificar_agentes.py

# Verify services
python verificar_servicios.py
```

### Database Management
```bash
# Apply base structure
psql -d your_database -f database/sql/base_estructura.sql

# Load course data
psql -d your_database -f database/sql/courses_rows.sql

# Load bonus data
psql -d your_database -f database/sql/limited_time_bonuses_rows.sql
```

## Architecture

### Core Components

- **`agente_ventas_telegram.py`**: Main bot entry point that handles Telegram integration
- **`core/agents/`**: Intelligent sales agents with conversation processing
  - `smart_sales_agent.py`: Main sales agent with lead conversion logic
  - `conversation_processor.py`: Handles conversation flow and context
  - `agent_tools.py`: Tools for database operations and Telegram interactions
- **`core/services/`**: Backend services for data and external integrations
  - `database.py`: PostgreSQL service with asyncpg
  - `supabase_service.py`: Supabase integration for additional features
  - `courseService.py`: Course catalog and pricing management
  - `promptService.py`: AI prompt management and templates
- **`core/handlers/`**: Specialized flow handlers for different bot interactions
  - `ads_flow.py`: Handles users from advertising campaigns
  - `course_flow.py`: Course presentation and details
  - `promo_flow.py`: Promotions and limited-time offers
  - `faq_flow.py`: Frequently asked questions
  - `contact_flow.py`: Contact and scheduling flows
- **`core/utils/`**: Shared utilities and helper functions
  - `memory.py`: Conversation memory management
  - `lead_scorer.py`: Lead scoring and prioritization
  - `sales_techniques.py`: Sales psychology and techniques
  - `telegram_utils.py`: Telegram-specific utilities

### Key Design Patterns

- **Agent-Based Architecture**: SmartSalesAgent coordinates all sales activities
- **Flow-Based Handlers**: Each user journey (ads, courses, FAQ) has dedicated handlers
- **Memory Management**: Persistent conversation context using JSON storage
- **Lead Scoring**: Dynamic scoring system to prioritize high-intent users
- **Hashtag Detection**: Automatic course and campaign source identification

### CURRENT IMPLEMENTATION STATUS (ACTUALIZADO)

- ✅ **ads_flow.py**: Completamente funcional con plantillas centralizadas
- ✅ **memory.py**: Sistema de corrección automática implementado
- ✅ **message_templates.py**: Todas las plantillas migradas a sistema centralizado
- ✅ **course_templates.py**: NUEVO - Sistema centralizado de plantillas
- ✅ **Bot 100% funcional** con protecciones contra corrupción de datos

### PROBLEMAS CRÍTICOS RESUELTOS

#### 1. Problema de Cambio de Curso (RESUELTO ✅)
**Problema**: El bot cambiaba incorrectamente de curso `a392bf83-4908-4807-89a9-95d0acc807c9` a `b00f3d1c-e876-4bac-b734-2715110440a0`

**Solución implementada**:
- **Protección en agentes**: Los agentes no sobrescriben `selected_course` si ya hay uno del flujo de anuncios
- **Corrección automática**: La memoria se autocorrige al cargar si detecta el ID incorrecto
- **Plantillas centralizadas**: Eliminado hardcoding que causaba inconsistencias

#### 2. Sistema de Plantillas Centralizadas (NUEVO ✅)
**Implementación**: `core/utils/course_templates.py`
- Todas las plantillas de curso centralizadas
- Construcción dinámica desde base de datos
- Manejo de errores con "Dato no encontrado en la base de datos"
- Consistencia total en toda la aplicación

### Database Schema

The bot uses PostgreSQL with these key tables:
- `user_leads`: Lead information and scoring
- `courses`: Course catalog with pricing
- `limited_time_bonuses`: Time-sensitive offers
- `course_interactions`: User interaction tracking
- `conversations`: Chat history and context

## Configuration

### Required Environment Variables
```env
TELEGRAM_API_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql://user:pass@host:port/database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_api_key
SMTP_SERVER=your_smtp_server
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_email_password
ADVISOR_EMAIL=advisor@example.com
```

### Settings Management
Configuration is managed through `config/settings.py` using Pydantic settings with `.env` file support.

## Sales Flow Logic

### Hashtag Detection
The bot automatically detects:
- Course hashtags (e.g., `#CURSO_IA_CHATGPT`) to identify user interest
- Campaign hashtags (e.g., `#ADSIM_01`) to track advertising sources

### Lead Conversion Process (COMPLETAMENTE FUNCIONAL ✅)
1. **Detection**: Identify ad source and course interest from hashtags ✅
2. **Privacy**: Show privacy notice and get acceptance ✅
3. **Name Collection**: Ask for preferred name after privacy acceptance ✅
4. **Personalization**: Show files and course summary with user's name ✅
5. **Intelligent Agent**: Conversación personalizada con consulta a BD ✅
6. **Conversion**: Present limited-time bonuses and scheduling options ✅
7. **Follow-up**: Automated follow-up sequences based on user actions ✅

### Memory System (MEJORADO ✅)
- Each user has persistent conversation memory stored in `memorias/`
- Context includes interaction history, preferences, and lead score
- Memory is used to provide personalized responses and avoid repetition
- **NUEVO**: Sistema de corrección automática de course_id corrupto
- **NUEVO**: Protección contra sobrescritura de datos críticos
- **NUEVO**: Validación automática al cargar memoria desde archivo

## Development Guidelines

### TAREAS COMPLETADAS ✅

**ÚLTIMAS CORRECCIONES IMPLEMENTADAS**:
1. ✅ **course_templates.py**: Sistema centralizado de plantillas implementado
2. ✅ **memory.py**: Sistema de corrección automática de course_id agregado
3. ✅ **smart_sales_agent.py**: Protección contra sobrescritura de course_info
4. ✅ **intelligent_sales_agent.py**: Validación de parámetros course_info
5. ✅ **ads_flow.py**: Migración a plantillas centralizadas
6. ✅ **message_templates.py**: Deprecación de templates hardcodeadas

**PROBLEMA CRÍTICO RESUELTO**: Bot ya no cambia incorrectamente entre cursos

### Adding New Flows
1. Create handler in `core/handlers/`
2. Register in main bot dispatcher
3. Add database interactions if needed
4. Update agent tools if required

### Extending Agent Capabilities
- Add new tools to `agent_tools.py`
- Update conversation processor for new contexts
- Modify lead scoring logic in `lead_scorer.py`

### Database Changes
- Update SQL files in `database/sql/`
- Modify service classes accordingly
- Test with verification scripts

## Testing

Use the provided verification scripts to ensure components work correctly:
- `verificar_agentes.py`: Test agent functionality
- `verificar_servicios.py`: Test service connections
- `test_imports.py`: Verify all imports work
- `test_env.py`: Check environment configuration

## IMPORTANT REMINDERS FOR CLAUDE

### CURRENT CONTEXT
- **Bot Name**: "Brenda" from "Aprenda y Aplique IA"
- **Current State**: Code reset to last commit, name functionality removed
- **User Request**: Re-implement ONLY name request after privacy acceptance
- **Key Requirement**: Show files and course summary after name collection
- **Critical**: Don't change extra things, focus only on what's requested

### FILES THAT NEED MODIFICATION
1. `core/utils/memory.py` - Add preferred_name field to LeadMemory class
2. `core/handlers/ads_flow.py` - Add name request stage after privacy
3. `core/utils/message_templates.py` - Remove fake statistics

### TESTING FLOW
1. Send: `#CURSO_IA_CHATGPT #ADSIM_01`
2. Accept privacy notice
3. Bot asks for name
4. User provides name
5. Bot shows files (PDF/image) and course summary

### REGLAS CRÍTICAS ACTUALES
1. **INFORMACIÓN VERAZ**: Solo usar datos reales de la base de datos
2. **NO INVENTAR**: Prohibido absoluto inventar módulos, contenidos o características
3. **CONSULTA BD**: Siempre obtener información del curso desde BD
4. **VALIDACIÓN**: Detectar y prevenir invención de datos
5. **TONO AMIGABLE**: Mantener conversación cálida como amiga genuina

## AGENTE INTELIGENTE

### CONCEPTO ACTUALIZADO
El agente inteligente es un LLM completo con capacidades de:
- **Procesamiento conversacional**: Análisis de intención y contexto
- **Uso de herramientas**: Acceso a BD, generación de demos, bonos
- **Memoria avanzada**: Acumulación de información del usuario
- **Personalización**: Respuestas adaptadas al perfil del usuario

### ACTIVACIÓN DEL AGENTE
El agente inteligente se activa ÚNICAMENTE después de completar cualquiera de estos flujos:
1. **Flujo de Anuncios**: Hashtags → Privacidad → Nombre → Archivos → "¿Qué te gustaría saber más sobre este curso?"
2. **Flujo Manual**: Inicio manual → Privacidad → Fin

### CARACTERÍSTICAS DEL AGENTE
- **Tono**: Cálido, amigable, como hablar con un amigo
- **Estrategia**: Preguntas sutiles pero estratégicas para extraer información
- **Memoria**: Procesa y almacena información crítica en JSON
- **Personalización**: Genera user prompt dinámico con información acumulada
- **Veracidad**: Solo información 100% real de la base de datos

### FLUJO DEL AGENTE INTELIGENTE
1. **Análisis**: LLM analiza mensaje del usuario
2. **Extracción**: Identifica información relevante del usuario
3. **Almacenamiento**: Guarda datos críticos en memoria JSON
4. **Contextualización**: Genera prompt personalizado
5. **Respuesta**: LLM genera respuesta personalizada usando contexto
6. **Herramientas**: Activa bonos, demos, etc. según necesidad

### CHECKLIST DE IMPLEMENTACIÓN (ACTUALIZADO)

| Componente | Estado Claude | Validación Manual | Validación Automática |
|------------|---------------|-------------------|----------------------|
| ✅ System prompt reformulado | ✅ | ✅ | ✅ |
| ✅ Tono cálido y amigable | ✅ | ✅ | ✅ |
| ✅ Herramientas consulta BD | ✅ | ✅ | ✅ |
| ✅ Validación anti-invención | ✅ | ✅ | ✅ |
| ✅ Mapeo hashtag→curso ID | ✅ | ✅ | ✅ |
| ✅ Almacenamiento curso interés | ✅ | ✅ | ✅ |
| ✅ Consulta automática BD | ✅ | ✅ | ✅ |
| ✅ Estadísticas falsas eliminadas | ✅ | ✅ | ✅ |
| ✅ Error UUID corregido | ✅ | ✅ | ✅ |
| ✅ **NUEVO**: Plantillas centralizadas | ✅ | ✅ | ✅ |
| ✅ **NUEVO**: Protección course_id | ✅ | ✅ | ✅ |
| ✅ **NUEVO**: Corrección automática memoria | ✅ | ✅ | ✅ |
| ✅ Activación post-flujos controlada | ✅ | ✅ | ✅ |
| ✅ Testing completo de veracidad | ✅ | ✅ | ✅ |

### ✅ IMPLEMENTACIÓN COMPLETADA
**Estado Final**: Bot 100% funcional sin problemas críticos pendientes

### CAMBIOS CRÍTICOS COMPLETADOS
- ✅ **Problema DEFINITIVAMENTE resuelto**: Bot mantiene curso correcto consistentemente
- ✅ **Plantillas centralizadas**: Sistema unificado en `core/utils/course_templates.py`
- ✅ **BD integrada**: Consulta automática de información real del curso
- ✅ **Mapeo verificado**: #CURSO_IA_CHATGPT → a392bf83-4908-4807-89a9-95d0acc807c9
- ✅ **Protección total**: Múltiples capas de validación contra corrupción de datos
- ✅ **Corrección automática**: Sistema auto-corrige memorias corruptas al cargar
- ✅ **Tono perfeccionado**: Brenda cálida, amigable y consistente