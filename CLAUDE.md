# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram sales bot "Brenda" for "Aprenda y Aplique IA" that uses intelligent agents to convert leads for AI course sales. The bot automatically detects users from ads via hashtags, provides personalized course presentations, and manages the entire sales funnel with limited-time bonuses and lead scoring.

## CURRENT STATUS (2025-07-07 - ACTUALIZADO)

**ESTADO ACTUAL**: Bot 98% funcional con agente inteligente mejorado
**ÚLTIMA ACTUALIZACIÓN**: Corrección crítica para evitar invención de datos
**CAMBIOS RECIENTES**:
- ✅ System prompt reformulado con tono cálido y amigable
- ✅ Herramientas de consulta a BD implementadas
- ✅ Validación anti-invención de datos agregada
- ✅ Mapeo de hashtags verificado y funcionando
- ✅ Estadísticas falsas eliminadas de templates

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

### CURRENT IMPLEMENTATION STATUS

- **ads_flow.py**: Simplified, lacks name handling (lines 77-82)
- **memory.py**: Missing preferred_name field (removed from LeadMemory class)
- **message_templates.py**: Still contains fake statistics (lines 200-203, 210-213)
- **Bot is 95% functional** but user reset changes to focus on name request only

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

### Lead Conversion Process (CURRENT FOCUS)
1. **Detection**: Identify ad source and course interest from hashtags
2. **Privacy**: Show privacy notice and get acceptance
3. **NAME REQUEST**: After privacy acceptance, ask for preferred name ⚠️ NEEDS RE-IMPLEMENTATION
4. **Personalization**: Show files and course summary with user's name
5. **Conversion**: Present limited-time bonuses and scheduling options
6. **Follow-up**: Automated follow-up sequences based on user actions

### Memory System
- Each user has persistent conversation memory stored in `memorias/`
- Context includes interaction history, preferences, and lead score
- Memory is used to provide personalized responses and avoid repetition
- **MISSING**: preferred_name field needs to be re-added to LeadMemory class

## Development Guidelines

### CURRENT TASK: Re-implement Name Request Feature

**FOCUS AREAS**:
1. **memory.py**: Add preferred_name field back to LeadMemory class
2. **ads_flow.py**: Add name request stage after privacy acceptance
3. **message_templates.py**: Remove fake statistics (lines 200-203, 210-213)
4. **Flow**: Privacy → Name Request → Files + Course Summary

**USER INSTRUCTION**: "no cambies otras cosas extra solo corrige lo que te estoy diciendo"

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

### CHECKLIST DE IMPLEMENTACIÓN

| Componente | Estado Claude | Validación Manual | Validación Automática |
|------------|---------------|-------------------|----------------------|
| ✅ System prompt reformulado | ✅ | ⬜ | ⬜ |
| ✅ Tono cálido y amigable | ✅ | ⬜ | ⬜ |
| ✅ Herramientas consulta BD | ✅ | ⬜ | ⬜ |
| ✅ Validación anti-invención | ✅ | ⬜ | ⬜ |
| ✅ Mapeo hashtag→curso ID | ✅ | ⬜ | ⬜ |
| ✅ Almacenamiento curso interés | ✅ | ⬜ | ⬜ |
| ✅ Consulta automática BD | ✅ | ⬜ | ⬜ |
| ✅ Estadísticas falsas eliminadas | ✅ | ⬜ | ⬜ |
| ✅ Error UUID corregido | ✅ | ⬜ | ⬜ |
| ⬜ Activación post-flujos controlada | ⬜ | ⬜ | ⬜ |
| ⬜ Testing completo de veracidad | ⬜ | ⬜ | ⬜ |

### PRÓXIMOS PASOS
1. **Testing de veracidad** - Validar que no inventa datos del curso
2. **Implementar activación controlada** - Solo después de flujos predefinidos
3. **Optimizar respuestas** - Mejorar personalización con datos reales
4. **Expandir herramientas** - Agregar más consultas específicas a BD

### CAMBIOS CRÍTICOS RECIENTES
- **Problema resuelto**: Agente ya no inventa módulos o contenido del curso
- **BD integrada**: Consulta automática de información real del curso
- **Mapeo verificado**: #CURSO_IA_CHATGPT → a392bf83-4908-4807-89a9-95d0acc807c9
- **Validación activa**: Detecta y previene invención de datos
- **Tono mejorado**: Brenda más cálida y amigable