"""
Agente de ventas inteligente que combina IA, técnicas de venta
y análisis de comportamiento para maximizar conversiones.
"""

import logging
import asyncio
import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from core.services.database import DatabaseService
from core.agents.agent_tools import AgentTools
from core.agents.conversation_processor import ConversationProcessor
from core.agents.intelligent_sales_agent import IntelligentSalesAgent
from core.utils.memory import GlobalMemory
from core.utils.lead_scorer import LeadScorer
from core.services.supabase_service import save_lead, get_course_detail, get_promotions
from core.utils.message_templates import MessageTemplates
from core.utils.sales_techniques import SalesTechniques
from config.settings import settings
from core.services.courseService import CourseService
from core.services.promptService import PromptService
from core.utils.lead_scorer import LeadScorer
from core.utils.memory import GlobalMemory, LeadMemory
from core.utils.message_templates import MessageTemplates
from core.utils.sales_techniques import SalesTechniques
from core.agents.conversation_processor import ConversationProcessor
from core.agents.intelligent_sales_agent import IntelligentSalesAgent

logger = logging.getLogger(__name__)

# Mapeo de códigos de curso a IDs
CURSOS_MAP = {
    "CURSO_IA_CHATGPT": "a392bf83-4908-4807-89a9-95d0acc807c9",  # ID correcto del curso
    "CURSO_PROMPTS": "2",
    "CURSO_IMAGENES": "3",
    "CURSO_AUTOMATIZACION": "4"
}

