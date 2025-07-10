# Plan de Implementación: Datos de Pago y Recursos Reales

## 🎯 Objetivo
Implementar el envío automático de datos de pago cuando hay intención de compra y solucionar los errores de recursos/documentos faltantes.

## 📋 Problemas Actuales Identificados

### 1. **Errores de Documentos**
```
Error enviando documento: Wrong type of the web page content
Error enviando documento desde URL: Wrong type of the web page content
```
**Causa**: Los recursos que intenta enviar el bot no existen en las rutas especificadas o son URLs inválidas.

### 2. **Falta de Datos de Pago**
No hay un sistema para enviar automáticamente los datos bancarios cuando se detecta intención de compra.

### 3. **Recursos Placeholder**
Los datos en la base de datos son placeholders, no recursos reales.

## 🗄️ PARTE 1: Base de Datos - Datos de Pago

### Crear tabla de configuración de pago
```sql
-- Nueva tabla para datos de pago
CREATE TABLE payment_info (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    bank_name VARCHAR(100) NOT NULL,
    clabe_account VARCHAR(18) NOT NULL,
    rfc VARCHAR(13) NOT NULL,
    cfdi_usage VARCHAR(10) NOT NULL,
    cfdi_description VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar los datos de pago de la empresa
INSERT INTO payment_info (
    company_name,
    bank_name, 
    clabe_account,
    rfc,
    cfdi_usage,
    cfdi_description
) VALUES (
    'Aprende y Aplica Al S.A.de CV.',
    'BBVA',
    '012345678901234567',
    'AAI210307DEF',
    'G03',
    'Gastos en general'
);
```

## 📋 PARTE 2: Estructura de Recursos Clarificada

### **FREE RESOURCES (Nivel CURSO)**
**Propósito**: Recursos gratuitos para convencer al usuario y mostrar calidad del curso
**Cuándo se envían**: Cuando se activa herramienta `enviar_recursos_gratuitos` o usuario pregunta por contenido
**Tabla**: `free_resources`

```sql
-- Usar tabla existente free_resources
CREATE TABLE free_resources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id uuid REFERENCES courses(id),
    resource_name text NOT NULL,
    resource_type text, -- 'PDF', 'VIDEO', 'TEMPLATE'
    resource_url text,  -- URLs de GitHub
    resource_description text,
    download_count integer DEFAULT 0,
    created_at timestamp DEFAULT NOW(),
    active boolean DEFAULT true
);
```

### **BONOS EXCLUSIVOS (Nivel CURSO)**
**Propósito**: Incentivos para cerrar venta, solo se mencionan para convencer, NO se envían hasta comprar
**Cuándo se mencionan**: Para persuadir durante conversación de ventas
**Cuándo se envían**: SOLO después de confirmar compra

```sql
-- NUEVA tabla para bonos exclusivos
CREATE TABLE course_bonuses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id),
    bonus_name TEXT NOT NULL,
    bonus_description TEXT NOT NULL, -- Para que el agente sepa qué es
    bonus_type TEXT, -- 'MASTERCLASS', 'TEMPLATE', 'GUIDE', 'VIDEO'
    resource_url TEXT, -- URL de GitHub del recurso
    value_usd DECIMAL(10,2), -- Valor del bono en USD
    condition_type TEXT, -- 'TIME_LIMITED', 'FIRST_BUYERS', 'FULL_PAYMENT'
    condition_detail TEXT, -- 'next_24_hours', 'first_50', etc
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insertar ejemplo: Plantilla de calendario de contenido
INSERT INTO course_bonuses (
    course_id,
    bonus_name,
    bonus_description,
    bonus_type,
    resource_url,
    value_usd,
    condition_type,
    condition_detail
) VALUES (
    'c76bc3dd-502a-4b99-8c6c-3f9fce33a14b',
    'Plantilla de Calendario de Contenido 30 Días',
    'Plantilla completa para planificar y organizar tu contenido durante 30 días, incluye temas sugeridos, horarios óptimos de publicación y métricas a seguir para maximizar el engagement',
    'TEMPLATE',
    'https://github.com/nocode-ecosdeliderazgo/bot-recursos-publicos/blob/f1e643cb17e2d5e6607d1b40dbe1201416431582/pdfs/calendario-contenido-30dias.pdf',
    47.00,
    'TIME_LIMITED',
    'próximas 24 horas'
);
```

## 📁 PARTE 3: Recursos que Necesitas Crear/Subir

