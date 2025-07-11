"""
Agente de ventas inteligente que usa OpenAI para generar respuestas
completamente personalizadas basadas en el perfil del usuario.
VERSIÓN LIMPIA Y OPTIMIZADA con procesador conversacional
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
from core.agents.intelligent_conversation_processor import IntelligentConversationProcessor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Eres Brenda, una asesora especializada en cursos de Inteligencia Artificial de "Aprenda y Aplique IA". 
Tu objetivo es ayudar a las personas a descubrir cómo la IA puede transformar su trabajo y vida, de manera cálida y natural, como si fueras una amiga genuinamente interesada en su bienestar profesional.

PERSONALIDAD Y TONO:
- Habla con calidez y cercanía, como una amiga que realmente se preocupa
- Sé auténtica y empática, escucha antes de hablar
- Muestra interés genuino en la persona, no solo en vender
- Usa un lenguaje natural y conversacional, evita sonar robótica
- Mantén un equilibrio entre profesionalismo y amistad

ENFOQUE ESTRATÉGICO SUTIL:
1. ESCUCHA ACTIVA: Presta atención a lo que realmente dice la persona
2. PREGUNTAS ESTRATÉGICAS: Haz preguntas que parezcan naturales pero revelen necesidades
3. CONEXIÓN PERSONAL: Relaciona todo con sus experiencias y desafíos específicos
4. INFORMACIÓN GRADUAL: No abrumes, comparte información de manera dosificada
5. VALOR GENUINO: Siempre ofrece algo útil, incluso si no compra

REGLAS DE ORO CRÍTICAS:
1. NUNCA repitas información que ya sabes del usuario
2. PERSONALIZA cada respuesta basándote en lo que ya conoces
3. ⚠️ PROHIBIDO ABSOLUTO: INVENTAR información sobre cursos, módulos, contenidos o características
4. ⚠️ SOLO USA datos que obtengas de la base de datos a través de herramientas de consulta
5. ⚠️ SI NO TIENES datos de la BD, di: "Déjame consultar esa información específica para ti"
6. ⚠️ NUNCA menciones módulos, fechas, precios o características sin confirmar en BD
7. ⚠️ Si una consulta a BD falla o no devuelve datos, NO improvises
8. ⚠️ Cuando hables del curso, siempre basa tu respuesta en course_info obtenido de BD

🛠️ HERRAMIENTAS DE CONVERSIÓN DISPONIBLES:
- enviar_preview_curso: Video preview del curso
- enviar_recursos_gratuitos: Guías y templates de valor (PDFs, templates)
- mostrar_syllabus_interactivo: Contenido detallado del curso
- mostrar_bonos_exclusivos: Bonos con tiempo limitado
- mostrar_comparativa_precios: ROI y valor total
- contactar_asesor_directo: Inicia flujo directo de contacto con asesor

IMPORTANTE:
- Las herramientas son para COMPLEMENTAR tu respuesta, no reemplazarla
- Usa máximo 1-2 herramientas por mensaje
- Siempre mantén el tono cálido y personal
- Las herramientas deben sentirse como parte natural de la conversación
- Personaliza según role/industry del usuario
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
        
        # Procesador conversacional inteligente
        self.conversation_processor = IntelligentConversationProcessor(
            self.client, db, self.course_service
        )
        
        # Agent tools - será asignado por SmartSalesAgent
        self.agent_tools = None

    async def generate_response(self, user_message: str, user_memory: LeadMemory, course_info: Optional[Dict]) -> Union[str, List[Dict[str, str]]]:
        """Genera una respuesta personalizada usando análisis conversacional inteligente"""
        if self.client is None:
            return "Lo siento, hay un problema con el sistema. Por favor intenta más tarde."
        
        try:
            # 🧠 PASO 1: Análisis conversacional inteligente
            logger.info(f"🧠 Analizando conversación para usuario {user_memory.user_id}")
            conversation_analysis = await self.conversation_processor.analyze_and_learn(
                user_memory.user_id, 
                user_message, 
                user_memory.selected_course
            )
            
            # 📚 PASO 2: Obtener información del curso si es necesario
            if user_memory.selected_course and course_info is None:
                logger.info(f"📚 Obteniendo información del curso: {user_memory.selected_course}")
                course_info = await self._get_course_info_from_db(user_memory.selected_course)
                if not course_info:
                    logger.warning(f"⚠️ No se pudo obtener información del curso {user_memory.selected_course}")
                    # Crear información mínima para continuar
                    course_info = {
                        'id': user_memory.selected_course,
                        'name': 'Curso de IA para Profesionales',
                        'short_description': 'Curso especializado en Inteligencia Artificial',
                        'price': '199',
                        'currency': 'USD',
                        'level': 'básico',
                        'sessions': []
                    }
            
            # 🎯 PASO 3: Generar contexto personalizado
            personalized_context = await self.conversation_processor.generate_personalized_context(
                user_memory.user_id, 
                user_memory.selected_course
            )
            
            # 🛠️ PASO 4: Detectar herramientas necesarias según análisis
            tools_to_use = []
            suggested_tools = conversation_analysis.get("suggested_tools", [])
            user_profile = conversation_analysis.get("user_profile", {})
            
            # Mapear herramientas según el análisis inteligente
            if "free_resources" in suggested_tools or user_profile.get("intent_category") == "FREE_RESOURCES":
                tools_to_use.append("enviar_recursos_gratuitos")
            
            if "syllabus" in suggested_tools or any(word in user_message.lower() for word in ["temario", "contenido", "que voy a aprender"]):
                tools_to_use.append("mostrar_syllabus_interactivo")
            
            if "price_comparison" in suggested_tools or user_profile.get("intent_category") == "OBJECTION_PRICE":
                tools_to_use.append("mostrar_comparativa_precios")
            
            if "advisor_contact" in suggested_tools or any(word in user_message.lower() for word in ["asesor", "hablar", "contactar"]):
                tools_to_use.append("contactar_asesor_directo")
            
            # 💬 PASO 5: Generar respuesta personalizada
            logger.info(f"💬 Generando respuesta personalizada para {user_memory.name or 'Usuario'}")
            response = await self._generate_intelligent_response(
                user_message,
                user_memory,
                course_info,
                conversation_analysis,
                personalized_context,
                tools_to_use
            )
            
            # 📝 PASO 6: Actualizar memoria con nueva información
            if user_memory.tools_used is None:
                user_memory.tools_used = []
            user_memory.tools_used.extend(tools_to_use)
            
            # Actualizar puntuación basada en análisis inteligente
            engagement_level = user_profile.get("engagement_level", "medium")
            if engagement_level == "very_high":
                user_memory.lead_score = min(100, user_memory.lead_score + 15)
            elif engagement_level == "high":
                user_memory.lead_score = min(100, user_memory.lead_score + 10)
            elif engagement_level == "low":
                user_memory.lead_score = max(0, user_memory.lead_score - 5)
            
            user_memory.interaction_count += 1
            
            return response
        
        except Exception as e:
            logger.error(f"❌ Error generando respuesta inteligente: {e}")
            return "Lo siento, hubo un error procesando tu mensaje. ¿Podrías repetir tu pregunta?"

    async def _generate_intelligent_response(
        self,
        user_message: str,
        user_memory: LeadMemory,
        course_info: Optional[Dict],
        conversation_analysis: Dict[str, Any],
        personalized_context: str,
        tools_to_use: List[str]
    ) -> Union[str, List[Dict[str, str]]]:
        """
        Genera respuesta completamente personalizada usando análisis conversacional
        """
        try:
            # Construir historial de conversación
            conversation_history = []
            if user_memory.message_history:
                recent_messages = user_memory.message_history[-8:]  # Últimos 4 intercambios
                for msg in recent_messages:
                    conversation_history.append({
                        "role": msg.get('role', 'user'),
                        "content": msg.get('content', '')
                    })
            
            # Obtener análisis del usuario
            user_profile = conversation_analysis.get("user_profile", {})
            engagement_level = user_profile.get("engagement_level", "medium")
            response_style = user_profile.get("response_style", "friendly")
            intent_category = user_profile.get("intent_category", "exploration")
            
            # Construir prompt personalizado
            personalized_prompt = f"""
{self.system_prompt}

