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

EXTRACCIÓN DE INFORMACIÓN (SUTILMENTE):
- ¿En qué trabajas? / ¿A qué te dedicas?
- ¿Qué es lo que más tiempo te consume en tu trabajo?
- ¿Has usado alguna herramienta de IA antes?
- ¿Qué te frustra más de tus tareas diarias?
- ¿Qué te gustaría automatizar si pudieras?

REGLAS DE ORO:
1. NUNCA repitas información que ya sabes del usuario
2. PERSONALIZA cada respuesta basándote en lo que ya conoces
3. USA SOLO información 100% real de la base de datos
4. NO inventes estadísticas, testimonios o características del curso
5. Si no sabes algo específico del curso, sé honesta: "Déjame verificar eso para ti"

CATEGORÍAS DE RESPUESTA:
- EXPLORACIÓN: Ayuda a descubrir necesidades sin presionar
- EDUCACIÓN: Comparte valor sobre IA de manera útil
- OBJECIÓN_PRECIO: Enfócate en retorno de inversión real
- OBJECIÓN_TIEMPO: Muestra flexibilidad y eficiencia
- OBJECIÓN_VALOR: Demuestra resultados concretos
- OBJECIÓN_CONFIANZA: Usa transparencia y honestidad
- SEÑALES_COMPRA: Facilita el siguiente paso de manera natural
- NECESIDAD_AUTOMATIZACIÓN: Conecta con módulos específicos del curso
- PREGUNTA_GENERAL: Responde útilmente y conecta naturalmente

EJEMPLO DE CONVERSACIÓN NATURAL:
Usuario: "Trabajo en marketing y paso horas creando contenido"
Respuesta: "¡Ay, entiendo perfectamente! El marketing puede ser súper demandante con todo el contenido que hay que crear. Me imagino que debe ser agotador estar siempre pensando en posts, emails, copys... ¿Qué tipo de contenido es el que más tiempo te consume? Porque justamente tenemos módulos que pueden ayudarte a automatizar mucho de eso."

