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
- enviar_recursos_gratuitos: Guías y templates de valor (PDFs, templates)
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
- Si necesita convencerse del valor → enviar_recursos_gratuitos
- Si pide recursos gratuitos o guías → enviar_recursos_gratuitos

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
- EDUCACIÓN: Comparte valor + enviar_recursos_gratuitos
- RECURSOS_GRATUITOS: Solicitud directa de recursos + enviar_recursos_gratuitos
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
        
        # Procesador conversacional inteligente
        self.conversation_processor = IntelligentConversationProcessor(
            self.client, db, self.course_service
        )
        
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
            9. FREE_RESOURCES - Solicitud de recursos gratuitos, guías, templates, prompts
            10. GENERAL_QUESTION - Pregunta general sobre IA/tecnología

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
            
            logger.info(f"🔍 _get_course_info_from_db iniciado para curso: {course_id}")
            
            # Usar CourseService para obtener información básica primero
            course_info = await self.course_service.getCourseBasicInfo(course_id)
            if not course_info:
                logger.warning(f"No se encontró información básica del curso {course_id}")
                return None
                
            logger.info(f"✅ Información básica obtenida: {course_info.get('name', 'Sin nombre')}")
                
            # Obtener información detallada si la básica existe
            course_details = await self.course_service.getCourseDetails(course_id)
            if course_details:
                # Combinar información básica con detalles
                course_info.update(course_details)
                logger.info(f"✅ Detalles del curso combinados")
                
                # Obtener módulos/sesiones por separado para asegurar compatibilidad
                modules_sessions = await self.course_service.getCourseModules(course_id)
                logger.info(f"📋 getCourseModules retornó {len(modules_sessions) if modules_sessions else 0} elementos")
                
                if modules_sessions:
                    # Detectar estructura basado en los campos presentes
                    first_item = modules_sessions[0] if modules_sessions else {}
                    logger.info(f"🔍 Primer elemento para detectar estructura: {first_item}")
                    
                    # Si tiene 'name' y 'description' -> estructura antigua (modules)
                    # Si tiene 'title' y 'objective' -> nueva estructura (sessions)
                    if 'name' in first_item and 'description' in first_item:
                        # Estructura actual: modules
                        course_info['modules'] = modules_sessions
                        logger.info(f"✅ Detectada estructura ANTIGUA - {len(modules_sessions)} módulos agregados a course_info")
                        logger.info(f"📖 Nombres de módulos: {[m.get('name') for m in modules_sessions]}")
                    elif 'title' in first_item and 'objective' in first_item:
                        # Nueva estructura: sessions - mapear a format compatible
                        sessions_mapped = []
                        for session in modules_sessions:
                            mapped_session = {
                                'id': session.get('id'),
                                'name': session.get('name'),  # Ya mapeado en CourseService
                                'description': session.get('description'),  # Ya mapeado en CourseService
                                'duration': session.get('duration'),
                                'module_index': session.get('module_index'),
                                # Mantener también los campos originales para compatibilidad
                                'title': session.get('name'),
                                'objective': session.get('description'),
                                'duration_minutes': session.get('duration'),
                                'session_index': session.get('module_index')
                            }
                            sessions_mapped.append(mapped_session)
                        
                        # Agregar tanto como 'sessions' (nueva) como 'modules' (compatibilidad)
                        course_info['sessions'] = sessions_mapped
                        course_info['modules'] = sessions_mapped  # Para compatibilidad con validación
                        logger.info(f"✅ Detectada estructura NUEVA - {len(sessions_mapped)} sesiones mapeadas")
                        logger.info(f"📖 Nombres de sesiones: {[s.get('name') for s in sessions_mapped]}")
                        logger.info(f"🔗 course_info ahora tiene 'modules' y 'sessions' para compatibilidad")
                        
                        # Calcular duración total en minutos
                        total_duration = sum(session.get('duration', 0) for session in sessions_mapped)
                        course_info['total_duration_min'] = total_duration
                        
                        # Obtener prácticas por sesión (solo nueva estructura)
                        for session in sessions_mapped:
                            session_id = session.get('id')
                            if session_id:
                                practices = await self.course_service.getModuleExercises(session_id)
                                if practices:
                                    session['practices'] = practices
                        
                        # Obtener entregables por sesión (solo nueva estructura)
                        for session in sessions_mapped:
                            session_id = session.get('id')
                            if session_id:
                                deliverables = await self.course_service.getSessionDeliverables(session_id)
                                if deliverables:
                                    session['deliverables'] = deliverables
                    else:
                        logger.warning(f"⚠️ No se pudo detectar estructura de módulos/sesiones para curso {course_id}")
                        course_info['modules'] = modules_sessions  # Fallback
                else:
                    logger.warning(f"❌ NO se obtuvieron módulos/sesiones de getCourseModules para curso {course_id}")
                
                # Obtener bonos disponibles (funciona en ambas estructuras)
                bonuses = await self.course_service.getAvailableBonuses(course_id)
                if bonuses:
                    course_info['bonuses'] = bonuses
                    
                # Obtener subtema del curso (solo nueva estructura)
                subtheme = await self.course_service.getCourseSubtheme(course_id)
                if subtheme:
                    course_info['subtheme'] = subtheme
                    
                # Obtener recursos gratuitos (funciona en ambas estructuras)
                free_resources = await self.course_service.getFreeResources(course_id)
                if free_resources:
                    course_info['free_resources'] = free_resources
            
            # LOG FINAL del course_info que se va a retornar
            logger.info(f"📊 COURSE_INFO FINAL para validación:")
            logger.info(f"🗂️ Keys en course_info: {list(course_info.keys())}")
            logger.info(f"📚 Módulos en course_info: {len(course_info.get('modules', []))}")
            logger.info(f"📚 Sesiones en course_info: {len(course_info.get('sessions', []))}")
            
            return course_info
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo información del curso {course_id}: {e}")
            return None
    
    async def _validate_course_content_mention(self, response_text: str, course_info: Dict) -> bool:
        """Valida que no se mencione contenido inventado del curso."""
        try:
            if not course_info:
                logger.warning("🚫 No hay course_info para validar")
                return True
                
            # Lista de palabras que indican contenido específico del curso
            content_indicators = [
                'módulo', 'módulos', 'capítulo', 'capítulos', 'lección', 'lecciones',
                'temario', 'contenido', 'syllabus', 'programa', 'plan de estudios',
                'sesión', 'sesiones', 'práctica', 'prácticas', 'entregable', 'entregables'
            ]
            
            response_lower = response_text.lower()
            mentions_content = any(indicator in response_lower for indicator in content_indicators)
            
            # 🔍 LOGGING DETALLADO PARA DEBUG
            logger.info(f"🔍 VALIDANDO RESPUESTA:")
            logger.info(f"📝 Respuesta generada: {response_text}")
            logger.info(f"🎯 Menciona contenido específico: {mentions_content}")
            
            if not mentions_content:
                logger.info("✅ Respuesta NO menciona contenido específico - APROBADA")
                return True  # No menciona contenido específico, está bien
                
            # Verificar si tenemos módulos/sesiones reales (estructura híbrida)
            real_modules = course_info.get('modules', [])
            real_sessions = course_info.get('sessions', [])
            
            logger.info(f"🗂️ Módulos en course_info: {len(real_modules)} - {[m.get('name', 'Sin nombre') for m in real_modules[:3]]}")
            logger.info(f"🗂️ Sesiones en course_info: {len(real_sessions)} - {[s.get('title', s.get('name', 'Sin nombre')) for s in real_sessions[:3]]}")
            
            # Si tenemos cualquiera de las dos estructuras, validar
            if real_modules:
                # Estructura actual - validar módulos
                logger.info(f"📚 Validando contra {len(real_modules)} módulos reales")
                for i, module in enumerate(real_modules[:3]):  # Solo primeros 3 para logging
                    logger.info(f"📖 Módulo {i+1}: {module}")
                    if not all(key in module for key in ['name', 'description']):
                        logger.warning(f"❌ Módulo {module.get('id')} no tiene toda la información requerida")
                        return False
                logger.info(f"✅ Validación exitosa: curso tiene {len(real_modules)} módulos reales")
                return True
                
            elif real_sessions:
                # Nueva estructura - validar sesiones
                logger.info(f"📚 Validando contra {len(real_sessions)} sesiones reales")
                for i, session in enumerate(real_sessions[:3]):  # Solo primeros 3 para logging
                    logger.info(f"📖 Sesión {i+1}: {session}")
                    if not all(key in session for key in ['title', 'objective', 'duration_minutes']):
                        logger.warning(f"❌ Sesión {session.get('id')} no tiene toda la información requerida")
                        return False
                        
                # Si menciona prácticas, verificar que existan
                if 'práctica' in response_lower or 'prácticas' in response_lower:
                    has_practices = any(
                        session.get('practices', []) 
                        for session in real_sessions
                    )
                    if not has_practices:
                        logger.warning("❌ Respuesta menciona prácticas pero no hay prácticas en BD")
                        return False
                        
                # Si menciona entregables, verificar que existan
                if 'entregable' in response_lower or 'entregables' in response_lower:
                    has_deliverables = any(
                        session.get('deliverables', []) 
                        for session in real_sessions
                    )
                    if not has_deliverables:
                        logger.warning("❌ Respuesta menciona entregables pero no hay entregables en BD")
                        return False
                        
                logger.info(f"✅ Validación exitosa: curso tiene {len(real_sessions)} sesiones reales")
                return True
            else:
                # No hay módulos ni sesiones - permitir solo si es información general
                logger.warning(f"❌ NO HAY módulos ni sesiones en course_info")
                logger.warning(f"🔍 Keys disponibles en course_info: {list(course_info.keys())}")
                if any(word in response_lower for word in ['módulo', 'módulos', 'lección', 'lecciones', 'temario', 'syllabus']):
                    logger.warning("❌ Respuesta menciona contenido específico pero no hay módulos/sesiones reales en BD")
                    return False
                return True
                
        except Exception as e:
            logger.error(f"❌ Error validando contenido del curso: {e}")
            return True  # En caso de error, permitir la respuesta

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
            response_focus = conversation_analysis.get("next_conversation_focus", "general")
            suggested_tools = conversation_analysis.get("suggested_tools", [])
            
            # Mapear herramientas según el análisis inteligente
            if "free_resources" in suggested_tools or "FREE_RESOURCES" in conversation_analysis.get("user_profile", {}).get("intent_category", ""):
                tools_to_use.append("enviar_recursos_gratuitos")
            
            if "syllabus" in suggested_tools or any(word in user_message.lower() for word in ["temario", "contenido", "que voy a aprender"]):
                tools_to_use.append("mostrar_syllabus_interactivo")
            
            if "price_comparison" in suggested_tools or conversation_analysis.get("user_profile", {}).get("intent_category") == "OBJECTION_PRICE":
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
            engagement_level = conversation_analysis.get("user_profile", {}).get("engagement_level", "medium")
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
- Herramientas usadas: {', '.join(str(t) for t in (course_info.get('tools_used') or ['No disponible']))}
- Prerrequisitos: {', '.join(str(p) for p in (course_info.get('prerequisites') or ['No disponible']))}
- Requerimientos: {', '.join(str(r) for r in (course_info.get('requirements') or ['No disponible']))}
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
                # Validar respuesta para prevenir contenido inventado
                is_valid = await self._validate_course_content_mention(response_text, course_info)
                
                if not is_valid:
                    logger.warning(f"❌ RESPUESTA DE LA IA RECHAZADA POR CONTENIDO INVENTADO:")
                    logger.warning(f"📝 Respuesta completa: {response_text}")
                    logger.warning(f"🎯 Curso ID: {user_memory.selected_course}")
                    logger.warning(f"📚 Course_info keys: {list(course_info.keys()) if course_info else 'None'}")
                    logger.warning(f"Respuesta menciona contenido inventado para curso {user_memory.selected_course}")
                    
                    # Usar respuesta genérica en lugar de contenido potencialmente inventado
                    response_text = "Perfecto, me da mucho gusto que estés interesado en el curso. Déjame consultar la información específica del contenido para darte detalles precisos. ¿Hay algo particular que te gustaría saber sobre el curso?"
                else:
                    logger.info(f"✅ RESPUESTA DE LA IA APROBADA:")
                    logger.info(f"📝 Respuesta: {response_text[:200]}...")  # Solo primeros 200 caracteres
                
                # Validar respuesta con datos COMPLETOS de BD (incluir TODO)
                bonuses = course_info.get('bonuses', [])
                if not bonuses:
                    bonuses = await self.course_service.getAvailableBonuses(course_info['id'])
                
                # Obtener recursos gratuitos para el validador
                free_resources = course_info.get('free_resources', [])
                if not free_resources:
                    free_resources = await self.course_service.getFreeResources(course_info['id'])
                
                # Enriquecer course_data con TODA la información disponible
                complete_course_data = course_info.copy()
                complete_course_data['bonuses'] = bonuses
                complete_course_data['free_resources'] = free_resources
                
                # Agregar información de la base de datos para el validador
                logger.info(f"🔍 Enviando al validador course_data con {len(complete_course_data.keys())} claves")
                logger.info(f"📊 Keys disponibles: {list(complete_course_data.keys())}")
                
                # Validar respuesta incluyendo TODOS los datos disponibles
                validation = await self.prompt_service.validate_response(
                    response=response_text,
                    course_data=complete_course_data,
                    bonuses_data=bonuses,
                    all_courses_data=None  # Se puede expandir para incluir otros cursos si es necesario
                )
                
                logger.info(f"🔍 Validador ejecutado - Resultado: {validation.get('is_valid', True)}")
                if validation.get('warnings'):
                    logger.info(f"⚠️ Warnings del validador: {validation.get('warnings')}")
                if validation.get('errors'):
                    logger.warning(f"❌ Errores del validador: {validation.get('errors')}")
                
                if not validation.get('is_valid', True):
                    errors = validation.get('errors', [])
                    logger.warning(f"Respuesta inválida para usuario {user_memory.user_id}: {', '.join(errors)}")
                    
                    # Si la respuesta es inválida, devolver respuesta segura
                    return "Te entiendo perfectamente. Déjame obtener la información más actualizada sobre el curso para responderte con precisión. ¿Qué aspecto específico te interesa más?"
            
            # REDISEÑADO: Activar herramientas ANTES de procesar la respuesta para incorporar contenido
            tool_contents = await self._activate_tools_based_on_intent(
                intent_analysis, user_memory, course_info, user_message
            )
            
            # Procesar contenido de herramientas
            tools_content_text = ""
            if tool_contents:
                from core.agents.intelligent_sales_agent_tools import IntelligentSalesAgentTools
                tools_handler = IntelligentSalesAgentTools(self.agent_tools)
                tools_content_text = tools_handler.format_tool_content_for_agent(tool_contents)
                
                # Si se activó contacto con asesor, retornar directamente
                if any(content.get('type') == 'contact_flow_activated' for content in tool_contents):
                    logger.info(f"🔄 Flujo de contacto activado, agente se desactiva temporalmente")
                    return tools_content_text
                
                # NUEVO: Si se activaron herramientas específicas que deben reemplazar la respuesta de GPT
                tools_that_replace_response = ['mostrar_bonos_exclusivos', 'enviar_recursos_gratuitos', 
                                              'mostrar_syllabus_interactivo', 'enviar_preview_curso']
                
                # Verificar si alguna herramienta de reemplazo se activó revisando el tipo de contenido
                replace_gpt_response = False
                detected_keywords = [
                    'bonos exclusivos', 'bonos incluidos', 'plantilla de calendario', 'valor total de bonos',
                    'recursos gratuitos', 'syllabus', 'preview', 'temario completo'
                ]
                
                for content in tool_contents:
                    if content.get('type') == 'text':
                        content_text = content.get('content', '').lower()
                        for keyword in detected_keywords:
                            if keyword in content_text:
                                replace_gpt_response = True
                                logger.info(f"🔧 Detectado contenido de herramienta específica: '{keyword}' - activando reemplazo")
                                break
                        if replace_gpt_response:
                            break
                
                if replace_gpt_response:
                    logger.info(f"🔄 Herramientas de contenido específico activadas - usando solo contenido de herramientas")
                    # Usar SOLO el contenido crudo de las herramientas, sin headers ni respuesta de GPT
                    raw_tools_content = tools_handler.extract_raw_tool_content(tool_contents)
                    
                    if raw_tools_content and raw_tools_content.strip():
                        final_response = await self._process_response_with_tools(raw_tools_content, user_memory, tool_contents)
                        return final_response
                    else:
                        logger.warning(f"⚠️ Contenido de herramientas vacío, usando respuesta de GPT como fallback")
                        # Fallback: usar respuesta de GPT si las herramientas no tienen contenido
                
                logger.info(f"✅ Contenido de herramientas procesado para incorporar en respuesta")
            
            # Incorporar contenido de herramientas en la respuesta del agente si existe
            if tools_content_text:
                # Combinar la respuesta del agente con el contenido de las herramientas
                combined_response = response_text + "\n\n" + tools_content_text
                final_response = await self._process_response_with_tools(combined_response, user_memory, tool_contents)
            else:
                # Procesar respuesta normal sin herramientas
                final_response = await self._process_response(response_text, user_memory)
            
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

    async def _process_response_with_tools(self, combined_response: str, user_memory: LeadMemory, tool_contents: List[Dict[str, Any]]) -> Union[str, List[Dict[str, str]]]:
        """
        NUEVO: Procesa la respuesta combinada del agente + herramientas para generar multimedia.
        Convierte el contenido de herramientas en formato multimedia para el bot principal.
        """
        
        # Actualizar historial con solo la parte del agente (sin contenido de herramientas)
        agent_response = combined_response.split("\n\n## CONTENIDO DE HERRAMIENTAS ACTIVADAS:")[0]
        
        if user_memory.message_history is None:
            user_memory.message_history = []
        
        user_memory.message_history.append({
            'role': 'assistant',
            'content': agent_response,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Limitar historial
        if len(user_memory.message_history) > 20:
            user_memory.message_history = user_memory.message_history[-20:]
        
        # Actualizar timestamps
        user_memory.last_interaction = datetime.utcnow()
        user_memory.updated_at = datetime.utcnow()
        
        # Construir respuesta multimedia con recursos
        multimedia_response = []
        
        # Agregar mensaje del agente
        multimedia_response.append({
            'type': 'text',
            'content': agent_response
        })
        
        # Procesar contenido de herramientas para agregar recursos
        for content in tool_contents:
            content_type = content.get('type', 'text')
            
            if content_type == 'multimedia':
                # Agregar recursos de herramientas multimedia
                resources = content.get('resources', [])
                for resource in resources:
                    if resource.get('type') == 'document' and resource.get('url'):
                        multimedia_response.append({
                            'type': 'document',
                            'url': resource['url'],
                            'caption': resource.get('caption', 'Documento')
                        })
                    elif resource.get('type') == 'video' and resource.get('url'):
                        multimedia_response.append({
                            'type': 'video',
                            'url': resource['url'],
                            'caption': resource.get('caption', 'Video')
                        })
                    elif resource.get('type') == 'link' and resource.get('url'):
                        # Los links se incluyen en el texto del agente
                        pass
        
        # Si hay recursos multimedia, retornar lista; sino, solo texto
        if len(multimedia_response) > 1:
            return multimedia_response
        else:
            return agent_response
    
    async def _activate_tools_based_on_intent(
        self, 
        intent_analysis: Dict, 
        user_memory, 
        course_info: Optional[Dict],
        user_message: str
    ) -> List[Dict[str, Any]]:
        """REDISEÑADO: Wrapper para activar herramientas - retorna contenido en lugar de nombres"""
        try:
            # Verificar que agent_tools esté disponible
            if not self.agent_tools:
                logger.warning("Agent tools no está disponible. Las herramientas no se activarán.")
                return []
                
            from core.agents.intelligent_sales_agent_tools import IntelligentSalesAgentTools
            tools_handler = IntelligentSalesAgentTools(self.agent_tools)
            
            user_id = user_memory.user_id
            tool_contents = await tools_handler._activate_tools_based_on_intent(
                intent_analysis, user_memory, course_info, user_message, user_id
            )
            
            return tool_contents
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