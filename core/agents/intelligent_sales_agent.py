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
Tienes acceso a herramientas avanzadas que DEBES usar inteligentemente según el momento apropiado:

**HERRAMIENTAS DE DEMOSTRACIÓN:**
- enviar_preview_curso: Video preview del curso
- mostrar_recursos_gratuitos: Guías y templates de valor
- mostrar_syllabus_interactivo: Contenido detallado del curso

**HERRAMIENTAS DE PERSUASIÓN:**
- mostrar_bonos_exclusivos: Bonos con tiempo limitado
- presentar_oferta_limitada: Descuentos especiales
- mostrar_testimonios_relevantes: Social proof personalizado
- mostrar_comparativa_precios: ROI y valor total

**HERRAMIENTAS DE URGENCIA:**
- generar_urgencia_dinamica: Cupos limitados, datos reales
- mostrar_social_proof_inteligente: Compradores similares
- mostrar_casos_exito_similares: Resultados de personas como el usuario

**HERRAMIENTAS DE CIERRE:**
- agendar_demo_personalizada: Sesión 1:1 con instructor
- personalizar_oferta_por_budget: Opciones de pago flexibles
- mostrar_garantia_satisfaccion: Garantía de 30 días
- ofrecer_plan_pagos: Facilidades de pago
- contactar_asesor_directo: Inicia flujo directo de contacto con asesor

**HERRAMIENTAS AVANZADAS:**
- mostrar_comparativa_competidores: Ventajas únicas
- implementar_gamificacion: Progreso y logros
- generar_oferta_dinamica: Oferta personalizada por comportamiento

📊 CUÁNDO USAR CADA HERRAMIENTA:

**AL DETECTAR INTERÉS INICIAL (primera conversación):**
- Si pregunta por contenido → mostrar_syllabus_interactivo
- Si quiere ver antes de decidir → enviar_preview_curso
- Si necesita convencerse del valor → mostrar_recursos_gratuitos

**AL DETECTAR OBJECIONES:**
- Objeción de precio → mostrar_comparativa_precios + personalizar_oferta_por_budget
- Objeción de valor → mostrar_casos_exito_similares + mostrar_testimonios_relevantes
- Objeción de confianza → mostrar_garantia_satisfaccion + mostrar_social_proof_inteligente
- Objeción de tiempo → mostrar_syllabus_interactivo (mostrar flexibilidad)

**AL DETECTAR SEÑALES DE COMPRA:**
- Preguntas sobre precio → presentar_oferta_limitada
- Interés en hablar con alguien → contactar_asesor_directo
- Comparando opciones → mostrar_comparativa_competidores
- Dudando entre opciones → mostrar_bonos_exclusivos
- Necesita ayuda personalizada → contactar_asesor_directo

**PARA CREAR URGENCIA (usuarios tibios):**
- Usuario indeciso → generar_urgencia_dinamica + mostrar_social_proof_inteligente
- Múltiples interacciones sin decidir → presentar_oferta_limitada
- Usuario analítico → mostrar_comparativa_precios + mostrar_casos_exito_similares

**ESTRATEGIA DE USO:**
1. **Sutil al principio**: Usa 1 herramienta por conversación máximo
2. **Progresivo**: Si responde bien, puedes usar 2-3 herramientas relacionadas
3. **Inteligente**: Analiza su perfil (role, industry) para personalizar
4. **Natural**: Las herramientas deben fluir naturalmente en la conversación
5. **No invasivo**: Si rechaza algo, cambia de estrategia

