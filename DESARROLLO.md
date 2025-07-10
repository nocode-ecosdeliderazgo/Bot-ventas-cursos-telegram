# Guía de Desarrollo - Bot Ventas IA "Brenda"

**Estado**: ✅ **100% FUNCIONAL - PRODUCTION READY**  
**Última actualización**: Julio 2025

## 🎯 Estado Actual del Desarrollo

### ✅ **SISTEMA COMPLETAMENTE IMPLEMENTADO**
- 🤖 **Bot principal**: Funcional con detección inteligente hashtags
- 🧠 **Agente IA**: OpenAI GPT-4o-mini integrado y operativo
- 🛠️ **35+ Herramientas**: Todas implementadas enviando recursos reales
- 💾 **Base de Datos**: PostgreSQL completamente migrada
- 📱 **Flujos**: Ads, contacto, cursos - todos operativos
- 🎯 **Recursos**: URLs y archivos enviándose correctamente

## 🚀 Setup de Desarrollo

### **Prerrequisitos**
- Python 3.10+
- PostgreSQL 13+
- Cuenta OpenAI con API key
- Bot de Telegram configurado

### **Instalación Rápida**
```bash
# Clonar y navegar
git clone [repo-url]
cd Bot-ventas-cursos-telegram

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# O en Windows:
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Ejecutar bot
python agente_ventas_telegram.py
```

### **Variables de Entorno Críticas**
```env
# Bot de Telegram
TELEGRAM_API_TOKEN=tu_token_aqui

# Base de datos
DATABASE_URL=postgresql://user:pass@host:port/database

# OpenAI para IA conversacional
OPENAI_API_KEY=sk-proj-tu-key-aqui

# Email para notificaciones
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu_email@gmail.com
SMTP_PASSWORD=tu_app_password
ADVISOR_EMAIL=asesor@empresa.com

# Supabase (opcional)
SUPABASE_URL=tu_url_supabase
SUPABASE_KEY=tu_key_supabase
```

## 🏗️ Arquitectura del Sistema

### **Componentes Principales**
```
agente_ventas_telegram.py     # Entry point - gestión Telegram
├── core/agents/              # Sistema de agentes IA
│   ├── smart_sales_agent.py  # Orquestador principal
│   ├── intelligent_sales_agent.py # Motor IA OpenAI
│   └── agent_tools.py        # 35+ herramientas conversión
├── core/services/            # Servicios backend
│   ├── database.py           # PostgreSQL con asyncpg
│   ├── courseService.py      # Gestión cursos
│   └── resourceService.py    # Gestión recursos multimedia
├── core/handlers/            # Manejadores flujos
│   ├── ads_flow.py           # Flujo anuncios hashtag→conversión
│   ├── contact_flow.py       # Contacto asesor directo
│   └── course_flow.py        # Exploración cursos
└── core/utils/               # Utilidades
    ├── memory.py             # Sistema memoria JSON
    ├── message_parser.py     # Análisis hashtags
    └── lead_scorer.py        # Scoring dinámico leads
```

### **Flujo de Datos**
```
Usuario → Telegram → Bot Principal → Smart Sales Agent
                                       ↓
                              Intelligent Sales Agent (OpenAI)
                                       ↓
                              Agent Tools (35+ herramientas)
                                       ↓
                              Database Service → PostgreSQL
```

## 🛠️ Testing y Validación

### **Tests Automatizados**
```bash
# Test configuración entorno
python test_env.py

# Test integración completa
python test_integration.py

# Test funcionalidad agentes
python verificar_agentes.py

# Test servicios BD
python verificar_servicios.py

# Testing automatizado avanzado
python testing_automation/simple_tester.py
```

### **Flujo de Testing Manual**
```
1. Enviar: "#Experto_IA_GPT_Gemini #ADSIM_05"
   ✅ Debe detectar hashtags y activar ads_flow

2. Aceptar privacidad
   ✅ Debe solicitar nombre personalizado

3. Proporcionar nombre: "María González"
   ✅ Debe enviar PDF + imagen + info curso

4. Preguntar: "Tienen recursos gratuitos?"
   ✅ Debe enviar PDFs inmediatamente

5. Preguntar: "Quiero ver el temario"
   ✅ Debe enviar syllabus PDF

6. Decir: "Está muy caro"
   ✅ Debe mostrar comparativa precios

7. Preguntar: "Quiero hablar con alguien"
   ✅ Debe activar flujo contacto asesor
```

## 📊 Base de Datos

### **Estructura Principal**
```sql
-- Cursos y contenido
ai_courses              -- Catálogo principal
ai_course_sessions      -- Sesiones por curso
ai_tematarios          -- Temarios detallados

-- Recursos multimedia
bot_resources          -- URLs archivos
bot_course_resources   -- Recursos por curso
free_resources         -- Materiales gratis

-- Gestión usuarios
user_leads            -- Info leads
course_interactions   -- Tracking
conversations         -- Historial
```

### **Comandos Útiles BD**
```sql
-- Ver cursos disponibles
SELECT course_id, name, price_usd FROM ai_courses;

-- Ver interacciones recientes
SELECT * FROM course_interactions 
ORDER BY created_at DESC LIMIT 10;

-- Ver memoria usuario específico
SELECT * FROM conversations 
WHERE user_id = '12345' 
ORDER BY created_at DESC;
```

## 🔧 Desarrollo de Nuevas Funcionalidades

