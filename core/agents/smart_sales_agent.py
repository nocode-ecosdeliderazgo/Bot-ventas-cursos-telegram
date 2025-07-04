"""
Agente de ventas inteligente que utiliza técnicas avanzadas de conversión,
análisis de interés del usuario y seguimiento automatizado.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from core.services.database import DatabaseService
from core.agents.sales_agent import AgenteSalesTools
from core.utils.memory import GlobalMemory
from core.utils.lead_scorer import LeadScorer
from core.services.supabase_service import save_lead, get_course_detail, get_promotions
from core.utils.message_templates import MessageTemplates
from core.utils.sales_techniques import SalesTechniques

logger = logging.getLogger(__name__)

class SmartSalesAgent:
    """
    Agente de ventas inteligente que combina IA, técnicas de venta
    y análisis de comportamiento para maximizar conversiones.
    """
    
    def __init__(self, db: DatabaseService, agent: AgenteSalesTools):
        self.db = db
        self.agent = agent
        self.global_memory = GlobalMemory()
        self.lead_scorer = LeadScorer()
        self.templates = MessageTemplates()
        self.sales_techniques = SalesTechniques()
        
        # Configuración de seguimiento
        self.follow_up_schedule = {
            'same_day': 4,  # 4 horas después
            'next_day': 24,  # 1 día después
            'week_reminder': 168,  # 1 semana después
            'course_start': None  # Se calcula dinámicamente
        }

    async def handle_conversation(self, message_data: dict, user_data: dict) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Punto de entrada principal para la conversación de ventas.
        """
        try:
            user_id = str(user_data['id'])
            message_text = message_data['text']
            
            # Obtener memoria del usuario
            user_memory = self.global_memory.get_lead_memory(user_id)
            
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
            
            # Actualizar memoria
            user_memory.last_interaction = datetime.now()
            user_memory.message_history.append({
                'timestamp': datetime.now().isoformat(),
                'message': message_text,
                'strategy_used': strategy,
                'interest_level': interest_analysis['level']
            })
            self.global_memory.save_lead_memory(user_id, user_memory)
            
            return response, keyboard
            
        except Exception as e:
            logger.error(f"Error en handle_conversation: {e}", exc_info=True)
            return self.templates.get_error_message(), None

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

    async def _generate_strategic_response(self, strategy: str, message: str, user_memory, analysis: Dict) -> Tuple[str, InlineKeyboardMarkup]:
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

    async def _close_immediate_strategy(self, user_name: str, user_memory) -> Tuple[str, InlineKeyboardMarkup]:
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

    async def _handle_objection_strategy(self, message: str, user_name: str, analysis: Dict) -> Tuple[str, InlineKeyboardMarkup]:
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

    async def _provide_value_info_strategy(self, message: str, user_name: str, user_memory) -> Tuple[str, InlineKeyboardMarkup]:
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

    async def _urgency_close_strategy(self, user_name: str, user_memory) -> Tuple[str, InlineKeyboardMarkup]:
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

    async def _build_value_strategy(self, user_name: str, user_memory) -> Tuple[str, InlineKeyboardMarkup]:
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

    async def _nurture_interest_strategy(self, user_name: str, user_memory) -> Tuple[str, InlineKeyboardMarkup]:
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

    async def _discover_needs_strategy(self, user_name: str, user_memory) -> Tuple[str, InlineKeyboardMarkup]:
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
            return self.templates.get_schedule_info_message(user_name)
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