CATEGORÍAS DE RESPUESTA:
- EXPLORACIÓN: Ayuda a descubrir necesidades + mostrar_syllabus_interactivo
- EDUCACIÓN: Comparte valor + mostrar_recursos_gratuitos
- OBJECIÓN_PRECIO: ROI real + mostrar_comparativa_precios + personalizar_oferta_por_budget
- OBJECIÓN_TIEMPO: Flexibilidad + mostrar_syllabus_interactivo
- OBJECIÓN_VALOR: Resultados + mostrar_casos_exito_similares + mostrar_testimonios_relevantes
- OBJECIÓN_CONFIANZA: Transparencia + mostrar_garantia_satisfaccion + mostrar_social_proof_inteligente
- SEÑALES_COMPRA: Facilita siguiente paso + presentar_oferta_limitada + agendar_demo_personalizada + contactar_asesor_directo
- NECESIDAD_AUTOMATIZACIÓN: Conecta con curso + enviar_preview_curso
- PREGUNTA_GENERAL: Responde útilmente + herramienta relevante

EJEMPLOS DE CONVERSACIÓN CON HERRAMIENTAS:

**Ejemplo 1: Usuario interesado en contenido**
Usuario: "Trabajo en marketing y paso horas creando contenido"
Respuesta: "¡Ay, entiendo perfectamente! El marketing puede ser súper demandante con todo el contenido que hay que crear. Me imagino que debe ser agotador estar siempre pensando en posts, emails, copys... ¿Qué tipo de contenido es el que más tiempo te consume? Porque justamente nuestro curso tiene módulos específicos que pueden ayudarte a automatizar mucho de eso. ¿Te gustaría ver algunos ejemplos prácticos de cómo otros marketers han aplicado estas técnicas?"
[Activar: mostrar_casos_exito_similares si responde positivamente]

**Ejemplo 2: Usuario que quiere hablar con asesor**
Usuario: "Puedo hablar con un asesor?"
Respuesta: "¡Por supuesto! Te voy a conectar con un asesor especializado que podrá atender todas tus dudas de manera personalizada. Déjame recopilar algunos datos para que el asesor pueda contactarte..."
[Activar: contactar_asesor_directo]

**Ejemplo 3: Usuario con dudas complejas**
Usuario: "Tengo varias dudas específicas sobre mi situación"
Respuesta: "Entiendo que tienes dudas específicas, y me parece perfecto que quieras asegurarte de tomar la mejor decisión. Te voy a conectar con un asesor especializado que podrá resolver todas tus dudas de manera personalizada..."
[Activar: contactar_asesor_directo]

IMPORTANTE:
- Las herramientas son para COMPLEMENTAR tu respuesta, no reemplazarla
- Usa máximo 1-2 herramientas por mensaje
- Siempre mantén el tono cálido y personal
- Las herramientas deben sentirse como parte natural de la conversación
- Personaliza según role/industry del usuario
- Si una herramienta no funciona, cambia de estrategia

**CUÁNDO USAR contactar_asesor_directo:**
✅ ÚSALA cuando detectes:
- Usuario dice "puedo hablar con un asesor", "necesito hablar con alguien"
- Preguntas muy específicas de su industria/situación
- Objeciones complejas que necesitan atención personalizada
- Usuario indeciso después de múltiples interacciones
- Solicitud directa de contacto con asesor
- Dudas que requieren atención personalizada

❌ NO la uses si:
- Es una pregunta simple que puedes responder
- Usuario solo está explorando información básica
- No hay indicación clara de querer hablar con asesor

**CRÍTICO: SOLICITUDES DE ASESOR:**
- Si el usuario menciona "asesor", "hablar con alguien", "contactar", etc.
- NUNCA generes una respuesta de texto
- SIEMPRE usa la herramienta contactar_asesor_directo
- Esta herramienta inicia el flujo completo automáticamente
- NO escribas respuestas como "te conectaré con un asesor" - usa la herramienta