class SmartSalesAgent:
    """
    Agente de ventas inteligente que combina IA, técnicas de venta
    y análisis de comportamiento para maximizar conversiones.
    """
    
    def __init__(self, db: DatabaseService, agent: AgentTools):
        self.db = db
        self.agent = agent
        self.global_memory = GlobalMemory()
        self.lead_scorer = LeadScorer()
        self.templates = MessageTemplates()
        self.sales_techniques = SalesTechniques()
        
        # Servicios adicionales
        self.course_service = CourseService(db)
        self.prompt_service = PromptService(settings.OPENAI_API_KEY)
        
        # Inicializar el procesador de conversaciones con CourseService
        self.conversation_processor = ConversationProcessor(self.course_service)
        
        # Inicializar el agente inteligente con la API key
        try:
            self.intelligent_agent = IntelligentSalesAgent(settings.OPENAI_API_KEY, db)
        except Exception as e:
            logger.error(f"Error inicializando agente inteligente: {e}")
            self.intelligent_agent = None
        
        # Configuración de seguimiento
        self.follow_up_schedule = {
            'same_day': 4,  # 4 horas después
            'next_day': 24,  # 1 día después
            'week_reminder': 168,  # 1 semana después
            'course_start': None  # Se calcula dinámicamente
        }

    async def handle_conversation(self, message_data: dict, user_data: dict) -> Tuple[Union[str, List[Dict[str, Any]]], Optional[InlineKeyboardMarkup]]:
        """
        Maneja la conversación con el usuario y determina la mejor respuesta.
        
        Args:
            message_data: Datos del mensaje recibido
            user_data: Datos del usuario
            
        Returns:
            Respuesta generada y teclado opcional
        """
        try:
            # Extraer información básica
            user_id = str(user_data.get('id', message_data.get('from', {}).get('id', 'unknown')))
            message_text = message_data.get('text', '')
            
            # Obtener o crear memoria del usuario
            user_memory = self.global_memory.get_lead_memory(user_id)
            if not user_memory:
                user_memory = LeadMemory(user_id=user_id)
                self.global_memory.save_lead_memory(user_id, user_memory)
            
            # Actualizar datos básicos si están disponibles
            if 'username' in message_data.get('from', {}):
                user_memory.username = message_data['from']['username']
            if 'first_name' in message_data.get('from', {}):
                user_memory.first_name = message_data['from']['first_name']
            
            # **NUEVO: Detectar hashtags de anuncios PRIMERO**
            from core.utils.message_parser import extract_hashtags
            hashtags = extract_hashtags(message_text)
            has_course_hashtag = any(tag.startswith('curso:') or tag.startswith('CURSO_') for tag in hashtags)
            has_ad_hashtag = any(tag.startswith('anuncio:') or tag.startswith('ADSIM_') for tag in hashtags)
            
            if has_course_hashtag and has_ad_hashtag:
                # Usar el nuevo AdsFlowHandler si está disponible
                from core.handlers.ads_flow import AdsFlowHandler
                ads_handler = AdsFlowHandler(self.db, self.agent)
                course_hashtag = next((tag for tag in hashtags if tag.startswith('CURSO_') or tag.startswith('curso:')), None)
                campaign_hashtag = next((tag for tag in hashtags if tag.startswith('ADSIM_') or tag.startswith('anuncio:')), None)
                return await ads_handler.process_ad_message(message_data, user_data, course_hashtag, campaign_hashtag)
            
            # FLUJO: Si el usuario está en la etapa de 'awaiting_preferred_name', mostrar archivos y mensaje
            if user_memory.stage == "awaiting_preferred_name":
                return await self._handle_name_and_send_media(message_data, user_data, user_memory)
            
            # **MEJORADO: Usar el agente inteligente para conversaciones después de presentación inicial**
            if user_memory.stage in ["info_sent", "brenda_introduced", "course_presented"] or user_memory.interaction_count > 1:
                # Verificar si el agente inteligente está disponible
                if self.intelligent_agent is None:
                    logger.warning("Agente inteligente no disponible, usando respuesta por defecto")
                    return "Gracias por tu mensaje. Un asesor te contactará pronto.", None
                
                # Obtener información del curso
                course_info = None
                if user_memory.selected_course:
                    course_info = await self.course_service.getCourseDetails(user_memory.selected_course)
                
                # Buscar referencias a cursos en el mensaje si no hay curso seleccionado
                if not course_info:
                    try:
                        course_references = await self.prompt_service.extract_course_references(message_text)
                        if course_references:
                            for reference in course_references:
                                courses = await self.course_service.searchCourses(reference)
                                if courses:
                                    course_info = await self.course_service.getCourseDetails(courses[0]['id'])
                                    user_memory.selected_course = courses[0]['id']
                                    break
                    except Exception as e:
                        logger.warning(f"Error buscando referencias de curso: {e}")
                
                # Incrementar contador de interacciones
                user_memory.interaction_count += 1
                
                # Usar el agente inteligente para generar respuesta personalizada
                response = await self.intelligent_agent.generate_response(message_text, user_memory, course_info)
                
                # Guardar la memoria actualizada
                self.global_memory.save_lead_memory(user_id, user_memory)
                return response, None
            
            # Analizar el interés del usuario
            interest_analysis = await self._analyze_user_interest(message_text, user_memory)
            
            # Actualizar puntuación de lead
            self.lead_scorer.update_score(user_id, message_text, user_memory)
            
            # Determinar la mejor estrategia de respuesta
            strategy = await self._determine_sales_strategy(interest_analysis, user_memory)
            
            # Generar respuesta usando la estrategia seleccionada
            response, keyboard = await self._generate_strategic_response(
                strategy, message_text, user_memory, interest_analysis
            )
            
            # Programar seguimiento si es necesario
            await self._schedule_follow_up(user_id, strategy, user_memory)
            
            # Guardar la memoria actualizada
            self.global_memory.save_lead_memory(user_id, user_memory)
            
            return response, keyboard
            
        except Exception as e:
            logger.error(f"Error en handle_conversation: {e}", exc_info=True)
            return "Lo siento, ocurrió un error. Por favor intenta nuevamente.", None

    async def _handle_ad_flow(self, hashtag_match, message_data: dict, user_data: dict) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Maneja el flujo específico de usuarios que vienen de anuncios con hashtags.
        """
        try:
            user_id = str(user_data['id'])
            codigo_curso = hashtag_match.group(1)
            codigo_anuncio = hashtag_match.group(2)
            
            logger.info(f"Detectado flujo de anuncio: curso={codigo_curso}, anuncio={codigo_anuncio}")
            
            # Obtener ID del curso
            id_curso = CURSOS_MAP.get(codigo_curso)
            if not id_curso:
                logger.warning(f"Curso no encontrado en mapa: {codigo_curso}")
                return "¡Gracias por tu interés! En breve un asesor te contactará con más información.", None
            
            # Obtener información del curso
            curso_info = await self.course_service.getCourseDetails(id_curso)
            if not curso_info:
                logger.warning(f"Información del curso no encontrada: {id_curso}")
                return "No se encontró información del curso en la base de datos. Un asesor te contactará.", None
            
            # Crear/actualizar memoria del usuario
            user_memory = self.global_memory.create_lead_memory(user_id)
            user_memory.selected_course = id_curso
            user_memory.stage = "info"
            user_memory.ad_source = codigo_anuncio
            user_memory.first_name = user_data.get('first_name', 'Usuario')
            user_memory.name = user_data.get('first_name', 'Usuario')
            
            # Guardar en base de datos - ahora es async y no requiere email
            success = await save_lead(user_memory)
            if not success:
                logger.warning(f"No se pudo guardar el lead en la base de datos para usuario {user_id}")
            
            # Guardar en memoria local
            self.global_memory.save_lead_memory(user_id, user_memory)
            
            # Respuesta inicial
            saludo = f"Hola {user_memory.name} 😄 ¿cómo estás? Mi nombre es Brenda. Soy un sistema inteligente, parte del equipo de Aprende y Aplica IA. Recibí tu solicitud de información sobre el curso: *{curso_info['name']}*. ¡Con gusto te ayudo!"
            
            # Actualizar etapa para esperar el nombre preferido
            user_memory.stage = "awaiting_preferred_name"
            self.global_memory.save_lead_memory(user_id, user_memory)
            
            return saludo + "\n\nAntes de continuar, ¿cómo te gustaría que te llame?", None
            
        except Exception as e:
            logger.error(f"Error en _handle_ad_flow: {e}", exc_info=True)
            return "Ha ocurrido un error. Un asesor te contactará pronto.", None

    async def _handle_name_and_send_media(self, message_data: dict, user_data: dict, user_memory) -> Tuple[List[dict], Optional[InlineKeyboardMarkup]]:
        """
        Maneja la respuesta del nombre preferido y prepara los mensajes y archivos multimedia.
        """
        try:
            user_id = str(user_data['id'])
            nombre_preferido = message_data['text'].strip()
            # Procesar nombre preferido
            if len(nombre_preferido) > 1 and not any(x in nombre_preferido.lower() for x in ["no", "igual", "como quieras", "da igual", "me da igual"]):
                user_memory.name = nombre_preferido.title()
            else:
                user_memory.name = user_data.get('first_name', 'Usuario')
            # Obtener información del curso
            curso_info = await self.course_service.getCourseDetails(user_memory.selected_course)
            if not curso_info:
                return [
                    {"type": "text", "content": "No se encontró información del curso."}
                ], None
            # Actualizar etapa
            user_memory.stage = "info_sent"
            user_memory.media_sent = True  # Ya se enviarán los archivos
            self.global_memory.save_lead_memory(user_id, user_memory)
            # Mensaje de confirmación
            confirmation_message = f"¡Perfecto, {user_memory.name}! A partir de ahora me dirigiré a ti así. 😊"
            # Mensaje de aviso de envío de archivos
            aviso = "Te enviaré ahora toda la información del curso."
            # Mensaje detallado del curso
            detalles = f"""¡Excelente {user_memory.name}! 🌟 Aquí tienes todos los detalles del curso. Analicémoslos juntos:
