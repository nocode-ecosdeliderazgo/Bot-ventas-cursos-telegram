"""
Agente de ventas inteligente que usa OpenAI para generar respuestas
completamente personalizadas basadas en el perfil del usuario.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, cast
from datetime import datetime
import json

try:
    from openai import AsyncOpenAI
    from openai.types.chat import ChatCompletionMessageParam
except ImportError:
    AsyncOpenAI = None
    ChatCompletionMessageParam = Dict[str, str]  # Tipo para compatibilidad

from core.utils.memory import LeadMemory
from core.services.courseService import CourseService
from core.services.promptService import PromptService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Eres Brenda, una asesora experta en ventas de IA de Ecos de Liderazgo. Tu objetivo es convertir leads en ventas del curso de Inteligencia Artificial 
de manera natural y estratégica.

REGLAS IMPORTANTES:
1. NO saludes en cada mensaje - solo al primer contacto
2. NO seas insistente con demos/cursos - menciona máximo 1 vez cada 3-4 intercambios
3. Divide mensajes largos automáticamente (máximo 2-3 oraciones por mensaje)
4. Sé conversacional y enfócate en entender sus necesidades ANTES de vender
5. Usa herramientas solo cuando sea estratégicamente apropiado

ESTRATEGIA DE MENSAJES:
- Mensaje 1: Pregunta/conversación principal (máximo 2-3 oraciones)
- Mensaje 2: Información adicional si es necesario (máximo 2-3 oraciones)  
- Mensaje 3: Call-to-action o demo SOLO si es el momento apropiado

CUÁNDO USAR HERRAMIENTAS:
- send_demo_link: Solo después de 2-3 intercambios de valor, cuando muestren interés real
- send_course_info: Solo cuando pregunten específicamente por detalles del curso
- send_pricing_info: Solo cuando mencionen presupuesto o pregunten por precios
- schedule_call: Solo cuando estén listos para comprar o necesiten asesoría personalizada

PERSONALIZACIÓN POR PROFESIÓN:
- Marketing: Automatización de copy, segmentación inteligente, A/B testing con IA
- Ventas: Calificación automática de leads, personalización de propuestas
- Estudiante: Investigación 10x más rápida, ventaja competitiva en el mercado
- Contador: Automatización de reportes, análisis predictivo, reducción de errores
- Gerente: Decisiones basadas en datos, optimización de equipos, KPIs inteligentes
- Emprendedor: Validación de ideas, automatización de procesos, análisis de mercado

RESPUESTA FORMATO:
Si tu respuesta tiene más de 3 oraciones, divídela en múltiples mensajes usando el formato:
[MENSAJE_1] contenido del primer mensaje
[MENSAJE_2] contenido del segundo mensaje
[MENSAJE_3] contenido del tercer mensaje (si es necesario)

Mantén cada mensaje conversacional, valioso y enfocado en sus necesidades específicas.

# Instrucciones Críticas de Veracidad

**NUNCA INVENTES INFORMACIÓN. SOLO USA DATOS DE LA BASE DE DATOS.**

## Reglas Estrictas:
1. **OBLIGATORIO**: Antes de responder cualquier pregunta sobre cursos, SIEMPRE consulta la base de datos
2. **PROHIBIDO**: Agregar información que no esté explícitamente en la base de datos
3. **VERIFICACIÓN**: Si no encuentras información específica en la BD, di "No tengo esa información específica en mis datos"
4. **EJERCICIOS PRÁCTICOS**: Si hay ejercicios prácticos disponibles, menciona que se pueden aplicar en el módulo o herramienta específica


## Estructura de la Base de Datos

### Tablas Principales:
- `courses`: Información completa de cursos
- `course_modules`: Módulos específicos de cada curso
- `course_prompts`: Ejemplos de uso para cada curso
- `user_leads`: Información de prospectos
- `course_sales`: Ventas realizadas
- `course_interactions`: Interacciones con cursos

### Campos Críticos de `courses`:
- `name`: Nombre exacto del curso
- `short_description`: Descripción breve
- `long_description`: Descripción completa (USAR ESTA COMO FUENTE PRINCIPAL)
- `total_duration`: Duración total
- `price_usd`: Precio en USD
- `level`: Nivel del curso
- `category`: Categoría
- `tools_used`: Herramientas utilizadas
- `prerequisites`: Prerrequisitos
- `requirements`: Requerimientos

## Protocolo de Respuesta

### Al describir un curso:
1. **PASO 1**: Verificar que tienes la información del curso en los datos proporcionados
2. **PASO 2**: Usar SOLO la información disponible
3. **PASO 3**: Si necesitas información de módulos, verificar que esté disponible
4. **PASO 4**: Estructurar respuesta basada únicamente en datos de BD


❌ "Tiene soporte 24/7" (si no está en los datos)

## Manejo de Preguntas sin Información

### Si no tienes la información específica:
- "No tengo esa información específica en mis datos del curso"
- "Según mi base de datos, el curso incluye [listar solo lo que está]"
- "Para obtener más detalles sobre ese aspecto, te recomiendo contactar directamente"

## Validación de Respuestas

### Antes de enviar cada respuesta, verificar:
1. ✅ ¿Toda la información proviene de los datos disponibles?
2. ✅ ¿Estoy citando textualmente los campos relevantes?
3. ✅ ¿Evité agregar interpretaciones o suposiciones?
4. ✅ ¿Verifiqué los datos antes de responder?

"""

