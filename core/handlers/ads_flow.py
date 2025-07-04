"""
Manejo del flujo de anuncios con enfoque en conversión y experiencia del usuario.
Incluye aviso de privacidad, captura de datos y presentación del curso.
"""

import logging
import os
from typing import Dict, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.services.database import DatabaseService
from core.agents.sales_agent import AgenteSalesTools
from core.agents.smart_sales_agent import SmartSalesAgent
from core.utils.memory import GlobalMemory
from core.utils.lead_scorer import LeadScorer
from core.services.supabase_service import save_lead, get_course_by_name
from core.utils.message_templates import MessageTemplates

logger = logging.getLogger(__name__)

class AdsFlowHandler:
    """
    Maneja el flujo completo de usuarios que llegan desde anuncios.
    """
    
    def __init__(self, db: DatabaseService, agent: AgenteSalesTools) -> None:
        """
        Inicializa el manejador de flujo de anuncios.

        Args:
            db: Servicio de base de datos
            agent: Herramientas del agente de ventas
        """
        self.db = db
        self.agent = agent
        self.smart_agent = SmartSalesAgent(db, agent)
        self.global_memory = GlobalMemory()
        self.lead_scorer = LeadScorer()
        self.templates = MessageTemplates()
        
    async def handle_ad_message(
        self, 
        message_data: Dict, 
        user_data: Dict
    ) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Punto de entrada principal para mensajes desde anuncios.

        Args:
            message_data: Datos del mensaje recibido
            user_data: Datos del usuario

        Returns:
            Tupla con el mensaje de respuesta y el teclado inline opcional
        """
        try:
            user_id = str(user_data['id'])
            message_text = message_data['text']
            
            user_memory = self.global_memory.get_lead_memory(user_id)
            
            if not user_memory.has_accepted_privacy:
                return await self._handle_first_interaction(user_data, message_text)
            
            if not user_memory.name:
                return await self._handle_name_request(user_data, message_text)
            
            if not user_memory.course_presented:
                return await self._present_course_content(user_data, message_text)
            
            return await self.smart_agent.handle_conversation(message_data, user_data)
            
        except Exception as e:
            logger.error(f"Error en handle_ad_message: {e}", exc_info=True)
            return self.templates.get_error_message(), None

    async def _handle_first_interaction(
        self, 
        user_data: Dict, 
        message_text: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Maneja la primera interacción mostrando el aviso de privacidad.

        Args:
            user_data: Datos del usuario
            message_text: Texto del mensaje recibido

        Returns:
            Tupla con mensaje de bienvenida y teclado de privacidad
        """
        user_id = str(user_data['id'])
        
        user_memory = self.global_memory.create_lead_memory(user_id)
        user_memory.first_name = user_data.get('first_name', '')
        user_memory.username = user_data.get('username', '')
        user_memory.ad_source = self._extract_ad_source(message_text)
        
        welcome_message = self.templates.get_privacy_notice_message(
            user_data.get('first_name', 'amigo')
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Acepto", callback_data=f"privacy_accept_{user_id}")],
            [InlineKeyboardButton("❌ No acepto", callback_data=f"privacy_decline_{user_id}")]
        ])
        
        return welcome_message, keyboard

    async def _handle_name_request(
        self, 
        user_data: Dict, 
        message_text: str
    ) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Solicita y procesa el nombre del usuario.

        Args:
            user_data: Datos del usuario
            message_text: Texto del mensaje recibido

        Returns:
            Tupla con mensaje de respuesta y teclado opcional
        """
        user_id = str(user_data['id'])
        user_memory = self.global_memory.get_lead_memory(user_id)
        
        if len(message_text.strip()) > 2 and not any(char in message_text for char in '#@[]{}'):
            user_memory.name = message_text.strip().title()
            user_memory.stage = "name_collected"
            self.global_memory.save_lead_memory(user_id, user_memory)
            
            return await self._present_course_content(user_data, message_text)
        
        name_message = self.templates.get_name_request_message(
            user_data.get('first_name', '')
        )
        return name_message, None

    async def _present_course_content(
        self, 
        user_data: Dict, 
        message_text: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Presenta el contenido del curso con detalles e interacciones.

        Args:
            user_data: Datos del usuario
            message_text: Texto del mensaje recibido

        Returns:
            Tupla con mensaje de presentación y teclado de opciones
        """
        user_id = str(user_data['id'])
        user_memory = self.global_memory.get_lead_memory(user_id)
        
        course_info = await self._extract_course_info(message_text) or {
            'name': 'Curso de Inteligencia Artificial con ChatGPT',
            'description': 'Aprende a dominar la IA para potenciar tu carrera profesional',
            'price': 120,
            'duration': '12 horas',
            'modality': 'Online',
            'schedule': 'Viernes 17:00-19:00 (CDMX)'
        }
        
        user_memory.course_presented = True
        user_memory.selected_course = course_info['name']
        user_memory.stage = "course_presented"
        self.global_memory.save_lead_memory(user_id, user_memory)
        
        presentation_message = self.templates.get_course_presentation_message(
            user_memory.name or user_data.get('first_name', 'amigo'),
            course_info
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📋 Ver temario completo", 
                callback_data=f"show_curriculum_{user_id}"
            )],
            [InlineKeyboardButton(
                "💬 Hablar con asesor", 
                callback_data=f"contact_advisor_{user_id}"
            )],
            [InlineKeyboardButton(
                "🎯 ¿Por qué este curso?", 
                callback_data=f"why_course_{user_id}"
            )],
            [InlineKeyboardButton(
                "💰 Opciones de pago", 
                callback_data=f"payment_options_{user_id}"
            )]
        ])
        
        return presentation_message, keyboard

    async def send_course_media(self, update: Update, course_info: Dict) -> None:
        """
        Envía la imagen y PDF del curso.

        Args:
            update: Objeto Update de Telegram
            course_info: Información del curso
        """
        try:
            if not update.effective_chat:
                logger.error("Chat no disponible para enviar media")
                return

            image_path = "data/imagen_prueba.jpg"
            if os.path.exists(image_path):
                with open(image_path, 'rb') as photo:
                    await update.effective_chat.send_photo(
                        photo=photo,
                        caption="🎯 ¡Este es el curso que transformará tu carrera profesional!"
                    )
            
            pdf_path = "data/pdf_prueba.pdf"
            if os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as document:
                    await update.effective_chat.send_document(
                        document=document,
                        caption=(
                            "📚 Aquí tienes toda la información detallada del curso.\n\n"
                            f"*Modalidad:* {course_info.get('modality', 'No especificado')}\n"
                            f"*Duración:* {course_info.get('duration', 'No especificado')}\n"
                            f"*Horario:* {course_info.get('schedule', 'No especificado')}\n"
                            f"*Precio:* ${course_info.get('price', 'No especificado')} USD\n"
                            "*Incluye:* Material, acceso a grabaciones, soporte"
                        ),
                        parse_mode='Markdown'
                    )
            
        except Exception as e:
            logger.error(f"Error enviando media del curso: {e}", exc_info=True)

    def _extract_ad_source(self, message_text: str) -> str:
        """
        Extrae la fuente del anuncio desde hashtags.

        Args:
            message_text: Texto del mensaje a analizar

        Returns:
            Hashtag encontrado o #unknown
        """
        hashtags = [word for word in message_text.split() if word.startswith('#')]
        return hashtags[0] if hashtags else "#unknown"

    async def _extract_course_info(self, message_text: str) -> Optional[Dict]:
        """
        Extrae información del curso desde el mensaje del anuncio.

        Args:
            message_text: Texto del mensaje a analizar

        Returns:
            Diccionario con información del curso o None
        """
        try:
            course_keywords = ['ia', 'chatgpt', 'inteligencia', 'artificial']
            
            for keyword in course_keywords:
                if keyword.lower() in message_text.lower():
                    course = await get_course_by_name("Curso de Inteligencia Artificial")
                    if course:
                        return {
                            'name': course.get('name', ''),
                            'description': course.get('description', ''),
                            'price': course.get('price', 120),
                            'duration': course.get('duration', '12 horas'),
                            'modality': course.get('modality', 'Online'),
                            'schedule': course.get('schedule', 'Flexible')
                        }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error extrayendo info del curso: {e}")
            return {}

    async def handle_privacy_response(
        self, 
        user_id: str, 
        accepted: bool
    ) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Maneja la respuesta al aviso de privacidad.

        Args:
            user_id: ID del usuario
            accepted: Si aceptó o no la política de privacidad

        Returns:
            Tupla con mensaje de respuesta y teclado opcional
        """
        user_memory = self.global_memory.get_lead_memory(user_id)
        
        if accepted:
            user_memory.has_accepted_privacy = True
            user_memory.stage = "privacy_accepted"
            self.global_memory.save_lead_memory(user_id, user_memory)
            
            message = self.templates.get_name_request_message()
            return message, None
        else:
            message = self.templates.get_privacy_declined_message()
            return message, None 