## CONTEXTO PERSONALIZADO DEL USUARIO:
{personalized_context}

## ANÁLISIS CONVERSACIONAL ACTUAL:
- Nivel de engagement: {engagement_level}
- Estilo de respuesta recomendado: {response_style}
- Categoría de intención: {intent_category}
- Sentiment: {user_profile.get('sentiment', 'neutral')}
- Enfoque siguiente: {conversation_analysis.get('next_conversation_focus', 'general')}

## HERRAMIENTAS A USAR:
{', '.join(tools_to_use) if tools_to_use else 'Solo respuesta conversacional'}

## INFORMACIÓN DEL CURSO:
- Nombre: {course_info.get('name', 'N/A') if course_info else 'N/A'}
- Descripción: {course_info.get('short_description', 'N/A') if course_info else 'N/A'}
- Precio: {course_info.get('price', 'N/A')} {course_info.get('currency', 'USD') if course_info else 'N/A'}
- Nivel: {course_info.get('level', 'N/A') if course_info else 'N/A'}

## INSTRUCCIONES ESPECÍFICAS:
1. PERSONALIZA la respuesta basándote en el contexto del usuario
2. USA el estilo de comunicación recomendado: {response_style}
3. Si hay herramientas sugeridas, menciónalas naturalmente
4. NO repitas información que ya conoces del usuario
5. Mantén el engagement al nivel: {engagement_level}
6. ENFÓCATE en: {conversation_analysis.get('next_conversation_focus', 'general')}