### **Free Resources (GitHub)**
```
📂 tu-organizacion/recursos-cursos/
├── 📂 ia-profesionales/
│   ├── 📄 temario-completo.pdf
│   ├── 📄 casos-exito-empresarios.pdf
│   ├── 📄 guia-implementacion-practica.pdf
│   └── 🎥 preview-curso.mp4
├── 📂 prompts/
│   └── 📄 guia-prompts-chatgpt-marketing.pdf ✅ (YA LO TIENES)
└── 📂 bonos/
    ├── 📄 calendario-contenido-30dias.pdf ✅ (YA LO TIENES)
    ├── 📄 plantillas-email-marketing.pdf
    ├── 🎥 masterclass-automatizacion.mp4
    └── 📄 checklist-implementacion-ia.pdf
```

### **SQLs para Free Resources**
```sql
-- Insertar free resources del curso IA Profesionales
INSERT INTO free_resources (course_id, resource_name, resource_type, resource_url, resource_description) VALUES 

('c76bc3dd-502a-4b99-8c6c-3f9fce33a14b', 'Temario Completo del Curso', 'PDF', 'https://github.com/TU-ORG/recursos-cursos/blob/main/ia-profesionales/temario-completo.pdf', 'Temario detallado con objetivos y contenido de cada módulo'),

('c76bc3dd-502a-4b99-8c6c-3f9fce33a14b', 'Guía de Prompts para Marketing', 'PDF', 'https://github.com/nocode-ecosdeliderazgo/bot-recursos-publicos/blob/f1e643cb17e2d5e6607d1b40dbe1201416431582/pdfs/guia-prompts-chatgpt-marketing.pdf', 'Guía práctica de prompts para ChatGPT aplicado al marketing'),

('c76bc3dd-502a-4b99-8c6c-3f9fce33a14b', 'Casos de Éxito Empresariales', 'PDF', 'https://github.com/TU-ORG/recursos-cursos/blob/main/ia-profesionales/casos-exito-empresarios.pdf', 'Casos reales de empresarios que implementaron IA exitosamente'),

('c76bc3dd-502a-4b99-8c6c-3f9fce33a14b', 'Guía de Implementación Práctica', 'PDF', 'https://github.com/TU-ORG/recursos-cursos/blob/main/ia-profesionales/guia-implementacion-practica.pdf', 'Pasos específicos para implementar IA en tu negocio'),

('c76bc3dd-502a-4b99-8c6c-3f9fce33a14b', 'Preview del Curso', 'VIDEO', 'https://github.com/TU-ORG/recursos-cursos/blob/main/ia-profesionales/preview-curso.mp4', 'Video preview del curso con adelanto del contenido');
```

### **SQLs para Bonos (ejemplos adicionales)**
```sql
-- Insertar más bonos para el curso
INSERT INTO course_bonuses (course_id, bonus_name, bonus_description, bonus_type, resource_url, value_usd, condition_type, condition_detail) VALUES 

('c76bc3dd-502a-4b99-8c6c-3f9fce33a14b', 'Masterclass: Automatización Avanzada', 'Masterclass exclusiva de 90 minutos sobre automatización de procesos con IA, incluye casos de uso avanzados y implementación paso a paso', 'MASTERCLASS', 'https://github.com/TU-ORG/recursos-cursos/blob/main/bonos/masterclass-automatizacion.mp4', 197.00, 'TIME_LIMITED', 'próximas 24 horas'),

('c76bc3dd-502a-4b99-8c6c-3f9fce33a14b', 'Pack de Plantillas Email Marketing', 'Colección de 25 plantillas de email marketing optimizadas con IA, incluye subject lines, secuencias de bienvenida y follow-up automatizado', 'TEMPLATE', 'https://github.com/TU-ORG/recursos-cursos/blob/main/bonos/plantillas-email-marketing.pdf', 97.00, 'FIRST_BUYERS', 'primeros 50 estudiantes'),

('c76bc3dd-502a-4b99-8c6c-3f9fce33a14b', 'Checklist de Implementación Empresarial', 'Checklist completo para implementar IA en empresas, incluye timeline, presupuestos, herramientas recomendadas y métricas de éxito', 'GUIDE', 'https://github.com/TU-ORG/recursos-cursos/blob/main/bonos/checklist-implementacion-ia.pdf', 67.00, 'FULL_PAYMENT', 'pago completo');
```

## 💻 PARTE 4: Cambios en el Código (MI RESPONSABILIDAD)

### **1. Crear PaymentService**
```python
# core/services/payment_service.py
class PaymentService:
    async def get_payment_info(self):
        """Obtiene datos de pago desde payment_info table"""
        
    def format_payment_message(self, payment_data):
        """Formatear mensaje elegante con datos bancarios"""
```

### **2. Crear BonusService**
```python
# core/services/bonus_service.py
class BonusService:
    async def get_course_bonuses(self, course_id):
        """Obtiene bonos del curso desde course_bonuses table"""
        
    def format_bonuses_for_persuasion(self, bonuses):
        """Formatea bonos para mencionar en conversación de ventas"""
```

