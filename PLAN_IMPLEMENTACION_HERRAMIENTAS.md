# PLAN DE IMPLEMENTACIÓN DE HERRAMIENTAS - BOT BRENDA

**Fecha:** 2025-07-09  
**Objetivo:** Implementar las herramientas faltantes para completar el sistema de ventas en menos de 4 horas  
**Estado:** Migración completada, herramientas requieren activación y recursos  

---

## 🚨 PROBLEMAS CRÍTICOS IDENTIFICADOS

### 1. **AGENTE INTELIGENTE NO ACTIVA HERRAMIENTAS**
**Problema:** El sistema de clasificación de intenciones no funciona
- Las herramientas existen pero no se activan automáticamente
- El agente responde de forma genérica sin usar las 35+ herramientas
- No hay logs de activación de herramientas

**Impacto:** CRÍTICO - El bot no está usando su funcionalidad principal

### 2. **FLUJO DE CONTACTO CON ASESOR NO SE ACTIVA**
**Problema:** La herramienta `contactar_asesor_directo` no se llama
- El flujo está implementado correctamente en `contact_flow.py`
- El bot dice "voy a conectarte" pero no ejecuta el flujo
- Importación incorrecta en `agent_tools.py`

**Impacto:** CRÍTICO - No hay cierre de ventas real

### 3. **FALTA DE RECURSOS EN BASE DE DATOS**
**Problema:** Las herramientas requieren links y recursos que no existen
- Tabla de links no existe
- PDFs y recursos gratuitos no están en BD
- URLs de demos son placeholders

**Impacto:** MEDIO - Funcionalidad limitada

---

## 🎯 PRIORIZACIÓN DE TAREAS (4 HORAS)

### **HORA 1: ARREGLAR ACTIVACIÓN DE HERRAMIENTAS (CRÍTICO)**

#### **Tarea 1.1: Diagnosticar sistema de clasificación de intenciones**
- [ ] Revisar `intelligent_sales_agent.py` - función de clasificación
- [ ] Verificar que el prompt de clasificación esté funcionando
- [ ] Agregar logging detallado para debugging
- [ ] Probar activación manual de herramientas

#### **Tarea 1.2: Corregir activación de herramientas**
- [ ] Verificar que el agente esté procesando las intenciones correctamente
- [ ] Asegurar que se llamen las funciones de herramientas
- [ ] Verificar que el sistema de validación no esté bloqueando respuestas

**Resultado esperado:** Herramientas se activan automáticamente según intención

### **HORA 2: IMPLEMENTAR FLUJO DE CONTACTO CON ASESOR (CRÍTICO)**

#### **Tarea 2.1: Corregir activación en agent_tools.py**
```python
# Cambiar esto:
from core.handlers.contact_flow import ContactFlowHandler

# Por esto:
from core.handlers.contact_flow import start_contact_flow
```

#### **Tarea 2.2: Agregar herramienta de contacto directo**
- [ ] Crear función `contactar_asesor_directo` que realmente funcione
- [ ] Integrar con el flujo de contacto existente
- [ ] Probar recolección de email y teléfono
- [ ] Verificar envío de correo a asesor

#### **Tarea 2.3: Probar flujo completo**
- [ ] Simular: "quiero hablar con un asesor"
- [ ] Verificar: recolección de datos
- [ ] Confirmar: envío de correo

**Resultado esperado:** Flujo de contacto funciona end-to-end

### **HORA 3: CREAR RECURSOS MÍNIMOS NECESARIOS (MEDIO)**

#### **Tarea 3.1: Crear tabla de links**
```sql
CREATE TABLE bot_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(50) NOT NULL,
    resource_key VARCHAR(100) NOT NULL,
    resource_url TEXT NOT NULL,
    resource_title TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### **Tarea 3.2: Insertar links básicos**
- [ ] Demo personalizada: `https://example.com/demo` (placeholder)
- [ ] Guía de prompting: `https://example.com/prompting-guide` (placeholder)
- [ ] Casos de éxito: `https://example.com/casos-exito` (placeholder)
- [ ] Recursos gratuitos: `https://example.com/recursos` (placeholder)

#### **Tarea 3.3: Actualizar herramientas para usar la tabla**
- [ ] Modificar herramientas para consultar `bot_resources`
- [ ] Agregar función helper para obtener links
- [ ] Implementar fallback para links faltantes

**Resultado esperado:** Herramientas muestran links (aunque sean placeholders)

### **HORA 4: VALIDACIÓN Y TESTING (CRÍTICO)**

#### **Tarea 4.1: Probar herramientas principales**
- [ ] `mostrar_syllabus_interactivo` - Con pregunta sobre contenido
- [ ] `mostrar_comparativa_precios` - Con objeción de precio
- [ ] `contactar_asesor_directo` - Con solicitud de contacto
- [ ] `enviar_recursos_gratuitos` - Con solicitud de materiales

#### **Tarea 4.2: Validar activación automática**
- [ ] Mensaje: "¿Qué voy a aprender?" → debe activar syllabus
- [ ] Mensaje: "Está muy caro" → debe activar comparativa
- [ ] Mensaje: "Quiero hablar con alguien" → debe activar contacto
- [ ] Mensaje: "¿Tienen recursos?" → debe activar recursos

#### **Tarea 4.3: Verificar logs y métricas**
- [ ] Logs de activación de herramientas
- [ ] Logs de clasificación de intenciones
- [ ] Respuestas del agente inteligente
- [ ] Memoria del usuario actualizada

**Resultado esperado:** Bot funciona como se especifica en documentación

---

