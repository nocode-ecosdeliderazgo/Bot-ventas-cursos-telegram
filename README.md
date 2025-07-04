# Bot de Ventas con IA para Telegram

Bot inteligente para la venta automatizada de cursos de IA, con agentes de ventas personalizados y seguimiento de leads.

## 📁 Estructura del Proyecto

```
Bot_ventas/
├── 🤖 agente_ventas_telegram.py    # Archivo principal del bot
├── 📊 database/                    # Datos y estructura de BD
│   └── sql/                       
│       ├── base_estructura.sql    # Estructura completa de la BD
│       ├── courses_data.sql       # Datos de los cursos
│       └── course_assets.sql      # Assets y recursos
├── 🔧 core/                       # Módulo principal
│   ├── 🤖 agents/                 # Agentes inteligentes
│   │   ├── sales_agent.py         # Agente principal de ventas
│   │   └── agent_tools.py         # Herramientas del agente
│   ├── 🛠️ services/               # Servicios de backend
│   │   ├── database.py            # Servicio de PostgreSQL
│   │   └── supabase_service.py    # Servicio de Supabase
│   ├── 📋 handlers/               # Manejadores de flujos
│   │   ├── ads_flow.py           # Flujo de anuncios
│   │   ├── auth_flow.py          # Autenticación
│   │   ├── course_flow.py        # Flujo de cursos
│   │   ├── faq_flow.py           # FAQ
│   │   ├── contact_flow.py       # Contacto
│   │   ├── promo_flow.py         # Promociones
│   │   └── menu_handlers.py      # Menús principales
│   └── 🔧 utils/                  # Utilidades
│       ├── message_parser.py     # Parser de mensajes
│       ├── lead_scorer.py        # Scorer de leads
│       └── telegram_utils.py     # Utils de Telegram
├── ⚙️ config/                     # Configuración
│   └── settings.py              
├── 💾 data/                       # Archivos de datos
│   ├── imagen_prueba.jpg
│   ├── pdf_prueba.pdf
│   └── plantillas.json
├── 🧠 memorias/                   # Memoria de conversaciones
│   ├── memory_.json
│   └── memory_8101815097.json
└── 📝 Documentación/
    ├── plan de mejora.md
    └── RESUMEN_BOT.md
```

## 🚀 Funcionalidades Principales

### 🎯 Agente de Ventas Inteligente
- **Detección automática** de usuarios provenientes de anuncios
- **Seguimiento personalizado** basado en interacciones
- **Score de interés** dinámico para priorizar leads
- **Ofertas limitadas** con urgencia y escasez

### 🔍 Análisis de Hashtags
- Detección automática de curso de interés (#CURSO_IA_CHATGPT)
- Identificación de fuente publicitaria (#ADSIM_01)
- Mapeo inteligente a cursos en base de datos

### 💼 Herramientas de Conversión
- **Presentación atractiva** de cursos con thumbnails
- **Videos preview** para demostrar calidad
- **Bonos exclusivos** con tiempo y cupos limitados
- **Comparativas de precio** y valor total
- **Testimonios relevantes** según perfil del usuario
- **Opciones de pago flexibles**

### 📊 Seguimiento y Analytics
- Registro completo de interacciones
- Scoring automático de leads
- Programación de seguimientos
- Métricas de conversión por fuente

## 💾 Base de Datos

### Tablas Principales
- **user_leads**: Información completa de leads
- **courses**: Catálogo de cursos con precios y descuentos
- **limited_time_bonuses**: Bonos con tiempo y cupos limitados
- **course_interactions**: Tracking de todas las interacciones
- **conversations**: Historial de conversaciones
- **course_sales**: Registro de ventas cerradas

### Características Avanzadas
- **Triggers automáticos** para actualizar contadores
- **Constraints** para integridad de datos
- **Índices optimizados** para consultas rápidas
- **RLS (Row Level Security)** para seguridad

## 🔧 Instalación y Configuración

### Variables de Entorno Requeridas
```env
TELEGRAM_TOKEN=tu_token_de_telegram
DATABASE_URL=postgresql://user:pass@host:port/database
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_key_de_supabase
```

### Dependencias
```bash
pip install python-telegram-bot asyncpg supabase python-dotenv
```

### Ejecución
```bash
python agente_ventas_telegram.py
```

## 📈 Flujo de Ventas

### 1. Detección de Lead
```
Usuario envía: "Hola, vengo de Facebook por el curso de IA #CURSO_IA_CHATGPT #ADSIM_01"
  ↓
Bot detecta hashtags y identifica:
- Curso: "IA para profesionales desde cero"  
- Fuente: "instagram_marketing_01"
```

### 2. Respuesta Personalizada
```
✅ Saludo personalizado con nombre del curso
✅ Descripción atractiva
✅ Botones de acción inmediatos
✅ Registro en BD con score inicial
```

### 3. Herramientas de Conversión
```
📚 Ver contenido → Syllabus interactivo
🎥 Video preview → Demo del curso  
💰 Precios → Oferta limitada con descuentos
🗣️ Agendar call → Link directo a calendario
```

### 4. Seguimiento Automático
```
⏰ Programación de seguimientos según interacción
📊 Actualización continua del score de interés
🎯 Estrategias personalizadas por perfil de usuario
```

## 🎁 Sistema de Bonos

### Características
- **Valor monetario explícito** ($300 USD de mentoría)
- **Cupos limitados** (solo 10 disponibles)
- **Tiempo limitado** (expira en 7 días)
- **Urgencia visual** (contador en tiempo real)

### Ejemplos de Bonos
- 🎓 Mentoría FastTrack (valor $300 USD)
- 📚 Pack Recursos Premium (valor $200 USD)  
- 🏆 Certificación Avanzada (valor $150 USD)

## 📊 Métricas y KPIs

### Tracking Automático
- **Conversion Rate** por fuente de anuncio
- **Engagement Score** por usuario
- **Time to Purchase** promedio
- **Valor promedio** de bonos reclamados
- **Abandono por etapa** del funnel

### Dashboard (Futuro)
- Métricas en tiempo real
- Análisis de cohortes
- A/B testing de mensajes
- ROI por campaña publicitaria

## 🔄 Flujos Implementados

### ✅ Completamente Funcionales
- Detección y procesamiento de anuncios
- Creación y scoring de leads
- Presentación de cursos
- Sistema de bonos limitados
- Tracking de interacciones

### 🚧 En Desarrollo
- Sistema de seguimiento automático
- Integración con calendario
- Dashboard de métricas
- A/B testing de mensajes
- Automatización de remarketing

## 🛠️ Arquitectura Técnica

### Patrón Utilizado
- **MVC adaptado** para bots de Telegram
- **Servicios independientes** para escalabilidad
- **Handlers especializados** por flujo
- **Utilidades reutilizables**

### Ventajas de la Estructura
- ✅ **Modularidad**: Cada componente tiene responsabilidad única
- ✅ **Escalabilidad**: Fácil agregar nuevos agentes/flujos
- ✅ **Mantenibilidad**: Código organizado y documentado
- ✅ **Testabilidad**: Componentes independientes
- ✅ **Reutilización**: Utilidades compartidas

Esta estructura permite un desarrollo ágil y mantenimiento eficiente del bot de ventas con IA. 