**REGLA DE ORO**: Si detectas cualquier solicitud de contacto con asesor:
1. NO escribas texto de respuesta
2. USA contactar_asesor_directo inmediatamente  
3. El sistema manejará todo el resto automáticamente
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
        
        # Agent tools - será asignado por SmartSalesAgent
        self.agent_tools = None

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

    async def _get_course_info_from_db(self, course_id: str) -> Optional[Dict]:
        """Obtiene información real del curso desde la base de datos."""
        try:
            if not course_id:
                return None
            
            # Usar CourseService para obtener información real
            course_details = await self.course_service.getCourseDetails(course_id)
            if course_details:
                # Obtener módulos también
                modules = await self.course_service.getCourseModules(course_id)
                if modules:
                    course_details['modules'] = modules
                
                # Obtener bonos disponibles
                bonuses = await self.course_service.getAvailableBonuses(course_id)
                if bonuses:
                    course_details['bonuses'] = bonuses
                    
            return course_details
            
        except Exception as e:
            logger.error(f"Error obteniendo información del curso {course_id}: {e}")
            return None
    
    async def _validate_course_content_mention(self, response_text: str, course_info: Dict) -> bool:
        """Valida que no se mencione contenido inventado del curso."""
        try:
            if not course_info:
                return True
                
            # Lista de palabras que indican contenido específico del curso
            content_indicators = [
                'módulo', 'módulos', 'capítulo', 'capítulos', 'lección', 'lecciones',
                'temario', 'contenido', 'syllabus', 'programa', 'plan de estudios'
            ]
            
            response_lower = response_text.lower()
            mentions_content = any(indicator in response_lower for indicator in content_indicators)
            
            if not mentions_content:
                return True  # No menciona contenido específico, está bien
                
            # Si menciona contenido, verificar que tengamos módulos reales
            real_modules = course_info.get('modules', [])
            if not real_modules:
                logger.warning("Respuesta menciona contenido pero no hay módulos reales en BD")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validando contenido del curso: {e}")
            return True  # En caso de error, permitir la respuesta

    async def generate_response(self, user_message: str, user_memory: LeadMemory, course_info: Optional[Dict]) -> Union[str, List[Dict[str, str]]]:
        """Genera una respuesta personalizada usando OpenAI"""
        if self.client is None:
            return "Lo siento, hay un problema con el sistema. Por favor intenta más tarde."
        
        try:
            # CRÍTICO: Solo obtener información del curso si NO se pasó una válida
            if user_memory.selected_course and course_info is None:
                logger.info(f"Obteniendo información del curso desde BD: {user_memory.selected_course}")
                course_info = await self._get_course_info_from_db(user_memory.selected_course)
                if not course_info:
                    logger.warning(f"No se pudo obtener información del curso {user_memory.selected_course}")
            elif course_info:
                logger.info(f"✅ Usando course_info pasado correctamente para curso: {user_memory.selected_course}")
            
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
            
            # 🛡️ PROTECCIÓN: Nunca permitir curso incorrecto
            if user_memory.selected_course == "b00f3d1c-e876-4bac-b734-2715110440a0":
                user_memory.selected_course = "a392bf83-4908-4807-89a9-95d0acc807c9"
            
            # ✅ CRÍTICO: Si hay curso seleccionado del flujo de anuncios, NUNCA cambiarlo
            if user_memory.selected_course:
                logger.info(f"🎯 CURSO FIJO del flujo de anuncios: {user_memory.selected_course}")
                if not course_info:
                    course_info = await self.course_service.getCourseDetails(user_memory.selected_course)
                    if not course_info:
                        logger.warning(f"❌ No se pudo obtener detalles del curso seleccionado: {user_memory.selected_course}")
                        # Mantener el curso seleccionado aunque falle la consulta
                        return "⚠️ Curso no seleccionado. Por favor, inicia el proceso desde el anuncio del curso que te interesa."
                # NUNCA buscar otros cursos - el curso está determinado por el flujo de anuncios
            else:
                # Solo buscar referencias a cursos si NO hay curso seleccionado previamente
                course_references = await self.prompt_service.extract_course_references(user_message)
                
                # Solo buscar otros cursos si NO hay curso seleccionado del flujo de anuncios
                if course_references:
                    for reference in course_references:
                        # Buscar cursos que coincidan con la referencia
                        courses = await self.course_service.searchCourses(reference)
                        if courses:
                            # 🛡️ CRÍTICO: NUNCA sobrescribir course_info si ya hay selected_course del flujo de anuncios
                            if not user_memory.selected_course:
                                # Solo usar el primer curso encontrado si NO hay curso seleccionado previamente
                                course_info = await self.course_service.getCourseDetails(courses[0]['id'])
                                user_memory.selected_course = courses[0]['id']
                            break
                
                # Si aún no hay curso seleccionado, mostrar mensaje de curso no seleccionado
                if not user_memory.selected_course and not course_info:
                    return "⚠️ Curso no seleccionado. Por favor, inicia el proceso desde el anuncio del curso que te interesa."
            
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
## ⚠️ INFORMACIÓN REAL DEL CURSO (ÚNICA FUENTE AUTORIZADA):
- Nombre EXACTO: {course_info.get('name', 'No disponible')}
- Descripción corta: {course_info.get('short_description', 'No disponible')}
- Descripción completa: {course_info.get('long_description', 'No disponible')}
- Duración total: {course_info.get('total_duration', 'No disponible')}
- Precio (USD): {course_info.get('price_usd', 'No disponible')}
- Nivel: {course_info.get('level', 'No disponible')}
- Categoría: {course_info.get('category', 'No disponible')}
- Herramientas usadas: {', '.join(str(t) for t in course_info.get('tools_used', ['No disponible']))}
- Prerrequisitos: {', '.join(str(p) for p in course_info.get('prerequisites', ['No disponible']))}
- Requerimientos: {', '.join(str(r) for r in course_info.get('requirements', ['No disponible']))}
- Horario: {course_info.get('schedule', 'No disponible')}