### **Agregar Nueva Herramienta**
```python
# En core/agents/agent_tools.py

async def mi_nueva_herramienta(self, user_id: str, course_id: str) -> Dict[str, Union[str, List[Dict]]]:
    """
    Nueva herramienta de conversión.
    
    Args:
        user_id: ID del usuario
        course_id: ID del curso
        
    Returns:
        Dict con type, content y resources
    """
    try:
        # Lógica de la herramienta
        mensaje = "Contenido de la herramienta"
        
        # Recursos multimedia (opcional)
        resources = [
            {
                "type": "document",
                "url": "https://ejemplo.com/archivo.pdf",
                "caption": "Descripción del archivo"
            }
        ]
        
        # Registrar interacción
        await self._registrar_interaccion(
            user_id, course_id, "nueva_herramienta", 
            {"descripcion": "descripcion_accion"}
        )
        
        return {
            "type": "multimedia",  # o "text"
            "content": mensaje,
            "resources": resources  # opcional para type="text"
        }
        
    except Exception as e:
        logger.error(f"Error en mi_nueva_herramienta: {e}")
        return {
            "type": "text",
            "content": "Error procesando solicitud"
        }
```

### **Agregar Nuevo Flujo**
```python
# En core/handlers/mi_nuevo_flow.py

class MiNuevoFlowHandler:
    def __init__(self, db_service, agent_tools):
        self.db = db_service
        self.agent_tools = agent_tools
    
    async def handle_flow(self, message_data: dict, user_data: dict):
        """Maneja el nuevo flujo"""
        try:
            # Lógica del flujo
            response = "Respuesta del flujo"
            keyboard = None  # Opcional
            
            return response, keyboard
            
        except Exception as e:
            logger.error(f"Error en nuevo flujo: {e}")
            return "Error procesando flujo", None
```

### **Integrar Nuevo Flujo en Bot Principal**
```python
# En agente_ventas_telegram.py

# Importar el handler
from core.handlers.mi_nuevo_flow import MiNuevoFlowHandler

# En __init__
self.mi_nuevo_flow = MiNuevoFlowHandler(self.db, self.agent_tools)

# En handle_message
if condicion_para_nuevo_flujo:
    response, keyboard = await self.mi_nuevo_flow.handle_flow(
        message_data, user_data
    )
```

## 🚀 Deployment

### **Preparación para Producción**
```bash
# Verificar configuración
python test_env.py

# Verificar funcionalidad completa
python test_integration.py

# Backup base de datos
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Configurar logging producción
# Editar logging level en agente_ventas_telegram.py
```

### **Variables Entorno Producción**
```env
# Modo producción
DEBUG=False
LOG_LEVEL=INFO

# Base datos producción
DATABASE_URL=postgresql://prod_user:prod_pass@prod_host:5432/prod_db

# APIs producción
OPENAI_API_KEY=sk-prod-key-aqui
TELEGRAM_API_TOKEN=prod_bot_token

# Monitoring
SENTRY_DSN=tu_sentry_dsn  # Opcional para monitoring errores
```

## 📈 Optimizaciones de Performance

### **Caching**
```python
# Implementar caching para consultas frecuentes
import functools
from datetime import datetime, timedelta

@functools.lru_cache(maxsize=100)
async def get_course_cached(course_id: str):
    """Cache información del curso por 1 hora"""
    return await database.get_course_details(course_id)
```

### **Async Optimization**
```python
# Usar gather para operaciones paralelas
import asyncio

async def multiple_operations():
    results = await asyncio.gather(
        database.get_course_details(course_id),
        database.get_user_memory(user_id),
        resource_service.get_course_resources(course_id)
    )
    return results
```

## 🔍 Debugging y Troubleshooting

### **Logs Importantes**
```bash
# Ver logs en tiempo real
tail -f bot.log

# Filtrar errores
grep ERROR bot.log

# Ver memoria específica usuario
cat memorias/memory_12345.json | jq .
```

### **Problemas Comunes**

**Bot no responde:**
```bash
# Verificar token
python -c "import os; print(os.getenv('TELEGRAM_API_TOKEN'))"

# Test conexión BD
python test_env.py
```

**Herramientas no activan:**
```python
# Debug en intelligent_sales_agent.py
logger.info(f"Intención detectada: {intent_analysis}")
logger.info(f"Herramientas activadas: {tools_used}")
```

**OpenAI errores:**
```python
# Verificar quota y key
import openai
try:
    response = openai.chat.completions.create(...)
    print("OpenAI funcionando")
except Exception as e:
    print(f"Error OpenAI: {e}")
```

## 🎯 Próximas Mejoras

### **Roadmap Técnico**
1. **Analytics Dashboard** - Métricas en tiempo real
2. **A/B Testing** - Testing automático mensajes
3. **CRM Integration** - HubSpot/Salesforce
4. **ML Optimization** - Predicción probabilidad compra
5. **Multi-channel** - WhatsApp, Instagram

### **Optimizaciones Performance**
1. **Database**: Índices adicionales, partitioning
2. **Caching**: Redis para cache distribuido
3. **CDN**: Para recursos multimedia
4. **Load Balancing**: Para múltiples instancias

### **Funcionalidades Avanzadas**
1. **Voice Messages**: Transcripción y respuesta
2. **Image Recognition**: Análisis imágenes usuario
3. **Sentiment Analysis**: Detección emocional avanzada
4. **Predictive Scoring**: ML para scoring leads

## 📚 Recursos Adicionales

### **Documentación**
- `README.md` - Guía usuario final
- `CLAUDE.md` - Contexto completo proyecto
- `SISTEMA_HERRAMIENTAS_UNIFICADO_FINAL.md` - Doc técnica

### **Testing**
- `testing_automation/` - Suite testing automatizado
- `test_*.py` - Tests específicos componentes

### **Configuración**
- `.env.example` - Template variables entorno
- `config/settings.py` - Configuración Pydantic

---

**El sistema está 100% funcional y listo para generar ventas inmediatamente. Esta guía cubre todo lo necesario para desarrollo continuo y optimización.** 