\n📚 *Curso:* {curso_info.get('name', 'Curso de IA')}\n\n🎯 *Nivel:* {curso_info.get('level', 'Beginner')}\n🌐 *Modalidad:* {'Online en vivo' if curso_info.get('online') else 'Presencial'}\n⏱ *Duración:* {curso_info.get('total_duration', '12:00:00 horas')}\n📅 *Horario:* {curso_info.get('schedule', 'Viernes, 17:00 - 19:00 (CDMX)')}\n💰 *Inversión:* ${curso_info.get('price_usd', '120')} USD\n\n✨ *El curso incluye:*\n• Material didáctico digital\n• Acceso a grabaciones de las clases\n• Certificado al completar\n• Soporte personalizado\n• Proyectos prácticos\n\n🦾 *Beneficios:*\n• Clases en vivo con instructor experto\n• Grupos reducidos para atención personalizada\n• Ejercicios y casos reales\n• Comunidad de estudiantes\n\n¿Te gustaría conocer más detalles sobre algún aspecto en particular? ¡Estoy aquí para ayudarte! 😊"""
            # Secuencia de mensajes y archivos
            messages = [
                {"type": "text", "content": confirmation_message},
                {"type": "text", "content": aviso},
                {"type": "image", "path": "data/imagen_prueba.jpg"},
                {"type": "document", "path": "data/pdf_prueba.pdf"},
                {"type": "text", "content": detalles}
            ]
            return messages, None
        except Exception as e:
            logger.error(f"Error en _handle_name_and_send_media: {e}", exc_info=True)
            return [{"type": "text", "content": "Ha ocurrido un error. Un asesor te contactará pronto."}], None

    async def _send_course_media(self, message_data: dict, course_info: Dict) -> None:
        """
        Envía los archivos multimedia del curso (imagen y PDF).
        """
        try:
            chat_id = message_data.get('chat_id')
            if not chat_id:
                logger.error("Chat ID no disponible para enviar media")
                return
            
            # **IMPORTANTE: Necesitamos obtener el bot de la instancia de la aplicación**
            # Por ahora, vamos a logear que necesitamos enviar los archivos
            # y usar una aproximación diferente
            
            logger.info(f"Enviando archivos multimedia al chat {chat_id}")
            
            # **TEMPORAL: Marcar que los archivos necesitan ser enviados**
            # En el próximo mensaje del usuario, el bot principal debería manejar esto
            
            # Verificar archivos
            image_path = "data/imagen_prueba.jpg"
            pdf_path = "data/pdf_prueba.pdf"
            
            if os.path.exists(image_path):
                logger.info(f"Archivo de imagen encontrado: {image_path}")
            else:
                logger.warning("Archivo de imagen no encontrado")
            
            if os.path.exists(pdf_path):
                logger.info(f"Archivo PDF encontrado: {pdf_path}")
            else:
                logger.warning("Archivo PDF no encontrado")
                
            # **NOTA**: Los archivos se enviarán a través del bot principal
            # que tiene acceso directo al Application de Telegram
                
        except Exception as e:
            logger.error(f"Error enviando media del curso: {e}", exc_info=True)

    async def _analyze_user_interest(self, message: str, user_memory) -> Dict:
        """
        Analiza el nivel de interés del usuario basado en su mensaje y historial.
        """
        analysis = {
            'level': 'medium',  # low, medium, high, very_high
            'intent': 'information',  # information, objection, ready_to_buy, price_sensitive
            'urgency': 'normal',  # low, normal, high
            'decision_stage': 'consideration',  # awareness, consideration, decision
            'pain_points': [],
            'buying_signals': []
        }
        
        message_lower = message.lower()
        
        # Detectar señales de compra alta
        high_buying_signals = [
            'comprar', 'adquirir', 'inscribir', 'registrar', 'pagar',
            'cuando empieza', 'cómo pago', 'tarjeta', 'transferencia',
            'necesito', 'urgente', 'rápido', 'ya'
        ]
        
        # Detectar objeciones
        objection_signals = [
            'caro', 'costoso', 'dinero', 'presupuesto', 'pensar',
            'después', 'más tarde', 'tiempo', 'ocupado', 'difícil'
        ]
        
        # Detectar interés en información
        info_signals = [
            'temario', 'programa', 'contenido', 'aprendo', 'incluye',
            'certificado', 'profesor', 'instructor', 'modalidad'
        ]
        
        # Analizar nivel de interés
        if any(signal in message_lower for signal in high_buying_signals):
            analysis['level'] = 'very_high'
            analysis['intent'] = 'ready_to_buy'
            analysis['buying_signals'] = [s for s in high_buying_signals if s in message_lower]
            
        elif any(signal in message_lower for signal in objection_signals):
            analysis['level'] = 'low'
            analysis['intent'] = 'objection'
            
        elif any(signal in message_lower for signal in info_signals):
            analysis['level'] = 'high'
            analysis['intent'] = 'information'
        
        # Detectar urgencia
        urgency_signals = ['urgente', 'rápido', 'pronto', 'ya', 'inmediato']
        if any(signal in message_lower for signal in urgency_signals):
            analysis['urgency'] = 'high'
        
        # Determinar etapa de decisión basada en historial
        if user_memory.message_history:
            recent_messages = len(user_memory.message_history)
            if recent_messages > 5:
                analysis['decision_stage'] = 'decision'
            elif recent_messages > 2:
                analysis['decision_stage'] = 'consideration'
        
        return analysis

    async def _determine_sales_strategy(self, interest_analysis: Dict, user_memory) -> str:
        """
        Determina la mejor estrategia de ventas basada en el análisis de interés.
        """
        level = interest_analysis['level']
        intent = interest_analysis['intent']
        stage = interest_analysis['decision_stage']
        
        # Estrategias basadas en nivel de interés e intención
        if intent == 'ready_to_buy' and level == 'very_high':
            return 'close_immediate'
        
        elif intent == 'objection':
            return 'handle_objection'
        
        elif intent == 'information' and level == 'high':
            return 'provide_value_info'
        
        elif stage == 'decision' and level in ['high', 'very_high']:
            return 'urgency_close'
        
        elif level == 'medium' and stage == 'consideration':
            return 'build_value'
        
        elif level == 'low':
            return 'nurture_interest'
        
        else:
            return 'discover_needs'

    async def _generate_strategic_response(self, strategy: str, message: str, user_memory, analysis: Dict) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Genera una respuesta estratégica basada en la estrategia determinada.
        """
        user_name = user_memory.name or "amigo"
        
        if strategy == 'close_immediate':
            return await self._close_immediate_strategy(user_name, user_memory)
        
        elif strategy == 'handle_objection':
            return await self._handle_objection_strategy(message, user_name, analysis)
        
        elif strategy == 'provide_value_info':
            return await self._provide_value_info_strategy(message, user_name, user_memory)
        
        elif strategy == 'urgency_close':
            return await self._urgency_close_strategy(user_name, user_memory)
        
        elif strategy == 'build_value':
            return await self._build_value_strategy(user_name, user_memory)
        
        elif strategy == 'nurture_interest':
            return await self._nurture_interest_strategy(user_name, user_memory)
        
        else:  # discover_needs
            return await self._discover_needs_strategy(user_name, user_memory)

    async def _close_immediate_strategy(self, user_name: str, user_memory) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Estrategia para cerrar la venta inmediatamente cuando hay alta intención de compra.
        """
        message = self.templates.get_immediate_close_message(user_name)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Inscribirme ahora", callback_data="enroll_now")],
            [InlineKeyboardButton("💬 Hablar con asesor", callback_data="contact_advisor_urgent")],
            [InlineKeyboardButton("📋 Ver opciones de pago", callback_data="payment_options")]
        ])
        
        return message, keyboard

    async def _handle_objection_strategy(self, message: str, user_name: str, analysis: Dict) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Maneja objeciones del usuario con técnicas de ventas probadas.
        """
        objection_type = self.sales_techniques.identify_objection_type(message)
        response = self.sales_techniques.handle_objection(objection_type, user_name)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Ver promociones", callback_data="show_promotions")],
            [InlineKeyboardButton("📞 Hablar con asesor", callback_data="contact_advisor")],
            [InlineKeyboardButton("🎯 Casos de éxito", callback_data="success_stories")]
        ])
        
        return response, keyboard

    async def _provide_value_info_strategy(self, message: str, user_name: str, user_memory) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Proporciona información valiosa cuando el usuario muestra alto interés informativo.
        """
        info_type = self._identify_info_request(message)
        response = await self._get_detailed_info(info_type, user_name, user_memory)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 Temario completo", callback_data="full_curriculum")],
            [InlineKeyboardButton("👨‍🏫 Conocer instructor", callback_data="instructor_info")],
            [InlineKeyboardButton("🎓 Certificación", callback_data="certification_info")],
            [InlineKeyboardButton("💼 Salidas laborales", callback_data="career_opportunities")]
        ])
        
        return response, keyboard

    async def _urgency_close_strategy(self, user_name: str, user_memory) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Crea urgencia para cerrar la venta cuando el usuario está en etapa de decisión.
        """
        # Verificar si hay promociones activas
        promotions = await get_promotions()
        
        if promotions:
            message = self.templates.get_urgency_with_promotion_message(user_name, promotions[0])
        else:
            message = self.templates.get_urgency_close_message(user_name)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 ¡Inscribirme ahora!", callback_data="enroll_urgent")],
            [InlineKeyboardButton("⏰ Reservar mi lugar", callback_data="reserve_spot")],
            [InlineKeyboardButton("📞 Llamar ahora", callback_data="urgent_call")]
        ])
        
        return message, keyboard

    async def _build_value_strategy(self, user_name: str, user_memory) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Construye valor cuando el usuario está en consideración con interés medio.
        """
        message = self.templates.get_value_building_message(user_name)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💡 Beneficios únicos", callback_data="unique_benefits")],
            [InlineKeyboardButton("📈 ROI del curso", callback_data="course_roi")],
            [InlineKeyboardButton("🏆 Casos de éxito", callback_data="success_stories")],
            [InlineKeyboardButton("🎁 Bonos incluidos", callback_data="course_bonuses")]
        ])
        
        return message, keyboard

    async def _nurture_interest_strategy(self, user_name: str, user_memory) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Nutre el interés cuando el nivel es bajo, construyendo confianza gradualmente.
        """
        message = self.templates.get_nurture_message(user_name)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 ¿Es para mí?", callback_data="course_fit_quiz")],
            [InlineKeyboardButton("📖 Contenido gratuito", callback_data="free_content")],
            [InlineKeyboardButton("👥 Comunidad", callback_data="community_info")],
            [InlineKeyboardButton("❓ Preguntas frecuentes", callback_data="faq")]
        ])
        
        return message, keyboard

    async def _discover_needs_strategy(self, user_name: str, user_memory) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Descubre las necesidades del usuario para personalizar la experiencia.
        """
        message = self.templates.get_needs_discovery_message(user_name)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💼 Profesional", callback_data="profile_professional")],
            [InlineKeyboardButton("🎓 Estudiante", callback_data="profile_student")],
            [InlineKeyboardButton("🚀 Emprendedor", callback_data="profile_entrepreneur")],
            [InlineKeyboardButton("💡 Curioso", callback_data="profile_curious")]
        ])
        
        return message, keyboard

    def _identify_info_request(self, message: str) -> str:
        """
        Identifica qué tipo de información solicita el usuario.
        """
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['temario', 'programa', 'contenido', 'módulos']):
            return 'curriculum'
        elif any(word in message_lower for word in ['instructor', 'profesor', 'maestro']):
            return 'instructor'
        elif any(word in message_lower for word in ['certificado', 'diploma', 'certificación']):
            return 'certification'
        elif any(word in message_lower for word in ['horario', 'tiempo', 'duración']):
            return 'schedule'
        elif any(word in message_lower for word in ['precio', 'costo', 'pago']):
            return 'pricing'
        else:
            return 'general'

    async def _get_detailed_info(self, info_type: str, user_name: str, user_memory) -> str:
        """
        Obtiene información detallada según el tipo solicitado.
        """
        course_name = user_memory.selected_course
        
        if info_type == 'curriculum':
            return self.templates.get_curriculum_info_message(user_name, course_name)
        elif info_type == 'instructor':
            return self.templates.get_instructor_info_message(user_name)
        elif info_type == 'certification':
            return self.templates.get_certification_info_message(user_name)
        elif info_type == 'schedule':
            return f"Hola {user_name}, el horario del curso es flexible y se adapta a diferentes zonas horarias. Te contactaré con más detalles específicos."
        elif info_type == 'pricing':
            return self.templates.get_pricing_info_message(user_name)
        else:
            return self.templates.get_general_info_message(user_name, course_name)

    async def _schedule_follow_up(self, user_id: str, strategy: str, user_memory):
        """
        Programa seguimiento automático basado en la estrategia y comportamiento del usuario.
        """
        try:
            # No programar seguimiento para cierres inmediatos exitosos
            if strategy == 'close_immediate':
                return
            
            # Determinar tipo de seguimiento
            follow_up_type = self._determine_follow_up_type(strategy, user_memory)
            
            if follow_up_type:
                # Aquí implementarías la lógica de programación
                # Por ejemplo, usando Celery, APScheduler, o similar
                logger.info(f"Programando seguimiento {follow_up_type} para usuario {user_id}")
                
        except Exception as e:
            logger.error(f"Error programando seguimiento: {e}")

    def _determine_follow_up_type(self, strategy: str, user_memory) -> Optional[str]:
        """
        Determina qué tipo de seguimiento programar.
        """
        if strategy in ['handle_objection', 'nurture_interest']:
            return 'gentle_reminder'
        elif strategy in ['build_value', 'urgency_close']:
            return 'value_reinforcement'
        elif strategy == 'discover_needs':
            return 'needs_follow_up'
        else:
            return None 