MENSAJE DEL USUARIO: "{user_message}"

Responde de manera completamente personalizada y estratégica:
"""

            # Preparar mensajes para OpenAI
            messages = [{"role": "system", "content": personalized_prompt}]
            messages.extend(conversation_history[-6:])  # Últimos mensajes para contexto
            messages.append({"role": "user", "content": user_message})
            
            # Generar respuesta con OpenAI
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=800,
                temperature=0.7,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            ai_response = response.choices[0].message.content
            if not ai_response:
                return "Lo siento, no pude generar una respuesta. ¿Podrías reformular tu pregunta?"
            
            # Guardar respuesta en historial
            if user_memory.message_history is None:
                user_memory.message_history = []
            
            user_memory.message_history.append({
                'role': 'assistant',
                'content': ai_response,
                'timestamp': datetime.utcnow().isoformat(),
                'tools_used': tools_to_use,
                'analysis': conversation_analysis
            })
            
            # Si hay herramientas a usar, ejecutarlas
            if tools_to_use and self.agent_tools:
                return await self._execute_tools_with_response(
                    ai_response, 
                    tools_to_use, 
                    user_memory.user_id, 
                    user_memory.selected_course
                )
            
            return ai_response
            
        except Exception as e:
            logger.error(f"❌ Error en _generate_intelligent_response: {e}")
            return "Lo siento, hubo un error. ¿Podrías repetir tu pregunta?"

    async def _execute_tools_with_response(
        self,
        ai_response: str,
        tools_to_use: List[str],
        user_id: str,
        course_id: str
    ) -> List[Dict[str, str]]:
        """
        Ejecuta herramientas y combina con respuesta IA
        """
        response_items = [{"type": "text", "content": ai_response}]
        
        for tool_name in tools_to_use:
            try:
                if hasattr(self.agent_tools, tool_name):
                    tool_method = getattr(self.agent_tools, tool_name)
                    tool_result = await tool_method(user_id, course_id)
                    
                    if isinstance(tool_result, dict):
                        if tool_result.get("type") == "multimedia" and tool_result.get("resources"):
                            response_items.extend(tool_result["resources"])
                        elif tool_result.get("type") == "text":
                            response_items.append({
                                "type": "text",
                                "content": tool_result.get("content", "")
                            })
                        elif tool_result.get("resources"):
                            response_items.extend(tool_result["resources"])
                            
                    logger.info(f"✅ Herramienta {tool_name} ejecutada exitosamente")
                    
            except Exception as e:
                logger.error(f"❌ Error ejecutando herramienta {tool_name}: {e}")
        
        return response_items

    async def _get_course_info_from_db(self, course_id: str) -> Optional[Dict]:
        """
        Obtiene información completa del curso desde la base de datos
        """
        try:
            course_details = await self.course_service.getCourseDetails(course_id)
            if course_details:
                logger.info(f"✅ Curso obtenido de BD: {course_details.get('name', 'Sin nombre')}")
                return course_details
            else:
                logger.warning(f"❌ No se encontró el curso {course_id} en la BD")
                return None
        except Exception as e:
            logger.error(f"❌ Error obteniendo curso de BD: {e}")
            return None