### **3. Modificar Herramientas Existentes**
```python
# En core/agents/agent_tools.py

async def enviar_recursos_gratuitos(self, user_id: str, course_id: str):
    """
    MODIFICADA: Usa free_resources table con URLs de GitHub
    Convierte URLs a formato RAW para Telegram
    """

async def mostrar_bonos_exclusivos(self, user_id: str, course_id: str):
    """
    MODIFICADA: Usa course_bonuses table 
    Solo MENCIONA bonos para persuadir, NO los envía
    """

async def enviar_datos_pago(self, user_id: str):
    """
    NUEVA: Envía datos bancarios para realizar el pago del curso
    """
```

### **4. Modificar Detección de Intención de Compra**
```python
# En core/agents/intelligent_sales_agent.py
# Detectar frases como:
# - "quiero inscribirme"
# - "como puedo pagar" 
# - "donde deposito"
# - "estoy listo para comprar"
# Activar automáticamente: enviar_datos_pago + contactar_asesor_directo
```

### **5. Arreglar Manejo de URLs GitHub**
```python
# En agente_ventas_telegram.py
def convert_github_url_to_raw(github_url):
    """Convierte URL de GitHub a formato RAW para Telegram"""
    return github_url.replace('/blob/', '/raw/')

# Mejor manejo de errores de documentos
# Logs más detallados
# Verificación de URLs antes de enviar
```

## 🔧 PARTE 5: Implementación Paso a Paso

### **Paso 1: Base de Datos (TÚ HACES)**
1. ✅ Ejecutar SQL para crear tabla `course_bonuses` 
2. ✅ Insertar bonos de ejemplo del curso IA Profesionales
3. ✅ Verificar que los datos se guardaron correctamente

### **Paso 2: Recursos GitHub (TÚ HACES)**
1. ✅ Subir PDFs a tu repositorio de GitHub
2. ✅ Obtener URLs correctas de cada archivo  
3. ✅ Ejecutar SQLs para insertar en `free_resources`

### **Paso 3: Código (YO HAGO)**
1. ✅ Crear `PaymentService` y `BonusService`
2. ✅ Crear herramienta `enviar_datos_pago`
3. ✅ Modificar `enviar_recursos_gratuitos` para usar GitHub URLs
4. ✅ Modificar `mostrar_bonos_exclusivos` para solo mencionar (no enviar)
5. ✅ Mejorar detección de intención de compra
6. ✅ Arreglar manejo de URLs y errores de documentos

### **Paso 4: Testing (AMBOS)**
1. ✅ Probar envío de free resources desde GitHub
2. ✅ Verificar mención de bonos (sin enviarlos)
3. ✅ Confirmar envío automático de datos de pago 
4. ✅ Validar flujo completo de intención de compra

## 📱 PARTE 6: Flujos de Usuario Esperados

### **Free Resources (Durante conversación)**
```
Usuario: "¿Qué voy a aprender exactamente?"
Bot: Activa enviar_recursos_gratuitos

Envía:
- 📄 Temario completo
- 📄 Casos de éxito 
- 🎥 Preview del curso
- 📄 Guía de implementación
```

### **Bonos (Para persuadir)**
```
Usuario: "Está un poco caro"
Bot: Activa mostrar_bonos_exclusivos

Menciona (NO envía):
- 🎁 Plantilla calendario 30 días ($47 valor)
- 🎓 Masterclass automatización ($197 valor)  
- 📧 Pack plantillas email ($97 valor)
- ⏰ Solo disponibles próximas 24 horas
```

### **Intención de Compra (Automático)**
```
Usuario: "Estoy convencida, ¿cómo puedo inscribirme?"

Bot responde automáticamente:
1. ✅ Mensaje de confirmación
2. 💳 Datos bancarios (payment_info table)
3. 📞 Contacto con asesor
4. 🎁 Recordatorio de bonos por tiempo limitado
```

## 📞 TU SIGUIENTE ACCIÓN

**PARTE 1 - Base de Datos:**
1. Ejecutar SQL para crear tabla `course_bonuses`
2. Insertar los bonos de ejemplo (calendario de 30 días, etc)

**PARTE 2 - Recursos GitHub:**
1. Subir PDFs faltantes a GitHub (temario, casos de éxito, guía implementación)
2. Obtener URLs exactas de GitHub
3. Ejecutar SQLs para insertar en `free_resources`
4. Enviarme las URLs finales

**YO ENTONCES HARÉ:**
1. Implementar todos los servicios y herramientas
2. Arreglar manejo de URLs y errores
3. Implementar detección automática de intención de compra
4. Probar que todo funcione perfectamente

**¿Perfecto? ¿Alguna duda sobre la estructura o necesitas que aclare algo?** 🚀 