IMPORTANTE:
- Siempre mantén el tono cálido y personal
- Haz que la persona se sienta escuchada y comprendida
- Conecta naturalmente con cómo el curso puede ayudar específicamente a SU situación
- Sé paciente, la confianza se construye gradualmente
- Recuerda: eres una amiga que quiere ayudar, no solo vender
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

    async def _analyze_user_intent(self, user_message: str, user_memory: LeadMemory) -> Dict[str, Any]:
        """
        Analiza el mensaje del usuario para detectar intenciones y decidir qué herramientas usar.
        """
        if not self.client:
            return self._get_default_intent()
            
        try:
            # Preparar historial de mensajes recientes
            recent_messages = []
            if user_memory.message_history:
                recent_messages = [
                    msg.get('content', '') 
                    for msg in user_memory.message_history[-3:] 
                    if msg.get('role') == 'user'
                ]

            # Preparar información de automatización conocida
            automation_info = ""
            if user_memory.automation_needs:
                automation_info = f"""
                Necesidades de automatización conocidas:
                - Tipos de reportes: {', '.join(user_memory.automation_needs.get('report_types', []))}
                - Frecuencia: {user_memory.automation_needs.get('frequency', 'No especificada')}
                - Tiempo invertido: {user_memory.automation_needs.get('time_investment', 'No especificado')}
                - Herramientas actuales: {', '.join(user_memory.automation_needs.get('current_tools', []))}
                - Frustraciones: {', '.join(user_memory.automation_needs.get('specific_frustrations', []))}
                """

            intent_prompt = f"""
            Clasifica el mensaje del usuario en una de estas CATEGORÍAS PRINCIPALES:

            1. EXPLORATION - Usuario explorando, preguntando sobre el curso
            2. OBJECTION_PRICE - Preocupación por el precio/inversión
            3. OBJECTION_TIME - Preocupación por tiempo/horarios
            4. OBJECTION_VALUE - Dudas sobre si vale la pena/sirve
            5. OBJECTION_TRUST - Dudas sobre confiabilidad/calidad
            6. BUYING_SIGNALS - Señales de interés en comprar
            7. AUTOMATION_NEED - Necesidad específica de automatización
            8. PROFESSION_CHANGE - Cambio de profesión/área de trabajo
            9. GENERAL_QUESTION - Pregunta general sobre IA/tecnología

            MENSAJE ACTUAL: {user_message}

            CONTEXTO DEL USUARIO:
            - Profesión actual: {user_memory.role if user_memory.role else 'No especificada'}
            - Intereses conocidos: {', '.join(user_memory.interests if user_memory.interests else [])}
            - Puntos de dolor: {', '.join(user_memory.pain_points if user_memory.pain_points else [])}
            - Mensajes recientes: {recent_messages}
            {automation_info}

            IMPORTANTE: 
            - Si ya tienes información suficiente del usuario, NO pidas más detalles
            - Si el usuario cambió de profesión, actualiza y conecta con el curso
            - Si menciona automatización, conecta directamente con beneficios del curso
            - Si muestra objeciones, activa herramientas de ventas

            Responde SOLO con JSON:
            {{
                "category": "CATEGORIA_PRINCIPAL",
                "confidence": 0.8,
                "should_ask_more": false,
                "recommended_tools": {{
                    "show_bonuses": false,
                    "show_demo": false,
                    "show_resources": false,
                    "show_testimonials": false
                }},
                "sales_strategy": "direct_benefit|explore_need|handle_objection|close_sale",
                "key_topics": [],
                "response_focus": "Qué debe enfocar la respuesta"
            }}
            """

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": intent_prompt}],
                max_tokens=300,
                temperature=0.1
            )

            content = response.choices[0].message.content
            if not content:
                return self._get_default_intent()

            intent_analysis = self._safe_json_parse(content)
            if not intent_analysis:
                return self._get_default_intent()

            return intent_analysis

        except Exception as e:
            logger.error(f"Error analizando intención: {e}")
            return self._get_default_intent()

    def _get_default_intent(self) -> Dict[str, Any]:
        """Retorna un análisis de intención por defecto"""
        return {
            "category": "GENERAL_QUESTION",
            "confidence": 0.5,
            "should_ask_more": False,
            "recommended_tools": {
                "show_bonuses": False,
                "show_demo": False,
                "show_resources": False,
                "show_testimonials": False
            },
            "sales_strategy": "direct_benefit",
            "key_topics": [],
            "response_focus": "Responder directamente y mostrar beneficios"
        }

    def _detect_objection_type(self, message: str) -> str:
        """Detecta el tipo de objeción en el mensaje del usuario."""
        message_lower = message.lower()
        
        objection_patterns = {
            'price': ['caro', 'costoso', 'precio', 'dinero', 'presupuesto', 'barato', 'económico'],
            'time': ['tiempo', 'ocupado', 'horario', 'disponible', 'rápido', 'lento', 'duración'],
            'trust': ['confianza', 'seguro', 'garantía', 'estafa', 'real', 'verdad', 'experiencia'],
            'value': ['necesito', 'útil', 'sirve', 'funciona', 'beneficio', 'resultado', 'vale la pena'],
            'decision': ['pensarlo', 'decidir', 'consultar', 'después', 'más tarde', 'mañana']
        }
        
        objection_scores = {}
        for objection_type, keywords in objection_patterns.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                objection_scores[objection_type] = score
        
        if objection_scores:
            return max(objection_scores.keys(), key=lambda x: objection_scores[x])
        else:
            return 'general'

    def _detect_buying_signals(self, message: str) -> List[str]:
        """Detecta señales de compra en el mensaje del usuario."""
        buying_signals = []
        message_lower = message.lower()
        
        signal_patterns = {
            'ready_to_buy': ['comprar', 'adquirir', 'inscribir', 'registrar'],
            'payment_interest': ['pagar', 'precio', 'costo', 'tarjeta', 'transferencia'],
            'timing_questions': ['cuando', 'inicio', 'empezar', 'comenzar'],
            'urgency': ['ya', 'ahora', 'inmediato', 'rápido', 'urgente'],
            'value_accepted': ['perfecto', 'excelente', 'me gusta', 'interesante']
        }
        
        for signal_type, keywords in signal_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                buying_signals.append(signal_type)
        
        return buying_signals

    def _calculate_interest_score(self, message: str, user_memory: LeadMemory) -> int:
        """Calcula una puntuación de interés basada en el mensaje y historial."""
        score = 50  # Base score
        
        # Analizar mensaje actual
        buying_signals = self._detect_buying_signals(message)
        score += len(buying_signals) * 10
        
        # Analizar historial
        if user_memory.message_history:
            score += min(len(user_memory.message_history) * 5, 30)
            
            # Buscar progresión de interés
            recent_messages = user_memory.message_history[-3:] if len(user_memory.message_history) >= 3 else user_memory.message_history
            for msg in recent_messages:
                if any(word in msg.get('content', '').lower() for word in ['precio', 'pago', 'inscribir']):
                    score += 15
        
        # Normalizar entre 0-100
        return min(max(score, 0), 100)

    async def generate_response(self, user_message: str, user_memory: LeadMemory, course_info: Optional[Dict]) -> Union[str, List[Dict[str, str]]]:
        """Genera una respuesta personalizada usando OpenAI"""
        if self.client is None:
            return "Lo siento, hay un problema con el sistema. Por favor intenta más tarde."
        
        try:
            # Analizar intención del usuario
            intent_analysis = await self._analyze_user_intent(user_message, user_memory)
            
            # Detectar objeciones y señales de compra
            objection_type = self._detect_objection_type(user_message)
            buying_signals = self._detect_buying_signals(user_message)
            interest_score = self._calculate_interest_score(user_message, user_memory)
            
            # Actualizar puntuación de interés
            user_memory.lead_score = interest_score
            user_memory.interaction_count += 1
            
            # CRÍTICO: Guardar mensaje del usuario en historial
            if user_memory.message_history is None:
                user_memory.message_history = []
            
            user_memory.message_history.append({
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Extraer información del mensaje del usuario
            await self._extract_user_info(user_message, user_memory)
            
            # Actualizar memoria con temas clave detectados
            key_topics = intent_analysis.get('key_topics', [])
            if key_topics and isinstance(key_topics, list):
                if user_memory.interests is None:
                    user_memory.interests = []
                user_memory.interests.extend(key_topics)
                user_memory.interests = list(set(user_memory.interests))
            
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
            
            # Agregar análisis de intención al contexto
            intent_context = f"""
## Análisis de Intención:
- Categoría: {intent_analysis.get('category', 'GENERAL_QUESTION')}
- Confianza: {intent_analysis.get('confidence', 0.5)}
- Estrategia de ventas: {intent_analysis.get('sales_strategy', 'direct_benefit')}
- Enfoque de respuesta: {intent_analysis.get('response_focus', 'Responder directamente')}
- Debe preguntar más: {intent_analysis.get('should_ask_more', False)}

## Herramientas Recomendadas:
{json.dumps(intent_analysis.get('recommended_tools', {}), indent=2, ensure_ascii=False)}

## Información Acumulada del Usuario:
- Profesión: {user_memory.role if user_memory.role else 'No especificada'}
- Intereses: {', '.join(user_memory.interests if user_memory.interests else ['Ninguno registrado'])}
- Puntos de dolor: {', '.join(user_memory.pain_points if user_memory.pain_points else ['Ninguno registrado'])}
- Nivel de interés: {user_memory.interest_level}
- Interacciones: {user_memory.interaction_count}
"""

            # Agregar información de automatización si existe
            if user_memory.automation_needs and any(user_memory.automation_needs.values()):
                automation_context = f"""
## Necesidades de Automatización Identificadas:
- Tipos de reportes: {', '.join(user_memory.automation_needs.get('report_types', []))}
- Frecuencia: {user_memory.automation_needs.get('frequency', 'No especificada')}
- Tiempo invertido: {user_memory.automation_needs.get('time_investment', 'No especificado')}
- Herramientas actuales: {', '.join(user_memory.automation_needs.get('current_tools', []))}
- Frustraciones específicas: {', '.join(user_memory.automation_needs.get('specific_frustrations', []))}

INSTRUCCIÓN ESPECIAL: El usuario YA expresó necesidades de automatización. NO preguntes más detalles. 
Conecta DIRECTAMENTE con cómo el curso resuelve estos problemas específicos.
"""
                intent_context += automation_context

            system_message = intent_context + "\n" + system_message
            
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
                    
                    # Obtener bonos disponibles
                    bonuses = await self.course_service.getAvailableBonuses(course_info['id'])
                    if bonuses:
                        bonuses_info = "\n## Bonos por Tiempo Limitado:\n"
                        for bonus in bonuses:
                            if bonus and bonus.get('active'):  # Solo bonos activos
                                bonuses_info += f"""
- {bonus.get('name', 'Sin nombre')}:
  Descripción: {bonus.get('description', 'No disponible')}
  Valor: ${bonus.get('original_value', '0')} USD
  Propuesta: {bonus.get('value_proposition', 'No disponible')}
  Expira: {bonus.get('expires_at', 'No disponible')}
  Cupos: {bonus.get('max_claims', '0')} totales, {bonus.get('current_claims', '0')} reclamados
"""
                        system_message += "\n" + bonuses_info
            
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
                model="gpt-4o-mini",  # Corregir nombre del modelo
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            # Obtener la respuesta
            response_text = response.choices[0].message.content
            if not response_text:
                return "Lo siento, no pude generar una respuesta."
            
            # Validar la respuesta si tenemos información del curso
            if course_info:
                # Obtener bonos disponibles para validación
                bonuses = await self.course_service.getAvailableBonuses(course_info['id'])
                
                # Validar respuesta incluyendo bonos
                validation = await self.prompt_service.validate_response(
                    response=response_text,
                    course_data=course_info,
                    bonuses_data=bonuses
                )
                
                if not validation.get('is_valid', True):
                    errors = validation.get('errors', [])
                    logger.warning(f"Respuesta inválida para usuario {user_memory.user_id}: {', '.join(errors)}")
                    
                    # Si la respuesta es inválida, intentar generar una nueva
                    return await self.generate_response(user_message, user_memory, course_info)
            
            # Procesar la respuesta y activar herramientas si es necesario
            final_response = await self._process_response(response_text, user_memory)
            
            # Activar herramientas basado en el análisis de intención
            if intent_analysis.get('recommended_tools'):
                tools = intent_analysis['recommended_tools']
                await self._activate_recommended_tools(tools, user_memory, course_info)
            
            return final_response
                
        except Exception as e:
            logger.error(f"Error generando respuesta: {e}", exc_info=True)
            return "Lo siento, ocurrió un error al procesar tu mensaje. Por favor intenta nuevamente."
    
    def _safe_json_parse(self, content: str) -> Optional[Dict]:
        """
        Parsea JSON de forma segura, limpiando el contenido si es necesario.
        """
        if not content:
            return None
            
        try:
            # Limpiar el contenido
            content = content.strip()
            
            # Remover markdown si existe
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            # Intentar parsear directamente
            return json.loads(content)
            
        except json.JSONDecodeError:
            try:
                # Buscar JSON dentro del texto
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
                
        except Exception:
            pass
            
        return None

    async def _extract_user_info(self, user_message: str, user_memory: LeadMemory):
        """Extrae información relevante del mensaje del usuario"""
        if not self.client:
            return
            
        try:
            extraction_prompt = f"""
            Analiza el siguiente mensaje del usuario para extraer información relevante sobre sus necesidades, intereses y puntos de dolor.
            Presta especial atención a menciones sobre:
            - Automatización de procesos o reportes
            - Tipos específicos de reportes o documentos
            - Frecuencia de tareas manuales
            - Tiempo invertido en tareas
            - Herramientas o software actual
            - Frustraciones o problemas específicos

            MENSAJE DEL USUARIO:
            {user_message}

            CONTEXTO ACTUAL:
            - Profesión: {user_memory.role if user_memory.role else 'No disponible'}
            - Intereses conocidos: {', '.join(user_memory.interests if user_memory.interests else [])}
            - Puntos de dolor conocidos: {', '.join(user_memory.pain_points if user_memory.pain_points else [])}

            Devuelve un JSON con el siguiente formato:
            {{
                "role": "profesión o rol detectado",
                "interests": ["lista", "de", "intereses"],
                "pain_points": ["lista", "de", "problemas"],
                "automation_needs": {{
                    "report_types": ["tipos", "de", "reportes"],
                    "frequency": "frecuencia de tareas",
                    "time_investment": "tiempo invertido",
                    "current_tools": ["herramientas", "actuales"],
                    "specific_frustrations": ["frustraciones", "específicas"]
                }}
            }}
            """

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Corregir nombre del modelo
                messages=[{"role": "user", "content": extraction_prompt}],
                max_tokens=500,
                temperature=0.1
            )

            content = response.choices[0].message.content
            if not content:
                return

            extracted_info = self._safe_json_parse(content)
            if not extracted_info:
                return

            # Actualizar información del usuario
            if extracted_info.get('role'):
                user_memory.role = extracted_info['role']

            # Actualizar intereses
            if extracted_info.get('interests'):
                if user_memory.interests is None:
                    user_memory.interests = []
                user_memory.interests.extend(extracted_info['interests'])
                user_memory.interests = list(set(user_memory.interests))

            # Actualizar puntos de dolor
            if extracted_info.get('pain_points'):
                if user_memory.pain_points is None:
                    user_memory.pain_points = []
                user_memory.pain_points.extend(extracted_info['pain_points'])
                user_memory.pain_points = list(set(user_memory.pain_points))

            # Guardar información de automatización
            automation_needs = extracted_info.get('automation_needs', {})
            if automation_needs:
                if user_memory.automation_needs is None:
                    user_memory.automation_needs = {
                        "report_types": [],
                        "frequency": "",
                        "time_investment": "",
                        "current_tools": [],
                        "specific_frustrations": []
                    }
                user_memory.automation_needs.update(automation_needs)

        except Exception as e:
            logger.error(f"Error extrayendo información del usuario: {e}")

    async def _process_response(self, response_text: str, user_memory: LeadMemory) -> Union[str, List[Dict[str, str]]]:
        """Procesa la respuesta del LLM y actualiza historial de conversación"""
        
        # CRÍTICO: Actualizar historial de conversación
        if user_memory.message_history is None:
            user_memory.message_history = []
        
        # Agregar la respuesta del bot al historial
        user_memory.message_history.append({
            'role': 'assistant',
            'content': response_text,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Limitar historial a los últimos 20 mensajes para evitar sobrecarga
        if len(user_memory.message_history) > 20:
            user_memory.message_history = user_memory.message_history[-20:]
        
        # Actualizar timestamp de última interacción
        user_memory.last_interaction = datetime.utcnow()
        user_memory.updated_at = datetime.utcnow()
        
        # Verificar si la respuesta contiene múltiples mensajes
        if "[MENSAJE_" in response_text:
            # Dividir por mensajes
            import re
            message_parts = re.split(r'\[MENSAJE_\d+\]', response_text)
            message_parts = [part.strip() for part in message_parts if part.strip()]
            
            messages = []
            for part in message_parts:
                if part:
                    messages.append({
                        'type': 'text',
                        'content': part
                    })
            return messages
        else:
            # Mensaje único como string
            return response_text

    async def _activate_recommended_tools(self, tools: Dict[str, bool], user_memory: LeadMemory, course_info: Optional[Dict]):
        """Activa herramientas recomendadas por el análisis de intención"""
        try:
            course_id = user_memory.selected_course or (course_info.get('id') if course_info else None)
            if not course_id:
                return
            
            # Marcar que se han usado herramientas de ventas
            if any(tools.values()):
                user_memory.buying_signals = user_memory.buying_signals or []
                user_memory.buying_signals.append("tools_activated")
            
            # Log de herramientas activadas para métricas
            activated_tools = [tool for tool, active in tools.items() if active]
            if activated_tools:
                logger.info(f"Herramientas activadas para usuario {user_memory.user_id}: {activated_tools}")
                
                # Guardar en historial que se activaron herramientas
                if user_memory.message_history is None:
                    user_memory.message_history = []
                
                user_memory.message_history.append({
                    'role': 'system',
                    'content': f"Herramientas activadas: {', '.join(activated_tools)}",
                    'timestamp': datetime.utcnow().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error activando herramientas: {e}") 