"""
Manejo del flujo de anuncios.
Implementa el flujo completo según el system prompt:
1. Detección de hashtags
2. Aviso de privacidad
3. Bienvenida de Brenda
4. Presentación del curso
5. Registro de métricas
"""

import logging
from typing import Dict, Optional, Tuple, Union, List, Any
from datetime import datetime

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from core.services.database import DatabaseService
from core.agents.agent_tools import AgentTools
from core.services.courseService import CourseService
from core.services.supabase_service import save_lead, get_course_detail
from core.utils.memory import GlobalMemory, LeadMemory
from core.utils.message_templates import MessageTemplates
from core.utils.course_templates import CourseTemplates

logger = logging.getLogger(__name__)

class AdsFlowHandler:
    """
    Maneja el flujo completo de usuarios que llegan desde anuncios.
    Implementa el system prompt completo para usuarios de publicidad.
    """
    
    def __init__(self, db: DatabaseService, agent: AgentTools) -> None:
        """
        Inicializa el manejador de flujo de anuncios.
        """
        self.db = db
        self.agent = agent
        self.course_service = CourseService(db)
        self.global_memory = GlobalMemory()
        self.templates = MessageTemplates()
        
        # Mapeo de hashtags de cursos a IDs
        self.course_mapping = {
            'CURSO_IA_CHATGPT': 'a392bf83-4908-4807-89a9-95d0acc807c9',
            'curso:ia_chatgpt': 'a392bf83-4908-4807-89a9-95d0acc807c9',
            'CURSO_PROMPTS': 'b00f3d1c-e876-4bac-b734-2715110440a0',
            'curso:prompts': 'b00f3d1c-e876-4bac-b734-2715110440a0',
            'CURSO_IMAGENES': '2715110440a0-b734-b00f3d1c-e876-4bac',
            'curso:imagenes': '2715110440a0-b734-b00f3d1c-e876-4bac',
            'CURSO_AUTOMATIZACION': '4bac-2715110440a0-b734-b00f3d1c-e876',
            'curso:automatizacion': '4bac-2715110440a0-b734-b00f3d1c-e876',
            # Agregar el nuevo mapeo
            'CURSO_NUEVO': 'd7ab3f21-5c6e-4d89-91f3-7a2b4e5c8d9f',
            'curso:nuevo': 'd7ab3f21-5c6e-4d89-91f3-7a2b4e5c8d9f'
        }

    async def process_ad_message(self, message_data: dict, user_data: dict, course_hashtag: str, campaign_hashtag: str) -> Tuple[Union[str, List[Dict[str, Any]]], Optional[InlineKeyboardMarkup]]:
        """
        Procesa un mensaje de usuario que viene de anuncio.
        Implementa el flujo completo del system prompt.
        """
        try:
            user_id = str(user_data['id'])
            
            # 1. Registrar interacción en métricas
            await self._register_ad_interaction(user_id, course_hashtag, campaign_hashtag)
            
            # 2. Obtener información del curso
            course_id = self._extract_course_id(course_hashtag)
            if not course_id:
                logger.warning(f"No se pudo mapear el hashtag {course_hashtag} a un curso")
                return "Lo siento, no pude identificar el curso. Por favor, contáctanos directamente.", None
            
            # 3. Verificar si es primera vez (aviso de privacidad)
            user_memory = self.global_memory.get_lead_memory(user_id)
            if not user_memory:
                user_memory = LeadMemory(user_id=user_id)
                # ✅ ASIGNAR CURSO INMEDIATAMENTE al detectar anuncio
                user_memory.selected_course = course_id
                self.global_memory.save_lead_memory(user_id, user_memory)
            
            # ✅ ASEGURAR que siempre tenga el curso asignado
            if not user_memory.selected_course:
                user_memory.selected_course = course_id
                self.global_memory.save_lead_memory(user_id, user_memory)
            
            if not user_memory.privacy_accepted:
                # Mostrar aviso de privacidad
                return await self._show_privacy_notice(user_data)
            
            # 4. Si ya aceptó privacidad, continuar con bienvenida de Brenda
            if not user_memory.brenda_introduced:
                return await self._show_brenda_welcome(user_data, course_id)
            
            # 5. Si ya se presentó Brenda, mostrar curso
            return await self._present_course(user_data, course_id)
            
        except Exception as e:
            logger.error(f"Error procesando mensaje de anuncio: {e}")
            return "Lo siento, hubo un error. Por favor, intenta nuevamente.", None

    async def _register_ad_interaction(self, user_id: str, course_hashtag: str, campaign_hashtag: str):
        """Registra la interacción del usuario con el anuncio en Supabase."""
        try:
            interaction_data = {
                'user_id': user_id,
                'course_hashtag': course_hashtag,
                'campaign_hashtag': campaign_hashtag,
                'timestamp': datetime.utcnow().isoformat(),
                'interaction_type': 'ad_click'
            }
            
            # Guardar en Supabase (si está disponible)
            await save_lead(user_id, interaction_data)
            logger.info(f"Interacción registrada: {user_id} - {course_hashtag} - {campaign_hashtag}")
            
        except Exception as e:
            logger.error(f"Error registrando interacción: {e}")

    def _extract_course_id(self, course_hashtag: str) -> Optional[str]:
        """Extrae el ID del curso desde el hashtag."""
        # Normalizar hashtag
        normalized = course_hashtag.upper()
        course_id = self.course_mapping.get(normalized)
        return course_id

    async def _show_privacy_notice(self, user_data: dict) -> Tuple[str, InlineKeyboardMarkup]:
        """Muestra el aviso de privacidad."""
        user_name = user_data.get('first_name', 'Usuario')
        message = self.templates.get_privacy_notice_message(user_name)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 Ver aviso completo", callback_data="privacy_full")],
            [InlineKeyboardButton("✅ Acepto", callback_data="privacy_accept")],
            [InlineKeyboardButton("❌ No acepto", callback_data="privacy_decline")]
        ])
        
        return message, keyboard

    async def _show_brenda_welcome(self, user_data: dict, course_id: str) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """Muestra la bienvenida de Brenda y pide el nombre preferido."""
        user_name = user_data.get('first_name', 'Usuario')
        
        message = f"""¡Hola {user_name}! 👋

Soy Brenda, parte del equipo automatizado de Aprenda y Aplique IA y te voy a ayudar.

Antes de mostrarte toda la información del curso, ¿cómo te gustaría que te llame? Puedes decirme tu nombre preferido o simplemente responder "está bien" si prefieres que te llame {user_name}."""
        
        # Marcar que Brenda ya se presentó
        user_memory = self.global_memory.get_lead_memory(str(user_data['id']))
        if user_memory:
            user_memory.brenda_introduced = True
            user_memory.selected_course = course_id
            self.global_memory.save_lead_memory(str(user_data['id']), user_memory)
        
        return message, None

    async def _present_course(self, user_data: dict, course_id: str) -> Tuple[List[Dict[str, Any]], Optional[InlineKeyboardMarkup]]:
        """Presenta el curso con PDF, imagen y datos."""
        try:
            # Obtener detalles del curso
            course_details = await self.course_service.getCourseDetails(course_id)
            if not course_details:
                return [{"type": "text", "content": "Lo siento, no pude obtener los detalles del curso."}], None
            
            response_items = []
            
            # 1. Enviar PDF si está disponible
            syllabus_url = course_details.get('syllabus_url')
            if syllabus_url:
                response_items.append({
                    "type": "document",
                    "url": syllabus_url,
                    "caption": "📚 Aquí tienes el PDF descriptivo del curso"
                })
            
            # 2. Enviar imagen si está disponible
            thumbnail_url = course_details.get('thumbnail_url')
            if thumbnail_url:
                response_items.append({
                    "type": "image",
                    "url": thumbnail_url,
                    "caption": "🎯 Imagen del curso"
                })
            
            # 3. Enviar datos del curso
            course_info = CourseTemplates.format_course_info(course_details)
            response_items.append({
                "type": "text",
                "content": course_info
            })
            
            # 4. Crear teclado con opciones
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Hacer una pregunta", callback_data="ask_question")],
                [InlineKeyboardButton("💰 Ver precios", callback_data="show_prices")],
                [InlineKeyboardButton("📞 Agendar llamada", callback_data="schedule_call")]
            ])
            
            return response_items, keyboard
            
        except Exception as e:
            logger.error(f"Error presentando curso: {e}")
            return [{"type": "text", "content": "Lo siento, hubo un error obteniendo la información del curso."}], None

    def _format_course_info(self, course_details: dict) -> str:
        """Formatea la información del curso usando plantillas centralizadas."""
        return CourseTemplates.format_course_info(course_details)
       