## 📋 SCRIPTS DE IMPLEMENTACIÓN

### **Script 1: Crear tabla de recursos**
```sql
-- Crear tabla de recursos
CREATE TABLE bot_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(50) NOT NULL,
    resource_key VARCHAR(100) NOT NULL,
    resource_url TEXT NOT NULL,
    resource_title TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insertar recursos básicos
INSERT INTO bot_resources (resource_type, resource_key, resource_url, resource_title) VALUES
('demo', 'demo_personalizada', 'https://calendly.com/aprenda-ia/demo', 'Demo Personalizada'),
('pdf', 'guia_prompting', 'https://example.com/guia-prompting.pdf', 'Guía de Prompting'),
('testimonios', 'casos_exito', 'https://example.com/casos-exito', 'Casos de Éxito'),
('recursos', 'recursos_gratuitos', 'https://example.com/recursos', 'Recursos Gratuitos'),
('comparativa', 'precios_competidores', 'https://example.com/comparativa', 'Comparativa de Precios');
```

### **Script 2: Función helper para obtener recursos**
```python
async def get_bot_resource(db, resource_key: str) -> str:
    """Obtiene una URL de recurso desde la base de datos."""
    try:
        async with db.pool.acquire() as connection:
            result = await connection.fetchrow(
                "SELECT resource_url FROM bot_resources WHERE resource_key = $1 AND is_active = TRUE",
                resource_key
            )
            return result['resource_url'] if result else f"https://example.com/{resource_key}"
    except Exception as e:
        logger.error(f"Error obteniendo recurso {resource_key}: {e}")
        return f"https://example.com/{resource_key}"
```

---

## 🔧 FIXES ESPECÍFICOS REQUERIDOS

### **1. Arreglar agent_tools.py - contactar_asesor_directo**
```python
async def contactar_asesor_directo(self, user_id: str, course_id: str = None) -> None:
    """
    Inicia flujo directo de contacto con asesor.
    CORREGIDO: Usar funciones directas del contact_flow
    """
    from core.handlers.contact_flow import start_contact_flow
    
    # Crear un mock update para activar el flujo
    mock_update = self._create_mock_update(user_id)
    mock_context = self._create_mock_context()
    
    await start_contact_flow(mock_update, mock_context)
```

### **2. Arreglar intelligent_sales_agent.py - activación de herramientas**
```python
async def process_message(self, user_id: str, message: str) -> str:
    """Procesa mensaje y activa herramientas según intención detectada."""
    
    # 1. Clasificar intención
    intent = await self._classify_intent(message)
    logger.info(f"Intención detectada: {intent}")
    
    # 2. Activar herramientas según intención
    tools_activated = await self._activate_tools_for_intent(intent, user_id, message)
    logger.info(f"Herramientas activadas: {tools_activated}")
    
    # 3. Generar respuesta
    response = await self._generate_response(user_id, message, tools_activated)
    
    return response
```

### **3. Agregar logging detallado**
```python
import logging
logger = logging.getLogger(__name__)

# En cada función de herramienta:
logger.info(f"🛠️ Activando herramienta: {tool_name}")
logger.info(f"📊 Parámetros: {parameters}")
logger.info(f"✅ Resultado: {result_summary}")
```

---

## 🚀 ORDEN DE EJECUCIÓN

### **Paso 1: Diagnóstico (15 min)**
```bash
# Probar el bot actual
python agente_ventas_telegram.py

# Enviar mensaje de prueba
"¿Qué voy a aprender exactamente?"

# Verificar logs
tail -f bot.log
```

### **Paso 2: Implementación rápida (3 horas)**
1. **Arreglar activación de herramientas** (60 min)
2. **Implementar flujo de contacto** (45 min)
3. **Crear recursos mínimos** (45 min)
4. **Testing y validación** (30 min)

### **Paso 3: Validación final (30 min)**
- Ejecutar los 3 flujos de `FLUJOS_VALIDACION_BOT.md`
- Verificar que las herramientas se activen correctamente
- Confirmar que el flujo de contacto funciona

---

## 🎯 MÉTRICAS DE ÉXITO

### **Al final de 4 horas, el bot debe:**
- ✅ Activar herramientas automáticamente según intención
- ✅ Completar flujo de contacto con asesor (email + teléfono)
- ✅ Enviar correo al asesor con datos del lead
- ✅ Mostrar links de recursos (aunque sean placeholders)
- ✅ Responder de forma inteligente y personalizada

### **Herramientas mínimas funcionando:**
1. `mostrar_syllabus_interactivo` - Pregunta sobre contenido
2. `mostrar_comparativa_precios` - Objeción de precio
3. `contactar_asesor_directo` - Solicitud de contacto
4. `enviar_recursos_gratuitos` - Solicitud de materiales
5. `mostrar_garantia_satisfaccion` - Pregunta sobre garantías

---

## 📝 PRÓXIMOS PASOS (POST-4 HORAS)

### **Mejoras a implementar después:**
1. **Recursos reales:** Reemplazar placeholders con links funcionales
2. **Más herramientas:** Implementar las 35+ herramientas restantes
3. **Analytics:** Agregar métricas de conversión
4. **Optimización:** Mejorar prompts y respuestas

### **Prioridad para siguiente sesión:**
- Crear recursos reales (PDFs, videos, demos)
- Implementar sistema de métricas
- Agregar más herramientas de conversión
- Optimizar prompts de clasificación

---

**OBJETIVO FINAL:** Bot totalmente funcional con herramientas activándose automáticamente y flujo de contacto operativo en menos de 4 horas.