⚠️ REGLA CRÍTICA: Solo usa la información de arriba. NO menciones módulos específicos a menos que estén listados abajo.
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
            
            # CRÍTICO: Validar que no se inventó contenido del curso
            if course_info:
                content_valid = await self._validate_course_content_mention(response_text, course_info)
                if not content_valid:
                    logger.warning(f"Respuesta menciona contenido inventado para curso {course_info.get('id')}")
                    return "Perfecto, me da mucho gusto que estés interesado en el curso. Déjame consultar la información específica del contenido para darte detalles precisos. ¿Hay algo particular que te gustaría saber sobre el curso?"
                
                # Validar respuesta con datos reales de BD
                bonuses = course_info.get('bonuses', [])
                if not bonuses:
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
                    
                    # Si la respuesta es inválida, devolver respuesta segura
                    return "Te entiendo perfectamente. Déjame obtener la información más actualizada sobre el curso para responderte con precisión. ¿Qué aspecto específico te interesa más?"
            
            # Procesar la respuesta y activar herramientas si es necesario
            final_response = await self._process_response(response_text, user_memory)
            
            # Activar herramientas basado en el análisis de intención
            activated_tools = await self._activate_tools_based_on_intent(
                intent_analysis, user_memory, course_info, user_message
            )
            
            # Si se activaron herramientas, incluir información en la respuesta
            if activated_tools:
                logger.info(f"Herramientas activadas: {activated_tools}")
            
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
    
    async def _activate_tools_based_on_intent(
        self, 
        intent_analysis: Dict, 
        user_memory, 
        course_info: Optional[Dict],
        user_message: str
    ) -> List[str]:
        """Wrapper para activar herramientas - implementación en módulo separado"""
        try:
            # Verificar que agent_tools esté disponible
            if not self.agent_tools:
                logger.warning("Agent tools no está disponible. Las herramientas no se activarán.")
                return []
                
            from core.agents.intelligent_sales_agent_tools import IntelligentSalesAgentTools
            tools_handler = IntelligentSalesAgentTools(self.agent_tools)
            
            user_id = user_memory.user_id
            return await tools_handler._activate_tools_based_on_intent(
                intent_analysis, user_memory, course_info, user_message, user_id
            )
        except Exception as e:
            logger.error(f"Error en wrapper de herramientas: {e}")
            return []

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