class IntelligentSalesAgent:
    """
    Agente de ventas inteligente que usa OpenAI para generar respuestas
    completamente personalizadas y estratégicas.
    """
    
    def __init__(self, openai_api_key: str, db):
        # Cliente de OpenAI
        if AsyncOpenAI is None:
            logger.error("OpenAI no está instalado. Instala con: pip install openai")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=openai_api_key)
        
        # Prompt de sistema que define al agente
        self.system_prompt = SYSTEM_PROMPT
        
        # Servicios
        self.course_service = CourseService(db)
        self.prompt_service = PromptService(openai_api_key)

    async def generate_response(self, user_message: str, user_memory: LeadMemory, course_info: Optional[Dict]) -> Union[str, List[Dict[str, str]]]:
        """Genera una respuesta personalizada usando OpenAI"""
        if self.client is None:
            return "Lo siento, hay un problema con el sistema. Por favor intenta más tarde."
        
        try:
            # Extraer información del mensaje del usuario
            await self._extract_user_info(user_message, user_memory)
            
            # Buscar referencias a cursos en el mensaje del usuario
            course_references = await self.prompt_service.extract_course_references(user_message)
            
            # Si hay referencias a cursos pero no tenemos información del curso,
            # intentar obtener la información del curso
            if course_references and not course_info:
                for reference in course_references:
                    # Buscar cursos que coincidan con la referencia
                    courses = await self.course_service.searchCourses(reference)
                    if courses:
                        # Usar el primer curso encontrado
                        course_info = await self.course_service.getCourseDetails(courses[0]['id'])
                        break
            
            # Si tenemos un ID de curso seleccionado pero no la información completa,
            # obtener los detalles
            if user_memory.selected_course and not course_info:
                course_info = await self.course_service.getCourseDetails(user_memory.selected_course)
            
            # Preparar el historial de conversación
            conversation_history: List[Dict[str, str]] = []
            
            # Agregar mensajes previos si existen
            if user_memory.message_history:
                # Limitar a los últimos 5 intercambios (10 mensajes)
                recent_messages = user_memory.message_history[-10:]
                for msg in recent_messages:
                    role = "user" if msg.get('role') == 'user' else "assistant"
                    conversation_history.append({
                        "role": role,
                        "content": msg.get('content', '')
                    })
            
            # Construir contexto para el prompt
            system_message = self.system_prompt
            
            # Agregar información del curso si está disponible
            if course_info:
                course_context = f"""
## Información del Curso Actual:
- Nombre: {course_info.get('name', 'No disponible')}
- Descripción corta: {course_info.get('short_description', 'No disponible')}
- Descripción completa: {course_info.get('long_description', 'No disponible')}
- Duración total: {course_info.get('total_duration', 'No disponible')}
- Precio (USD): {course_info.get('price_usd', 'No disponible')}
- Nivel: {course_info.get('level', 'No disponible')}
- Categoría: {course_info.get('category', 'No disponible')}
- Herramientas usadas: {', '.join(str(t) for t in course_info.get('tools_used', ['No disponible']))}
- Prerrequisitos: {', '.join(str(p) for p in course_info.get('prerequisites', ['No disponible']))}
- Requerimientos: {', '.join(str(r) for r in course_info.get('requirements', ['No disponible']))}
"""
                system_message += "\n" + course_context
                
                # Agregar información de módulos si está disponible
                if course_info.get('id'):
                    # Obtener módulos del curso
                    modules = await self.course_service.getCourseModules(course_info['id'])
                    if modules:
                        modules_info = "\n## Módulos del Curso:\n"
                        for module in modules:
                            if module:  # Verificar que el módulo no sea None
                                modules_info += f"- Módulo {module.get('module_index', '?')}: {module.get('name', 'Sin nombre')}\n"
                                if module.get('description'):
                                    modules_info += f"  Descripción: {module.get('description')}\n"
                                if module.get('duration'):
                                    modules_info += f"  Duración: {module.get('duration')}\n"
                        system_message += "\n" + modules_info
            
            # Agregar información del usuario
            user_context = f"""
## Información del Usuario:
- Nombre: {user_memory.name if user_memory.name else 'No disponible'}
- Profesión: {user_memory.role if user_memory.role else 'No disponible'}
- Intereses: {', '.join(user_memory.interests) if user_memory.interests else 'No disponible'}
- Puntos de dolor: {', '.join(user_memory.pain_points) if user_memory.pain_points else 'No disponible'}
- Nivel de interés: {user_memory.interest_level if user_memory.interest_level else 'No disponible'}
"""
            system_message += "\n" + user_context
            
            # Crear mensajes para la API
            messages: List[ChatCompletionMessageParam] = [
                {"role": "system", "content": system_message}
            ]
            
            # Agregar historial de conversación
            for msg in conversation_history:
                messages.append(cast(ChatCompletionMessageParam, msg))
            
            # Agregar mensaje actual del usuario
            messages.append({"role": "user", "content": user_message})
            
            # Llamar a la API de OpenAI
            response = await self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            # Obtener respuesta
            response_text = response.choices[0].message.content or ""
            
            # Validar la respuesta si tenemos información del curso
            if course_info:
                validation = await self.prompt_service.validate_response(response_text, course_info)
                
                # Si la respuesta no es válida, registrar advertencia
                if not validation.get('is_valid', True):
                    errors = validation.get('errors', [])
                    logger.warning(f"Respuesta inválida para usuario {user_memory.user_id}: {', '.join(errors)}")
                    
                    # Si la confianza es muy baja, regenerar la respuesta con instrucciones más estrictas
                    if validation.get('confidence', 1.0) < 0.3:
                        logger.info(f"Regenerando respuesta para usuario {user_memory.user_id}")
                        
                        # Agregar advertencia al prompt
                        warning_message = f"""
ADVERTENCIA: Tu respuesta anterior contenía información incorrecta o inventada:
{', '.join(errors)}

RECUERDA:
1. SOLO usa información que esté explícitamente en los datos del curso
2. NO agregues detalles que no estén en la base de datos
3. Si no tienes la información, di "No tengo esa información específica"
4. Verifica cada afirmación antes de incluirla

Por favor, genera una nueva respuesta que sea 100% precisa según los datos proporcionados.
"""
                        
                        # Agregar mensaje de advertencia
                        messages.append({"role": "assistant", "content": response_text})
                        messages.append({"role": "user", "content": warning_message})
                        
                        # Regenerar respuesta
                        new_response = await self.client.chat.completions.create(
                            model="gpt-4.1-mini",
                            messages=messages,
                            max_tokens=500,
                            temperature=0.5
                        )
                        
                        # Actualizar respuesta
                        response_text = new_response.choices[0].message.content or ""
            
            # Procesar la respuesta para manejar múltiples mensajes
            processed_messages = await self._process_response(response_text, user_memory)
            
            # Actualizar historial de conversación
            if not user_memory.message_history:
                user_memory.message_history = []
            
            # Agregar mensaje del usuario al historial
            user_memory.message_history.append({
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Agregar respuesta del agente al historial
            for msg in processed_messages:
                if msg['type'] == 'text':
                    user_memory.message_history.append({
                        'role': 'assistant',
                        'content': msg['content'],
                        'timestamp': datetime.now().isoformat()
                    })
            
            # Si hay múltiples mensajes, formatearlos correctamente
            if len(processed_messages) > 1:
                return processed_messages
            else:
                return processed_messages[0]['content'] if processed_messages else "Lo siento, no pude generar una respuesta."
                
        except Exception as e:
            logger.error(f"Error generando respuesta: {e}", exc_info=True)
            return "Lo siento, ocurrió un error al procesar tu mensaje. Por favor intenta nuevamente."
    
    async def _extract_user_info(self, user_message: str, user_memory: LeadMemory):
        """Extrae información relevante del mensaje del usuario"""
        try:
            if self.client is None:
                logger.error("No se puede extraer información del usuario: cliente OpenAI no disponible")
                return
                
            extraction_prompt = f"""
Analiza el siguiente mensaje del usuario y extrae información relevante:

MENSAJE: "{user_message}"

Extrae y devuelve en formato JSON:
{{
    "profession": "profesión detectada o null",
    "interests": ["lista", "de", "intereses"],
    "pain_points": ["puntos", "de", "dolor"],
    "buying_signals": ["señales", "de", "compra"],
    "objections": ["objeciones", "mencionadas"],
    "interest_level": "low/medium/high"
}}

Solo extrae información que esté claramente presente en el mensaje.
"""
            
            response = await self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": extraction_prompt}],
                max_tokens=300,
                temperature=0.1
            )
            
            # Parsear respuesta JSON
            raw_content = response.choices[0].message.content or ""
            extracted_info = json.loads(raw_content)
            
            # Actualizar memoria del usuario
            if extracted_info.get('profession'):
                user_memory.role = extracted_info['profession']
            
            if extracted_info.get('interests'):
                current_interests = user_memory.interests or []
                new_interests = [i for i in extracted_info['interests'] if i not in current_interests]
                user_memory.interests = current_interests + new_interests
            
            # Agregar información adicional
            if extracted_info.get('pain_points'):
                user_memory.pain_points = user_memory.pain_points or []
                user_memory.pain_points.extend(extracted_info['pain_points'])
            if extracted_info.get('buying_signals'):
                user_memory.buying_signals = user_memory.buying_signals or []
                user_memory.buying_signals.extend(extracted_info['buying_signals'])
            if extracted_info.get('interest_level'):
                user_memory.interest_level = extracted_info['interest_level']
                
        except Exception as e:
            logger.error(f"Error extrayendo información del usuario: {e}", exc_info=True)

    async def _process_response(self, response_text: str, user_memory: LeadMemory) -> List[Dict[str, str]]:
        """Procesa la respuesta del LLM y maneja múltiples mensajes"""
        messages: List[Dict[str, str]] = []
        
        # Verificar si la respuesta contiene múltiples mensajes
        if "[MENSAJE_" in response_text:
            # Dividir por mensajes
            import re
            message_parts = re.split(r'\[MENSAJE_\d+\]', response_text)
            message_parts = [part.strip() for part in message_parts if part.strip()]
            
            for part in message_parts:
                if part:
                    messages.append({
                        'type': 'text',
                        'content': part
                    })
        else:
            # Mensaje único
            messages.append({
                'type': 'text', 
                'content': response_text
            })
        
        return messages 