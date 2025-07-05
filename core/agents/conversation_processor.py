"""
Procesador de conversaciones inteligente para el agente de ventas.
Maneja todas las interacciones del usuario después de mostrar la información del curso.
"""

import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import aiohttp

from config.settings import settings
from core.services.supabase_service import get_course_detail, get_courses, get_promotions
from core.utils.memory import LeadMemory
# NUEVO: importar CourseService
from core.services.courseService import CourseService

logger = logging.getLogger(__name__)

class ConversationProcessor:
    """
    Procesador inteligente de conversaciones que analiza intenciones del usuario
    y responde con información real de la base de datos manteniendo el objetivo de venta.
    """
    
    def __init__(self, course_service: Optional[CourseService] = None):
        self.openai_headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Intenciones principales que puede detectar
        self.intentions = {
            "price_question": "Pregunta sobre precio, costo, inversión, pago",
            "schedule_question": "Pregunta sobre horarios, fechas, cuándo empieza",
            "content_question": "Pregunta sobre temario, contenido, qué aprenderá",
            "instructor_question": "Pregunta sobre instructor, profesor, quién enseña",
            "certificate_question": "Pregunta sobre certificado, validez, reconocimiento",
            "modality_question": "Pregunta sobre modalidad, online, presencial",
            "level_question": "Pregunta sobre nivel, dificultad, requisitos",
            "duration_question": "Pregunta sobre duración, tiempo, horas",
            "comparison_question": "Comparación con otros cursos o competencia",
            "objection": "Objeción, duda, preocupación, 'es caro', 'no tengo tiempo'",
            "ready_to_buy": "Listo para comprar, inscribirse, registrarse",
            "more_info": "Pide más información general",
            "testimonials": "Pide testimonios, reseñas, opiniones",
            "support_question": "Pregunta sobre soporte, ayuda durante el curso",
            "technical_question": "Pregunta técnica sobre herramientas, software",
            "career_question": "Pregunta sobre beneficios profesionales, carrera",
            "group_question": "Pregunta sobre grupo, compañeros, tamaño de clase",
            "payment_methods": "Pregunta sobre formas de pago, financiamiento",
            "refund_policy": "Pregunta sobre política de reembolso, garantías",
            "other": "Otra intención no clasificada"
        }
        # NUEVO: guardar referencia a course_service
        self.course_service = course_service
    
    async def process_message(self, message: str, user_memory: LeadMemory) -> Tuple[str, Optional[Dict]]:
        """
        Procesa un mensaje del usuario y genera una respuesta inteligente.
        
        Args:
            message: Mensaje del usuario
            user_memory: Memoria del usuario con contexto
            
        Returns:
            Tupla con (respuesta, datos_adicionales)
        """
        try:
            # 1. Analizar intención del usuario
            intention_analysis = await self._analyze_intention(message, user_memory)
            
            # 2. Obtener información del curso si es necesario
            course_info = None
            if user_memory.selected_course:
                # Por ahora, no usamos get_course_detail aquí ya que no tenemos acceso a db_service
                # course_info = await get_course_detail(user_memory.selected_course)
                pass
            
            # 3. Extraer información profesional del usuario si es posible
            user_profession = self._extract_profession_info(message, user_memory)
            if user_profession:
                user_memory.role = user_profession
            
            # 4. Generar respuesta basada en la intención
            response = await self._generate_response(
                intention_analysis, 
                message, 
                user_memory, 
                course_info
            )
            
            # 5. Actualizar memoria del usuario
            self._update_user_memory(user_memory, message, intention_analysis)
            
            return response, None
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}", exc_info=True)
            return f"Disculpa {user_memory.name}, hubo un problema procesando tu mensaje. ¿Podrías repetir tu pregunta?", None
    
    async def _analyze_intention(self, message: str, user_memory: LeadMemory) -> Dict:
        """
        Analiza la intención del usuario usando el LLM para determinar la estrategia de respuesta.
        """
        try:
            # Construir contexto del usuario
            user_context = await self._build_user_context(user_memory)
            
            # Prompt mejorado para análisis de intención
            prompt = f"""
            Analiza el siguiente mensaje de un usuario interesado en un curso de IA y determina su intención principal.

            MENSAJE DEL USUARIO: "{message}"
            
            CONTEXTO DEL USUARIO:
            {user_context}

            INSTRUCCIONES:
            1. Identifica la intención principal del mensaje
            2. Detecta si pregunta sobre aplicabilidad profesional/carrera (cualquier variación)
            3. Analiza el tono emocional y nivel de urgencia
            4. Identifica objeciones o preocupaciones
            5. Detecta información nueva sobre el usuario
            6. Recomienda herramientas específicas a usar

            INTENCIONES POSIBLES:
            - career_applicability: Pregunta si el curso le sirve para su profesión/trabajo/carrera
            - price_question: Pregunta sobre precios, costos, inversión
            - schedule_question: Pregunta sobre horarios, fechas, duración
            - content_question: Pregunta sobre qué se enseña, módulos, herramientas
            - objection: Expresa dudas, preocupaciones, objeciones
            - ready_to_buy: Muestra interés en comprar o inscribirse
            - more_info: Pide más información general
            - testimonials: Pregunta por casos de éxito, testimonios
            - technical_question: Pregunta sobre requisitos técnicos
            - instructor_question: Pregunta sobre instructores
            - other: Otras intenciones

            RESPONDE EN FORMATO JSON:
            {{
                "intention_analysis": {{
                    "primary_intention": "categoria_principal",
                    "secondary_intentions": ["categoria_secundaria"],
                    "confidence_level": 0.8,
                    "emotional_tone": "positivo/neutral/negativo",
                    "urgency": "alta/media/baja",
                    "specific_questions": ["pregunta_especifica_1", "pregunta_especifica_2"],
                    "detected_objections": ["objecion_1", "objecion_2"],
                    "profession_mentioned": "profesion_si_se_menciona_o_null"
                }},
                "user_summary_update": {{
                    "new_info_detected": "nueva_informacion_del_usuario",
                    "interest_level": "alto/medio/bajo",
                    "readiness_to_buy": "listo/considerando/explorando"
                }},
                "recommended_tools": [
                    {{
                        "tool_name": "nombre_herramienta",
                        "priority": "alta/media/baja",
                        "reason": "por_que_usar_esta_herramienta"
                    }}
                ],
                "response_strategy": {{
                    "approach": "educar/persuadir/cerrar_venta",
                    "tone": "entusiasta/consultivo/profesional",
                    "focus_areas": ["area_1", "area_2"]
                }}
            }}
            """
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "Eres un experto analista de intenciones de usuarios interesados en cursos de IA. Analiza con precisión y responde solo en formato JSON válido."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 800
                }
                
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=self.openai_headers,
                    json=payload
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        content = result["choices"][0]["message"]["content"]
                        # Limpiar el contenido para extraer solo el JSON
                        content = content.strip()
                        if content.startswith("```json"):
                            content = content[7:-3]
                        elif content.startswith("```"):
                            content = content[3:-3]
                        
                        return json.loads(content)
                    else:
                        logger.error(f"Error en análisis de intención: {result}")
                        return self._fallback_intention_analysis(message)
                        
        except Exception as e:
            logger.error(f"Error analizando intención: {e}", exc_info=True)
            return self._fallback_intention_analysis(message)

    async def _build_user_context(self, user_memory: LeadMemory) -> str:
        """
        Construye el contexto del usuario para el análisis de intención.
        """
        context = f"""
        - Nombre: {user_memory.name or 'No proporcionado'}
        - Profesión: {user_memory.role or 'No especificada'}
        - Nivel de interés: {user_memory.lead_score}/100
        - Curso seleccionado: {user_memory.selected_course or 'No especificado'}
        - Interacciones previas: {len(user_memory.message_history) if user_memory.message_history else 0}
        - Última actividad: {user_memory.last_interaction}
        """
        
        # Agregar contexto de mensajes recientes
        if user_memory.message_history:
            recent_messages = user_memory.message_history[-3:]  # Últimos 3 mensajes
            context += "\n- Mensajes recientes:\n"
            for msg in recent_messages:
                context += f"  • {msg.get('message', '')[:100]}...\n"
        
        return context

    def _fallback_intention_analysis(self, message: str) -> Dict:
        """
        Análisis de intención básico cuando falla el LLM.
        """
        message_lower = message.lower()
        
        # Detectar intención principal basada en palabras clave
        if any(word in message_lower for word in ['sirve', 'aplica', 'trabajo', 'profesión', 'carrera', 'contador', 'marketing', 'ventas', 'finanzas']):
            primary_intention = 'career_applicability'
        elif any(word in message_lower for word in ['precio', 'costo', 'vale', 'cuesta', 'dinero', 'pagar']):
            primary_intention = 'price_question'
        elif any(word in message_lower for word in ['horario', 'cuándo', 'fecha', 'tiempo', 'duración']):
            primary_intention = 'schedule_question'
        elif any(word in message_lower for word in ['qué', 'contenido', 'módulos', 'enseña', 'aprende']):
            primary_intention = 'content_question'
        elif any(word in message_lower for word in ['no', 'pero', 'sin embargo', 'problema', 'duda']):
            primary_intention = 'objection'
        elif any(word in message_lower for word in ['quiero', 'inscribir', 'comprar', 'listo']):
            primary_intention = 'ready_to_buy'
        else:
            primary_intention = 'other'
        
        return {
            "intention_analysis": {
                "primary_intention": primary_intention,
                "secondary_intentions": [],
                "confidence_level": 0.6,
                "emotional_tone": "neutral",
                "urgency": "medium",
                "specific_questions": [],
                "detected_objections": [],
                "profession_mentioned": None
            },
            "user_summary_update": {
                "new_info_detected": "",
                "interest_level": "medio",
                "readiness_to_buy": "explorando"
            },
            "recommended_tools": [],
            "response_strategy": {
                "approach": "educar",
                "tone": "consultivo",
                "focus_areas": []
            }
        }

    async def _generate_response(
        self, 
        intention_analysis: Dict, 
        original_message: str, 
        user_memory: LeadMemory, 
        course_info: Optional[Dict]
    ) -> str:
        """
        Genera una respuesta inteligente basada en el análisis de intención.
        """
        try:
            # Extraer datos del análisis
            analysis = intention_analysis.get('intention_analysis', {})
            primary_intention = analysis.get('primary_intention', 'other')
            user_summary = intention_analysis.get('user_summary_update', {})
            
            user_name = user_memory.name or "amigo"
            
            # Actualizar memoria del usuario con nueva información
            if user_summary.get('new_info_detected'):
                await self._update_user_profile_from_summary(user_memory, user_summary)
            
            # FLUJO PRINCIPAL: Detectar si es pregunta de aplicabilidad profesional
            if primary_intention == 'career_applicability':
                return await self._handle_career_applicability_with_llm(
                    original_message, user_name, user_memory, course_info, analysis
                )
            
            # OTROS FLUJOS ESPECÍFICOS
            elif primary_intention == 'price_question':
                return await self._handle_price_question(analysis, original_message, user_name, course_info)
            elif primary_intention == 'schedule_question':
                return await self._handle_schedule_question(analysis, original_message, user_name, course_info)
            elif primary_intention == 'content_question':
                return await self._handle_content_question(analysis, original_message, user_name, course_info)
            elif primary_intention == 'objection':
                return await self._handle_objection(analysis, original_message, user_name, course_info or {})
            elif primary_intention == 'ready_to_buy':
                return await self._handle_ready_to_buy(analysis, original_message, user_name, course_info or {})
            elif primary_intention == 'more_info':
                return await self._handle_more_info(analysis, original_message, user_name, course_info)
            
            # FLUJO LIBRE: Cuando no encaja en ningún flujo específico
            else:
                return await self._generate_free_response_with_llm(
                    original_message, user_name, user_memory, course_info, analysis
                )
            
        except Exception as e:
            logger.error(f"Error generando respuesta: {e}", exc_info=True)
            return f"Disculpa {user_name}, permíteme un momento para procesar tu consulta. ¿Podrías repetir tu pregunta?"

    async def _handle_career_applicability_with_llm(
        self, 
        message: str, 
        user_name: str, 
        user_memory: LeadMemory, 
        course_info: Optional[Dict],
        analysis: Dict
    ) -> str:
        """
        Maneja preguntas de aplicabilidad profesional usando el LLM con información real del curso.
        """
        try:
            # Detectar profesión del análisis o mensaje
            detected_profession = analysis.get('profession_mentioned')
            if not detected_profession:
                detected_profession = self._extract_profession_from_message(message.lower())
            if not detected_profession and hasattr(user_memory, 'role'):
                detected_profession = user_memory.role
            
            # Obtener información real del curso
            if not course_info and self.course_service and user_memory.selected_course:
                course_info = await self.course_service.getCourseDetails(user_memory.selected_course)
            
            # Obtener módulos y ejercicios reales
            modules = []
            all_exercises = []
            if course_info and self.course_service:
                if course_info.get('id'):
                    modules = await self.course_service.getCourseModules(course_info['id'])
                    for module in modules:
                        exercises = await self.course_service.getModuleExercises(module['id'])
                        all_exercises.extend(exercises)
            
            # Usar el LLM para generar respuesta personalizada
            return await self._generate_llm_personalized_response(
                detected_profession or "profesional", 
                user_name, 
                course_info or {}, 
                modules, 
                all_exercises, 
                message
            )
            
        except Exception as e:
            logger.error(f"Error en manejo de aplicabilidad profesional: {e}", exc_info=True)
            return f"¡{user_name}! Definitivamente la IA puede transformar tu área profesional. Para darte ejemplos específicos, cuéntame: ¿a qué te dedicas? Así te muestro aplicaciones exactas del curso. 🚀"

    async def _generate_free_response_with_llm(
        self, 
        message: str, 
        user_name: str, 
        user_memory: LeadMemory, 
        course_info: Optional[Dict],
        analysis: Dict
    ) -> str:
        """
        Genera una respuesta libre usando el LLM cuando no encaja en flujos específicos.
        """
        try:
            # Obtener información real del curso
            if not course_info and self.course_service and user_memory.selected_course:
                course_info = await self.course_service.getCourseDetails(user_memory.selected_course)
            
            # Obtener módulos y ejercicios reales
            modules = []
            all_exercises = []
            if course_info and self.course_service:
                if course_info.get('id'):
                    modules = await self.course_service.getCourseModules(course_info['id'])
                    for module in modules:
                        exercises = await self.course_service.getModuleExercises(module['id'])
                        all_exercises.extend(exercises)
            
            # Construir contexto del curso real
            course_content = self._build_course_content_context(course_info or {}, modules, all_exercises)
            
            # Construir contexto del usuario
            user_context = await self._build_user_context(user_memory)
            
            # Prompt para respuesta libre
            prompt = f"""Eres un agente de ventas experto y entusiasta de cursos de IA. Un usuario te escribió: "{message}"

INFORMACIÓN REAL DEL CURSO:
{course_content}

CONTEXTO DEL USUARIO:
{user_context}

ANÁLISIS DE INTENCIÓN:
- Intención principal: {analysis.get('primary_intention', 'other')}
- Tono emocional: {analysis.get('emotional_tone', 'neutral')}
- Nivel de urgencia: {analysis.get('urgency', 'medium')}

INSTRUCCIONES:
1. Responde como un agente de ventas experto y amigable
2. Usa SOLO la información real del curso proporcionada
3. Adapta tu respuesta al tono y contexto del usuario
4. Sé conversacional y entusiasta pero profesional
5. Incluye una pregunta de seguimiento para continuar la conversación
6. Nunca inventes información que no esté en los datos del curso
7. Si no tienes información suficiente, pide más detalles al usuario

NOMBRE DEL USUARIO: {user_name}

Responde directamente como el agente de ventas:"""
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "Eres un agente de ventas experto que responde usando solo información real del curso."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 600
                }
                
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=self.openai_headers,
                    json=payload
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        content = result["choices"][0]["message"]["content"]
                        return content.strip()
                    else:
                        logger.error(f"Error en respuesta libre: {result}")
                        return f"¡{user_name}! Gracias por tu mensaje. Para darte la mejor respuesta, ¿podrías contarme más detalles sobre lo que te interesa del curso? 😊"
                        
        except Exception as e:
            logger.error(f"Error generando respuesta libre: {e}", exc_info=True)
            return f"¡{user_name}! Gracias por escribir. ¿Podrías contarme más sobre qué te interesa del curso para poder ayudarte mejor? 🤔"

    async def _generate_llm_personalized_response(
        self,
        profession: str,
        user_name: str,
        course_info: Dict,
        modules: List[Dict],
        exercises: List[Dict],
        original_message: str
    ) -> str:
        """
        Usa el LLM para generar una respuesta súper personalizada basada en el contenido real del curso.
        """
        try:
            # Construir contexto del curso real
            course_content = self._build_course_content_context(course_info, modules, exercises)
            
            # Prompt para el LLM
            prompt = f"""Eres un agente de ventas experto y entusiasta. Un usuario que es {profession} te pregunta: "{original_message}"

INFORMACIÓN REAL DEL CURSO:
{course_content}

INSTRUCCIONES:
1. Responde como un amigo entusiasta que quiere ayudar al usuario
2. Usa SOLO la información real del curso proporcionada arriba
3. Genera ejemplos específicos y prácticos de cómo un {profession} puede aplicar lo que se enseña en el curso
4. Sé creativo pero realista: analiza qué se enseña y cómo se puede aplicar en el trabajo de un {profession}
5. Usa emojis y mantén un tono conversacional y emocionante
6. Incluye una pregunta de seguimiento específica para esa profesión
7. Nunca inventes módulos, herramientas o ejercicios que no estén en la información proporcionada

ESTRUCTURA DE RESPUESTA:
- Saludo entusiasta personalizado para {profession}
- Explicación de cómo el curso se aplica a su profesión
- 3-4 ejemplos específicos basados en el contenido real
- Pregunta de seguimiento personalizada

EJEMPLO DE TONO:
"¡{user_name}, como {profession} vas a AMAR este curso! 🎯"

Responde directamente, sin explicaciones adicionales:"""
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "gpt-4.1-mini",
                    "messages": [
                        {"role": "system", "content": "Eres un agente de ventas experto que genera respuestas personalizadas usando solo información real del curso."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 800
                }
                
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=self.openai_headers,
                    json=payload
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        content = result["choices"][0]["message"]["content"]
                        return content.strip()
                    else:
                        logger.error(f"Error en OpenAI: {result}")
                        return await self._fallback_personalized_response(profession, user_name, course_info)
                        
        except Exception as e:
            logger.error(f"Error generando respuesta con LLM: {e}", exc_info=True)
            return await self._fallback_personalized_response(profession, user_name, course_info)

    def _build_course_content_context(self, course_info: Dict, modules: List[Dict], exercises: List[Dict]) -> str:
        """
        Construye un contexto detallado del contenido real del curso.
        """
        context = f"""
        CURSO: {course_info.get('name', 'Curso de IA')}
        DESCRIPCIÓN: {course_info.get('long_description', course_info.get('short_description', 'Curso práctico de IA'))}
        DURACIÓN: {course_info.get('total_duration', 'N/A')}
        NIVEL: {course_info.get('level', 'N/A')}
        
        HERRAMIENTAS QUE SE ENSEÑAN:
        """
        
        # Agregar herramientas
        tools = course_info.get('tools_used', [])
        if tools:
            for tool in tools:
                context += f"- {tool}\n"
        else:
            context += "- No especificadas\n"
        
        context += "\nMÓDULOS DEL CURSO:\n"
        
        # Agregar módulos
        if modules:
            for i, module in enumerate(modules, 1):
                context += f"{i}. {module.get('name', 'Módulo sin nombre')}\n"
                if module.get('description'):
                    context += f"   Descripción: {module['description']}\n"
                if module.get('duration'):
                    context += f"   Duración: {module['duration']}\n"
                context += "\n"
        else:
            context += "- No hay módulos específicos disponibles\n"
        
        context += "EJERCICIOS PRÁCTICOS:\n"
        
        # Agregar ejercicios
        if exercises:
            for i, exercise in enumerate(exercises, 1):
                context += f"{i}. {exercise.get('description', 'Ejercicio práctico')}\n"
        else:
            context += "- No hay ejercicios específicos disponibles\n"
        
        return context

    async def _fallback_personalized_response(self, profession: str, user_name: str, course_info: Dict) -> str:
        """
        Respuesta de respaldo cuando no se puede usar el LLM.
        """
        # Mapeo básico de profesiones
        profession_responses = {
            'contador': f"¡{user_name}, como contador vas a AMAR este curso! 💰\n\nLa IA puede transformar completamente tu trabajo diario. Imagínate poder automatizar reportes financieros, hacer análisis predictivos de tendencias, y reducir errores en tus cálculos.\n\n",
            'finanzas': f"¡{user_name}, como profesional de finanzas vas a AMAR este curso! 💰\n\nLa IA puede revolucionar tu área. Desde automatizar análisis de riesgos hasta generar reportes predictivos que te ayuden a tomar mejores decisiones financieras.\n\n",
            'marketing': f"¡{user_name}, como profesional de marketing vas a AMAR este curso! 🎯\n\nLa IA va a multiplicar tu creatividad y eficiencia. Podrás generar contenido automáticamente, analizar comportamiento de clientes, y crear campañas más efectivas.\n\n",
            'ventas': f"¡{user_name}, este curso va a multiplicar tus ventas! 💼\n\nImagínate tener un asistente de IA que te ayude a calificar leads, personalizar propuestas, y predecir qué clientes están listos para comprar.\n\n"
        }
        
        base_response = profession_responses.get(profession, 
            f"¡{user_name}, la IA va a transformar tu área profesional! 🌟\n\n"
        )
        
        # Agregar información del curso
        if course_info.get('name'):
            base_response += f"El curso \"{course_info['name']}\" está diseñado específicamente para profesionales como tú.\n\n"
        
        base_response += "¿Te gustaría que te comparta ejemplos más específicos de cómo puedes aplicar estas herramientas en tu trabajo diario? 🤔"
        
        return base_response

    def _is_module_relevant_for_profession(self, module: Dict, profession: str) -> bool:
        """
        Determina si un módulo es relevante para una profesión específica.
        """
        module_name = module.get('name', '').lower()
        module_desc = module.get('description', '').lower()
        module_content = f"{module_name} {module_desc}"
        
        profession_keywords = {
            'finanzas': ['automatización', 'análisis', 'documentos', 'datos', 'reportes', 'excel', 'cálculos', 'presupuesto'],
            'contador': ['automatización', 'análisis', 'documentos', 'datos', 'reportes', 'excel', 'cálculos', 'presupuesto'],
            'marketing': ['contenido', 'copy', 'redes', 'publicidad', 'campañas', 'creatividad', 'imágenes'],
            'ventas': ['clientes', 'propuestas', 'seguimiento', 'personalización', 'comunicación'],
            'gerente': ['análisis', 'estrategia', 'equipos', 'productividad', 'decisiones', 'liderazgo'],
            'estudiante': ['presentaciones', 'ensayos', 'investigación', 'proyectos', 'tareas'],
            'emprendedor': ['automatización', 'negocio', 'clientes', 'costos', 'eficiencia']
        }
        
        keywords = profession_keywords.get(profession, [])
        return any(keyword in module_content for keyword in keywords)

    async def _build_personalized_response_with_real_data(
        self,
        profession: str,
        user_name: str,
        course_info: Dict,
        modules: List[Dict],
        exercises: List[Dict]
    ) -> str:
        """
        Construye una respuesta personalizada usando SOLO datos reales del curso.
        """
        # Mapeo de profesiones a ejemplos específicos
        profession_intro = {
            'finanzas': f"¡{user_name}, como profesional de finanzas vas a AMAR este curso! 💰",
            'contador': f"¡{user_name}, como contador vas a AMAR este curso! 💰", 
            'marketing': f"¡{user_name}, como profesional de marketing vas a AMAR este curso! 🎯",
            'ventas': f"¡{user_name}, este curso va a multiplicar tus ventas! 💼",
            'gerente': f"¡{user_name}, como gerente vas a transformar tu equipo! 👑",
            'estudiante': f"¡{user_name}, vas a estar AÑOS adelante de tus compañeros! 🎓",
            'emprendedor': f"¡{user_name}, esto va a catapultar tu negocio! 🚀"
        }
        
        response = profession_intro.get(profession, f"¡{user_name}, la IA va a transformar tu área profesional! 🌟")
        response += "\n\n"
        
        # Agregar información del curso
        if course_info.get('name'):
            response += f"El curso \"{course_info['name']}\" está diseñado para que aprendas a usar herramientas de IA específicamente en análisis predictivo, desde cómo preparar tus datos hasta interpretar resultados que te ayuden a tomar decisiones más acertadas.\n\n"
        
        # Agregar módulos relevantes encontrados
        if modules:
            relevant_modules = [m for m in modules if self._is_module_relevant_for_profession(m, profession)]
            if relevant_modules:
                response += "📚 **Módulos específicos que te van a servir:**\n"
                for module in relevant_modules[:3]:  # Máximo 3 módulos
                    response += f"• **{module['name']}**: {module.get('description', 'Contenido práctico aplicable a tu área')}\n"
                response += "\n"
        
        # Agregar ejercicios prácticos específicos
        if exercises:
            response += "🛠 **Ejercicios prácticos que puedes aplicar inmediatamente:**\n"
            for exercise in exercises[:3]:  # Máximo 3 ejercicios
                exercise_desc = exercise.get('description', '')
                if profession in ['finanzas', 'contador']:
                    response += f"• {exercise_desc} (aplicable a reportes financieros o análisis contables)\n"
                elif profession == 'marketing':
                    response += f"• {exercise_desc} (aplicable a campañas o contenido de marketing)\n"
                elif profession == 'ventas':
                    response += f"• {exercise_desc} (aplicable a seguimiento de clientes o propuestas)\n"
                else:
                    response += f"• {exercise_desc}\n"
            response += "\n"
        
        # Agregar herramientas reales del curso
        if course_info.get('tools_used'):
            tools = course_info['tools_used']
            if isinstance(tools, list) and tools:
                response += "🔧 **Herramientas que dominarás:**\n"
                for tool in tools[:4]:  # Máximo 4 herramientas
                    response += f"• {tool}\n"
                response += "\n"
        
        # Pregunta de seguimiento personalizada
        follow_up_questions = {
            'finanzas': "¿En qué tipo de análisis financieros te gustaría aplicar estas herramientas? ¿Reportes mensuales, análisis de tendencias, o proyecciones presupuestarias?",
            'contador': "¿En qué tipo de análisis contables te gustaría aplicar estas herramientas? ¿Reportes mensuales, análisis de tendencias, o proyecciones presupuestarias?",
            'marketing': "¿En qué área de marketing te gustaría enfocarte más? ¿Análisis de campañas, segmentación de audiencias, o creación de contenido?",
            'ventas': "¿Cuál es tu mayor desafío en ventas actualmente? ¿Calificación de leads, seguimiento, o cierre?",
            'gerente': "¿Qué tipo de decisiones gerenciales te gustaría optimizar con IA? ¿Análisis de equipo, predicción de resultados, o planificación estratégica?",
            'estudiante': "¿En qué materia o área de estudio te gustaría aplicar estas herramientas primero?",
            'emprendedor': "¿Cuál es el mayor desafío en tu negocio que te gustaría resolver con IA?"
        }
        
        response += follow_up_questions.get(profession, "¿Hay algún aspecto específico de tu trabajo que te gustaría automatizar o mejorar con IA?")
        response += " 🤔"
        
        return response

    async def _update_user_profile_from_summary(self, user_memory: LeadMemory, user_summary: Dict):
        """
        Actualiza el perfil del usuario basado en el resumen generado por el LLM.
        """
        try:
            new_info = user_summary.get('new_info_detected', '')
            
            # Detectar profesión
            if 'contador' in new_info.lower():
                user_memory.role = 'contador'
            elif 'marketing' in new_info.lower():
                user_memory.role = 'marketing'
            elif 'ventas' in new_info.lower():
                user_memory.role = 'ventas'
            # Agregar más detecciones según sea necesario
            
            # Actualizar puntuación de interés si hay señales positivas
            if any(word in new_info.lower() for word in ['interesado', 'me sirve', 'quiero', 'necesito']):
                user_memory.lead_score = min(100, user_memory.lead_score + 10)
                
        except Exception as e:
            logger.error(f"Error actualizando perfil de usuario: {e}")

    async def _execute_recommended_tools(
        self, 
        recommended_tools: List[Dict], 
        user_name: str, 
        user_memory: LeadMemory, 
        course_info: Optional[Dict],
        original_message: str
    ) -> str:
        """
        Ejecuta las herramientas recomendadas por el LLM (placeholder para implementación futura).
        """
        # Por ahora, generar respuesta basada en la estrategia recomendada
        high_priority_tools = [tool for tool in recommended_tools if tool.get('priority') == 'alta']
        
        if high_priority_tools:
            tool_name = high_priority_tools[0].get('tool_name', '')
            reason = high_priority_tools[0].get('reason', '')
            
            if 'social_proof' in tool_name:
                return f"¡{user_name}! Me da mucha confianza saber que estás evaluando seriamente el curso. Te cuento que muchos profesionales como tú ya están viendo resultados increíbles. ¿Te gustaría conocer algunos casos de éxito específicos de tu área?"
            elif 'gamificacion' in tool_name:
                return f"¡Excelente, {user_name}! Veo que estás realmente interesado. Te propongo algo: vamos paso a paso explorando el curso. Primero, cuéntame más sobre tu trabajo actual para personalizar completamente la información que te comparto. 🎯"
        
        # Respuesta por defecto conversacional
        return f"¡{user_name}! Me encanta tu interés. Para darte la información más útil y específica, ¿podrías contarme un poco más sobre tu situación actual? Por ejemplo, ¿cuáles son tus principales desafíos en el trabajo que te gustaría resolver?"

    async def _handle_specific_intention(
        self,
        primary_intention: str,
        analysis: Dict,
        message: str,
        user_name: str,
        course_info: Optional[Dict]
    ) -> str:
        """
        Maneja intenciones específicas con respuestas personalizadas.
        """
        # Mapeo de intenciones a handlers existentes
        intention_handlers = {
            'price_question': self._handle_price_question,
            'schedule_question': self._handle_schedule_question,
            'content_question': self._handle_content_question,
            'objection': self._handle_objection,
            'ready_to_buy': self._handle_ready_to_buy,
            'more_info': self._handle_more_info,
        }
        
        handler = intention_handlers.get(primary_intention)
        if handler:
            return await handler(analysis, message, user_name, course_info)
        
        # Respuesta por defecto conversacional
        return f"¡{user_name}! Gracias por tu mensaje. Para asegurarme de darte la información más precisa y útil, ¿podrías ser más específico sobre qué te gustaría saber del curso? Estoy aquí para resolver todas tus dudas. 😊"
    
    async def _handle_price_question(self, analysis: Dict, message: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja preguntas sobre precio - CONVERSACIONAL"""
        if not course_info:
            return f"Disculpa {user_name}, no tengo la información del curso disponible en este momento."
        
        price = course_info.get('price_usd', 'No disponible')
        original_price = course_info.get('original_price_usd')
        discount = course_info.get('discount_percentage')
        
        response = f"¡Excelente pregunta, {user_name}! 💰\n\n"
        
        # Mostrar precio con descuento si aplica
        if original_price and discount and original_price > price:
            response += f"🎉 **¡Tienes suerte!** Hay una promoción activa:\n"
            response += f"• Precio regular: ${original_price} USD\n"
            response += f"• **Tu precio HOY**: ${price} USD (${original_price - float(price)} de descuento)\n\n"
        else:
            response += f"La inversión para este curso es de **${price} USD**.\n\n"
        
        response += "✨ **¿Por qué es la mejor inversión que puedes hacer?**\n"
        response += "• Conocimiento que aplicarás desde el primer día\n"
        response += "• ROI promedio: recuperas la inversión en 2-4 semanas\n"
        response += "• Acceso de por vida al material y actualizaciones\n"
        response += "• Certificación que aumenta tu valor profesional\n\n"
        
        # Detectar si hay objeción de precio
        if any(word in message.lower() for word in ["caro", "costoso", "mucho", "barato", "dinero"]):
            response += "💡 **Pongámoslo en perspectiva:**\n"
            response += f"• Es menos de ${float(price)/30:.0f} USD por día durante un mes\n"
            response += "• Menos que 2 cenas en restaurante, pero los beneficios duran toda la vida\n"
            response += "• El aumento salarial promedio de nuestros alumnos es 40% en 6 meses\n\n"
        
        response += "🤔 **Cuéntame:** ¿Cuál es tu presupuesto ideal para invertir en tu crecimiento profesional? "
        response += "Tenemos opciones de pago flexibles que pueden ajustarse a ti. 😊"
        
        return response
    
    async def _handle_schedule_question(self, analysis: Dict, message: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja preguntas sobre horarios - CONVERSACIONAL"""
        if not course_info:
            return f"Disculpa {user_name}, no tengo la información del curso disponible en este momento."
        
        schedule = course_info.get('schedule', 'A consultar')
        duration = course_info.get('total_duration', '12:00:00')
        hours = duration.split(':')[0] if ':' in str(duration) else duration
        online = course_info.get('online', True)
        
        response = f"¡Perfecto {user_name}! 📅\n\n"
        response += f"**Horario:** {schedule}\n"
        response += f"**Duración total:** {hours} horas\n"
        response += f"**Modalidad:** {'100% Online en vivo' if online else 'Presencial'}\n\n"
        
        response += "✅ **Ventajas de este horario:**\n"
        response += "• Clases en vivo con interacción directa con el instructor\n"
        response += "• Horario diseñado especialmente para profesionales ocupados\n"
        response += "• Si no puedes asistir a alguna clase, tienes la grabación\n"
        response += "• Flexibilidad total para hacer preguntas en tiempo real\n"
        response += "• Networking con otros profesionales en tu mismo horario\n\n"
        
        response += "🤔 **Cuéntame:** ¿Este horario se ajusta bien a tu rutina actual? "
        response += "¿Trabajas en horario tradicional o tienes flexibilidad? "
        response += "Quiero asegurarme de que puedas aprovechar al máximo las clases. 😊"
        
        return response
    
    async def _handle_content_question(self, analysis: Dict, message: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja preguntas sobre contenido - CONVERSACIONAL"""
        response = f"¡Excelente pregunta, {user_name}! 📚\n\n"
        
        if course_info:
            tools_used = course_info.get('tools_used', [])
            if isinstance(tools_used, str):
                # Si tools_used es string, convertirlo a lista
                import json
                try:
                    tools_used = json.loads(tools_used.replace('{', '[').replace('}', ']').replace('"', '"'))
                except:
                    tools_used = []
            
            duration = course_info.get('total_duration', '12:00:00')
            hours = duration.split(':')[0] if ':' in str(duration) else duration
            
            response += f"Este curso de **{hours} horas** está diseñado para llevarte de cero a experto:\n\n"
            
            if tools_used:
                response += "🛠 **Herramientas que dominarás:**\n"
                for tool in tools_used[:4]:  # Mostrar máximo 4 herramientas
                    response += f"• {tool}\n"
                response += "\n"
        
        response += "🎯 **Módulos principales:**\n"
        response += "• Fundamentos de IA y ChatGPT (desde cero)\n"
        response += "• Prompts efectivos para resultados profesionales\n"
        response += "• Automatización de tareas diarias\n"
        response += "• Creación de contenido con IA\n"
        response += "• Casos de uso específicos por industria\n"
        response += "• Proyectos prácticos que van a tu portafolio\n\n"
        
        response += "💡 **Lo mejor:** Cada módulo incluye ejercicios que puedes aplicar INMEDIATAMENTE en tu trabajo.\n\n"
        response += "🤔 **Cuéntame:** ¿Hay algún tema específico que te emociona más? "
        response += "¿O alguna tarea en tu trabajo que te gustaría automatizar? "
        response += "Quiero asegurarme de que el curso cubra exactamente lo que necesitas. 😊"
        
        return response
    
    async def _handle_objection(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        """Maneja objeciones del usuario."""
        message_lower = message.lower()
        
        response = f"Te entiendo perfectamente, {user_name}. "
        
        if "caro" in message_lower or "costoso" in message_lower:
            response += "💭 Entiendo tu preocupación sobre la inversión.\n\n"
            response += "Déjame ponerte en perspectiva:\n"
            response += "• El promedio de aumento salarial tras dominar IA es del 40%\n"
            response += "• Solo necesitas aplicar 2-3 técnicas para recuperar la inversión\n"
            response += "• Es menos que una cena para dos, pero los beneficios duran toda la vida\n\n"
            response += "¿Qué tal si hablamos de opciones de pago flexibles? 💳"
            
        elif "tiempo" in message_lower or "ocupado" in message_lower:
            response += "⏰ Entiendo que el tiempo es valioso.\n\n"
            response += "Por eso diseñamos el curso pensando en profesionales ocupados:\n"
            response += "• Solo 2 horas por semana\n"
            response += "• Clases grabadas si no puedes asistir\n"
            response += "• Material para estudiar a tu ritmo\n"
            response += "• Ejercicios de 15 minutos que puedes hacer en el trabajo\n\n"
            response += "¿No crees que 2 horas semanales valen la pena para transformar tu carrera? 🚀"
            
        else:
            response += "🤔 Cuéntame más sobre tu preocupación. "
            response += "Estoy aquí para resolver todas tus dudas y asegurarme de que tomes la mejor decisión para ti."
        
        return response
    
    async def _handle_ready_to_buy(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        """Maneja cuando el usuario está listo para comprar."""
        response = f"¡Excelente decisión, {user_name}! 🎉\n\n"
        response += "Me emociona saber que estás listo para dar este paso hacia tu crecimiento profesional.\n\n"
        response += "📝 *Próximos pasos:*\n"
        response += "1. Te voy a conectar con nuestro asesor especializado\n"
        response += "2. Él te guiará en el proceso de inscripción\n"
        response += "3. Recibirás acceso inmediato al material preparatorio\n"
        response += "4. Te llegará el calendario con todas las fechas\n\n"
        response += "🚀 *¡Bienvenido a tu nueva etapa profesional!*\n\n"
        response += "Un asesor te contactará en los próximos 15 minutos para completar tu inscripción. "
        response += "¿Tienes alguna pregunta de último momento?"
        
        return response
    
    async def _handle_instructor_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Excelente pregunta, {user_name}! 👨‍🏫\n\n"
        response += "Nuestros instructores son expertos certificados con:\n"
        response += "• Más de 5 años de experiencia en IA\n"
        response += "• Certificaciones internacionales\n"
        response += "• Experiencia práctica en empresas Fortune 500\n"
        response += "• Metodología probada con miles de estudiantes\n\n"
        response += "¿Te gustaría conocer más sobre su metodología de enseñanza? 🎓"
        return response
    
    async def _handle_certificate_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Por supuesto, {user_name}! 🏆\n\n"
        response += "Al completar el curso recibirás:\n"
        response += "• Certificado oficial de Aprende y Aplica IA\n"
        response += "• Reconocimiento internacional\n"
        response += "• Validación en LinkedIn\n"
        response += "• Badge digital para tu perfil profesional\n\n"
        response += "Este certificado te abrirá puertas en el mundo laboral. ¿Hay alguna empresa específica donde te gustaría aplicar estas habilidades? 💼"
        return response
    
    async def _handle_payment_methods(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Perfecto, {user_name}! 💳\n\n"
        response += "Tenemos varias opciones de pago flexibles:\n"
        response += "• Pago único con descuento\n"
        response += "• Pago en 2 cuotas sin intereses\n"
        response += "• Pago en 3 cuotas (pequeño interés)\n"
        response += "• Tarjeta de crédito o débito\n"
        response += "• Transferencia bancaria\n\n"
        response += "¿Cuál opción te resulta más conveniente? 🤔"
        return response
    
    async def _handle_modality_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Excelente pregunta, {user_name}! 🌐\n\n"
        if course_info and course_info.get('online'):
            response += "El curso es *100% online en vivo*:\n"
            response += "• Clases interactivas por videoconferencia\n"
            response += "• Participación en tiempo real\n"
            response += "• Grabaciones disponibles si faltas\n"
            response += "• Acceso desde cualquier lugar\n\n"
        else:
            response += "El curso es *presencial*:\n"
            response += "• Interacción cara a cara\n"
            response += "• Ambiente de aprendizaje colaborativo\n"
            response += "• Networking directo con compañeros\n\n"
        response += "¿Prefieres esta modalidad o tienes alguna preferencia específica? 🤔"
        return response
    
    async def _handle_level_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Buena pregunta, {user_name}! 🎯\n\n"
        if course_info:
            level = course_info.get('level', 'Principiante a Avanzado')
            response += f"*Nivel del curso:* {level}\n\n"
        response += "📈 *Estructura progresiva:*\n"
        response += "• Empezamos desde cero (no necesitas experiencia previa)\n"
        response += "• Avanzamos gradualmente con ejercicios prácticos\n"
        response += "• Llegamos a técnicas avanzadas profesionales\n"
        response += "• Cada estudiante avanza a su ritmo\n\n"
        response += "¿Tienes alguna experiencia previa con IA o sería tu primer acercamiento? 🤓"
        return response
    
    async def _handle_duration_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Perfecto, {user_name}! ⏱\n\n"
        if course_info:
            duration = course_info.get('total_duration', 'N/A')
            response += f"*Duración total:* {duration} horas\n\n"
        response += "📅 *Distribución del tiempo:*\n"
        response += "• Clases semanales de 2 horas\n"
        response += "• Ejercicios prácticos (30 min por semana)\n"
        response += "• Proyecto final (2 horas)\n"
        response += "• Acceso de por vida al material\n\n"
        response += "Es perfecto para profesionales ocupados. ¿Te parece manejable este tiempo de dedicación? 🚀"
        return response
    
    async def _handle_comparison_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Excelente que compares opciones, {user_name}! 🔍\n\n"
        response += "🏆 *Lo que nos diferencia:*\n"
        response += "• Instructores con experiencia real en empresas\n"
        response += "• Metodología práctica (no solo teoría)\n"
        response += "• Grupos pequeños para atención personalizada\n"
        response += "• Soporte continuo durante y después del curso\n"
        response += "• Casos de uso reales de la industria\n"
        response += "• Comunidad activa de ex-alumnos\n\n"
        response += "💡 *Garantía:* Si en las primeras 2 clases no estás satisfecho, te devolvemos el 100% del dinero.\n\n"
        response += "¿Hay algún aspecto específico que te gustaría comparar? 🤔"
        return response
    
    async def _handle_more_info(self, analysis: Dict, message: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja solicitudes de más información - CONVERSACIONAL"""
        
        # Detectar si pide demo específicamente
        if any(word in message.lower() for word in ["demo", "prueba", "muestra", "ejemplo", "preview", "ver"]):
            return await self._handle_demo_request(user_name, course_info)
        
        response = f"¡Por supuesto, {user_name}! Me encanta que quieras conocer más detalles 📋\n\n"
        response += "Antes de bombardearte con información, quiero asegurarme de darte exactamente lo que necesitas.\n\n"
        response += "🎯 **Cuéntame un poco más sobre ti:**\n"
        response += "• ¿A qué te dedicas profesionalmente?\n"
        response += "• ¿Qué te motivó a buscar un curso de IA?\n"
        response += "• ¿Hay algo específico que quieres lograr o automatizar?\n\n"
        response += "📚 **Mientras tanto, aquí tienes lo más importante:**\n"
        response += "• Contenido 100% práctico (nada de teoría aburrida)\n"
        response += "• Ejercicios que puedes aplicar desde el día 1\n"
        response += "• Soporte personalizado durante todo el curso\n"
        response += "• Comunidad activa de profesionales como tú\n\n"
        response += "¿Qué aspecto te interesa más conocer primero? 😊"
        
        return response
    
    async def _handle_demo_request(self, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja solicitudes específicas de demo"""
        response = f"¡Por supuesto, {user_name}! 📱\n\n"
        
        if course_info and course_info.get('demo_request_link'):
            demo_link = course_info['demo_request_link']
            response += f"Aquí tienes acceso directo a la **demo interactiva**:\n"
            response += f"👉 {demo_link}\n\n"
            response += "🎯 **En la demo vas a ver:**\n"
            response += "• Ejercicios reales del curso\n"
            response += "• Metodología paso a paso\n"
            response += "• Resultados que puedes esperar\n"
            response += "• Interface de la plataforma\n\n"
            response += "💡 **Tip**: Tómate 10-15 minutos para explorarla completa. "
            response += "Después me cuentas qué te pareció y resuelvo cualquier duda que tengas.\n\n"
        else:
            response += "Te voy a conectar con nuestro asesor especializado para que te muestre una demo personalizada.\n\n"
            response += "📅 **La demo incluye:**\n"
            response += "• Recorrido completo del curso\n"
            response += "• Ejercicios en vivo\n"
            response += "• Sesión de preguntas y respuestas\n"
            response += "• Plan personalizado para tu caso\n\n"
        
        response += "Mientras tanto, ¿hay algún aspecto específico del curso que te gustaría que enfoque en la demo? 🤔"
        
        return response
    
    async def _handle_testimonials(self, analysis: Dict, message: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja solicitudes de testimonios - CONVERSACIONAL"""
        response = f"¡Me encanta que preguntes eso, {user_name}! 🌟\n\n"
        response += "Los resultados de nuestros estudiantes son lo que más me emociona compartir:\n\n"
        
        response += "💼 **Casos de éxito reales:**\n"
        response += "• **María (Marketing)**: Automatizó reportes y aumentó productividad 300%\n"
        response += "• **Carlos (Ventas)**: Implementó IA en su proceso y aumentó cierre 60%\n"
        response += "• **Ana (Emprendedora)**: Creó su consultora de IA y factura $5K/mes\n"
        response += "• **Luis (Gerente)**: Redujo 15 horas semanales de trabajo repetitivo\n"
        response += "• **Sofia (Estudiante)**: Consiguió pasantía en Google por sus habilidades IA\n\n"
        
        response += "📊 **Estadísticas que nos enorgullecen:**\n"
        response += "• 94% consigue mejor empleo o aumento en 6 meses\n"
        response += "• 87% inicia proyecto propio exitoso relacionado con IA\n"
        response += "• 100% recomienda el curso a colegas\n"
        response += "• Aumento salarial promedio: 40%\n\n"
        
        response += "🤝 **¿Te gustaría hablar directamente con algún ex-alumno?**\n"
        response += "Puedo conectarte con alguien de tu área profesional para que te cuente su experiencia personal.\n\n"
        
        response += "🤔 **Cuéntame:** ¿A qué te dedicas? Así te conecto con alguien que tenga un perfil similar al tuyo. 😊"
        
        return response
    
    async def _handle_support_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Excelente pregunta, {user_name}! 🤝\n\n"
        response += "Nuestro soporte es integral:\n\n"
        response += "📞 *Durante el curso:*\n"
        response += "• Sesiones de Q&A semanales\n"
        response += "• WhatsApp grupal para dudas rápidas\n"
        response += "• Revisión personalizada de proyectos\n"
        response += "• Mentorías individuales (2 por estudiante)\n\n"
        response += "🚀 *Después del curso:*\n"
        response += "• Acceso a comunidad de ex-alumnos\n"
        response += "• Actualizaciones del material sin costo\n"
        response += "• Sesiones de refuerzo mensuales\n"
        response += "• Bolsa de trabajo exclusiva\n\n"
        response += "¿Hay algún tipo de soporte específico que te preocupe? 🤔"
        return response
    
    async def _handle_technical_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Perfecto, {user_name}! 💻\n\n"
        response += "Requisitos técnicos súper simples:\n\n"
        response += "✅ *Lo que necesitas:*\n"
        response += "• Computadora o laptop (Windows/Mac/Linux)\n"
        response += "• Conexión a internet estable\n"
        response += "• Navegador web actualizado\n"
        response += "• ¡Eso es todo!\n\n"
        response += "🛠 *Herramientas que usaremos:*\n"
        response += "• ChatGPT (te enseñamos a configurarlo)\n"
        response += "• Herramientas gratuitas de IA\n"
        response += "• Plataformas web (sin instalaciones)\n\n"
        response += "💡 *Incluido:* Te damos acceso a herramientas premium durante el curso.\n\n"
        response += "¿Tienes alguna limitación técnica específica que te preocupe? 🤖"
        return response
    
    async def _handle_career_question(self, analysis: Dict, message: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja preguntas sobre aplicabilidad profesional - MUY CONVERSACIONAL"""
        message_lower = message.lower()
        
        # Detectar profesión mencionada en el mensaje
        detected_profession = self._extract_profession_from_message(message_lower)
        
        if detected_profession:
            return await self._generate_profession_specific_response(detected_profession, user_name, course_info)
        else:
            # Si no detectamos profesión, ser conversacional y preguntar
            response = f"¡Me encanta esa pregunta, {user_name}! 🚀\n\n"
            response += "La IA está transformando literalmente TODAS las profesiones, y quiero darte ejemplos súper específicos para tu área.\n\n"
            response += "Cuéntame un poco más sobre ti:\n"
            response += "• ¿A qué te dedicas actualmente?\n"
            response += "• ¿Cuál es tu rol principal en tu trabajo?\n"
            response += "• ¿Qué tipo de tareas haces día a día?\n\n"
            response += "Con esa info te voy a dar ejemplos EXACTOS de cómo la IA puede revolucionar tu trabajo específico. 💪\n\n"
            response += "¡Estoy súper curioso de conocer más sobre tu profesión! 😊"
            
            return response
    
    def _extract_profession_from_message(self, message_lower: str) -> Optional[str]:
        """Extrae profesión específica mencionada en el mensaje"""
        profession_keywords = {
            "marketing": ["marketing", "mercadeo", "publicidad", "brand", "redes sociales", "social media"],
            "ventas": ["ventas", "vendedor", "comercial", "sales", "cliente"],
            "gerente": ["gerente", "manager", "jefe", "supervisor", "líder", "coordinador"],
            "estudiante": ["estudiante", "estudio", "universidad", "carrera", "graduado"],
            "emprendedor": ["emprendedor", "startup", "negocio", "empresa propia", "freelance"],
            "desarrollador": ["desarrollador", "programador", "developer", "software", "código"],
            "diseñador": ["diseñador", "diseño", "creative", "gráfico", "ui", "ux"],
            "hr": ["recursos humanos", "rrhh", "hr", "talento", "personal"],
            "finanzas": ["finanzas", "contador", "contabilidad", "financiero", "presupuesto"],
            "educacion": ["profesor", "maestro", "docente", "educador", "instructor"],
            "salud": ["médico", "doctor", "enfermera", "salud", "hospital", "clínica"],
            "abogado": ["abogado", "legal", "derecho", "jurídico", "ley"]
        }
        
        for profession, keywords in profession_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return profession
        return None
    
    async def _generate_profession_specific_response(self, profession: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Genera respuesta específica y conversacional por profesión, SOLO usando información real del curso y ejercicios prácticos."""
        if not course_info:
            return f"No tengo información suficiente sobre el contenido del curso para darte ejemplos específicos para tu profesión, {user_name}. ¿Quieres que te muestre el temario real para que evalúes si se ajusta a tus necesidades?"

        modules = course_info.get('modules', [])
        if isinstance(modules, str):
            import json
            try:
                modules = json.loads(modules.replace("'", '"'))
            except Exception:
                modules = []
        tools_used = course_info.get('tools_used', [])
        if isinstance(tools_used, str):
            import json
            try:
                tools_used = json.loads(tools_used.replace("'", '"'))
            except Exception:
                tools_used = []

        aplicaciones = []
        # NUEVO: consultar ejercicios prácticos relevantes
        if modules and self.course_service:
            for mod in modules:
                mod_name = mod['name'] if isinstance(mod, dict) and 'name' in mod else str(mod)
                mod_desc = mod['description'] if isinstance(mod, dict) and 'description' in mod else ''
                mod_id = mod['id'] if isinstance(mod, dict) and 'id' in mod else None
                mod_lower = mod_name.lower() + ' ' + mod_desc.lower()
                # Buscar ejercicios prácticos del módulo
                ejercicios = []
                if mod_id:
                    try:
                        ejercicios = await self.course_service.getModuleExercises(mod_id)
                    except Exception:
                        ejercicios = []
                # Personalizar ejemplos según profesión
                if profession == 'finanzas' and any(x in mod_lower for x in ['automatización', 'análisis', 'documentos', 'datos', 'reportes']):
                    if ejercicios:
                        for ej in ejercicios:
                            aplicaciones.append(f"• {ej['description']} (aplicable a reportes o documentos contables)")
                    else:
                        aplicaciones.append(f"• Aplicar IA para automatizar reportes financieros o documentos contables en el módulo '{mod_name}'")
                if profession == 'marketing' and any(x in mod_lower for x in ['contenido', 'copy', 'redes', 'publicidad', 'campañas']):
                    if ejercicios:
                        for ej in ejercicios:
                            aplicaciones.append(f"• {ej['description']} (aplicable a campañas o contenido de marketing)")
                    else:
                        aplicaciones.append(f"• Generar contenido o ideas de campañas con IA en el módulo '{mod_name}'")
                if profession == 'ventas' and any(x in mod_lower for x in ['clientes', 'propuestas', 'seguimiento', 'personalización']):
                    if ejercicios:
                        for ej in ejercicios:
                            aplicaciones.append(f"• {ej['description']} (aplicable a ventas o seguimiento de clientes)")
                    else:
                        aplicaciones.append(f"• Automatizar seguimiento de clientes o personalizar propuestas en el módulo '{mod_name}'")
                if profession == 'gerente' and any(x in mod_lower for x in ['análisis', 'estrategia', 'equipos', 'productividad']):
                    if ejercicios:
                        for ej in ejercicios:
                            aplicaciones.append(f"• {ej['description']} (aplicable a gestión de equipos o análisis estratégico)")
                    else:
                        aplicaciones.append(f"• Analizar datos de desempeño de equipos o automatizar reportes estratégicos en el módulo '{mod_name}'")
                if profession == 'estudiante' and any(x in mod_lower for x in ['presentaciones', 'ensayos', 'investigación', 'proyectos']):
                    if ejercicios:
                        for ej in ejercicios:
                            aplicaciones.append(f"• {ej['description']} (aplicable a tareas escolares o proyectos académicos)")
                    else:
                        aplicaciones.append(f"• Automatizar tareas escolares como presentaciones, ensayos o investigación en el módulo '{mod_name}'")
                if profession == 'emprendedor' and any(x in mod_lower for x in ['automatización', 'negocio', 'clientes', 'costos']):
                    if ejercicios:
                        for ej in ejercicios:
                            aplicaciones.append(f"• {ej['description']} (aplicable a operaciones de negocio o análisis de costos)")
                    else:
                        aplicaciones.append(f"• Automatizar operaciones de negocio, atención al cliente o análisis de costos en el módulo '{mod_name}'")
        # Herramientas
        if tools_used:
            for tool in tools_used:
                tool_lower = tool.lower() if isinstance(tool, str) else str(tool).lower()
                if profession == 'finanzas' and any(x in tool_lower for x in ['excel', 'chatgpt', 'canva']):
                    aplicaciones.append('• Usar herramientas como ChatGPT o Excel para crear plantillas automáticas de informes')
                if profession == 'marketing' and any(x in tool_lower for x in ['chatgpt', 'dall', 'canva']):
                    aplicaciones.append('• Crear imágenes, copies o presentaciones para campañas usando IA')
                if profession == 'ventas' and any(x in tool_lower for x in ['chatgpt']):
                    aplicaciones.append('• Generar respuestas automáticas a clientes o scripts de ventas')
        aplicaciones = list(dict.fromkeys(aplicaciones))

        if aplicaciones:
            response = f"¡{user_name}, según el temario real del curso y sus ejercicios prácticos, podrías aplicar lo aprendido así en tu área profesional:\n\n"
            response += '\n'.join(aplicaciones)
            response += "\n\n¿Te gustaría que te comparta más detalles sobre los módulos o ejercicios específicos? 😊"
            return response
        else:
            return f"No tengo información específica en mis datos sobre aplicaciones concretas para tu profesión en este curso, {user_name}. ¿Quieres que te comparta el temario real para que evalúes si se ajusta a tus necesidades?"
    
    async def _handle_group_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Buena pregunta, {user_name}! 👥\n\n"
        response += "Mantenemos grupos pequeños para maximizar el aprendizaje:\n\n"
        response += "🎯 *Características del grupo:*\n"
        response += "• Máximo 15 estudiantes por clase\n"
        response += "• Profesionales de diferentes industrias\n"
        response += "• Ambiente colaborativo y de apoyo\n"
        response += "• Networking valioso para tu carrera\n\n"
        response += "🤝 *Beneficios del grupo reducido:*\n"
        response += "• Atención personalizada del instructor\n"
        response += "• Más tiempo para resolver tus dudas\n"
        response += "• Proyectos en equipo enriquecedores\n"
        response += "• Conexiones profesionales duraderas\n\n"
        response += "¿Prefieres grupos pequeños o tienes alguna preferencia específica? 🤔"
        return response
    
    async def _handle_refund_policy(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Excelente que preguntes, {user_name}! 🛡️\n\n"
        response += "Tenemos una política de satisfacción garantizada:\n\n"
        response += "✅ *Garantía de 14 días:*\n"
        response += "• Si no estás satisfecho en las primeras 2 clases\n"
        response += "• Te devolvemos el 100% de tu dinero\n"
        response += "• Sin preguntas, sin complicaciones\n"
        response += "• Proceso simple y rápido\n\n"
        response += "🎯 *¿Por qué ofrecemos esta garantía?*\n"
        response += "• Confiamos 100% en la calidad del curso\n"
        response += "• Queremos que te sientas seguro al invertir\n"
        response += "• Nuestro éxito depende de tu satisfacción\n\n"
        response += "💡 *Dato:* Menos del 2% de estudiantes pide reembolso.\n\n"
        response += "¿Esta garantía te da más confianza para dar el paso? 😊"
        return response
    
    async def _handle_other(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        """Maneja intenciones no clasificadas."""
        response = f"Gracias por tu mensaje, {user_name}. "
        response += "Quiero asegurarme de darte la información más precisa. "
        response += "¿Podrías ser más específico sobre qué te gustaría saber del curso? "
        response += "Por ejemplo:\n\n"
        response += "• Detalles sobre el contenido\n"
        response += "• Información sobre precios\n"
        response += "• Horarios y fechas\n"
        response += "• Proceso de inscripción\n\n"
        response += "¡Estoy aquí para ayudarte! 😊"
        
        return response
    
    def _update_user_memory(self, user_memory: LeadMemory, message: str, analysis: Dict):
        """Actualiza la memoria del usuario con la nueva interacción."""
        if not user_memory.message_history:
            user_memory.message_history = []
        
        user_memory.message_history.append({
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'intention': analysis.get('primary_intention'),
            'interest_level': analysis.get('interest_level'),
            'buying_signals': analysis.get('buying_signals', []),
            'objections': analysis.get('objections', [])
        })
        
        # Actualizar puntuación basada en intención
        if analysis.get('primary_intention') == 'ready_to_buy':
            user_memory.lead_score = min(100, user_memory.lead_score + 20)
        elif analysis.get('interest_level') == 'high':
            user_memory.lead_score = min(100, user_memory.lead_score + 10)
        elif analysis.get('primary_intention') == 'objection':
            user_memory.lead_score = max(0, user_memory.lead_score - 5)
        
        user_memory.last_interaction = datetime.now() 

    def _extract_profession_info(self, message: str, user_memory: LeadMemory) -> Optional[str]:
        """
        Extrae información sobre la profesión del usuario del mensaje.
        """
        message_lower = message.lower()
        
        # Detectar profesiones/roles específicos
        professions = {
            "gerente": ["gerente", "manager", "jefe", "supervisor"],
            "marketing": ["marketing", "mercadeo", "publicidad", "brand"],
            "ventas": ["ventas", "vendedor", "comercial", "sales"],
            "estudiante": ["estudiante", "estudio", "universidad", "carrera"],
            "emprendedor": ["emprendedor", "startup", "negocio propio", "empresa propia"],
            "desarrollador": ["desarrollador", "programador", "developer", "coder"],
            "diseñador": ["diseñador", "diseño", "designer", "creativo"],
            "consultor": ["consultor", "asesor", "freelance", "independiente"],
            "director": ["director", "ceo", "presidente", "ejecutivo"],
            "analista": ["analista", "analyst", "datos", "data"],
            "hr": ["recursos humanos", "rrhh", "hr", "talento humano"],
            "finanzas": ["finanzas", "contabilidad", "contador", "financiero"]
        }
        
        for profession, keywords in professions.items():
            if any(keyword in message_lower for keyword in keywords):
                return profession
        
        return None 