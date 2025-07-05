# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram sales bot that uses intelligent agents to convert leads for AI course sales. The bot automatically detects users from ads via hashtags, provides personalized course presentations, and manages the entire sales funnel with limited-time bonuses and lead scoring.

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

### Lead Conversion Process
1. **Detection**: Identify ad source and course interest from hashtags
2. **Scoring**: Calculate lead score based on interactions and behavior
3. **Personalization**: Provide course-specific presentations and offers
4. **Conversion**: Present limited-time bonuses and scheduling options
5. **Follow-up**: Automated follow-up sequences based on user actions

### Memory System
- Each user has persistent conversation memory stored in `memorias/`
- Context includes interaction history, preferences, and lead score
- Memory is used to provide personalized responses and avoid repetition

## Development Guidelines

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