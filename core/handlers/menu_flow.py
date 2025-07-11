"""
Manejador del flujo de menú principal para usuarios que inician desde cero.
Implementa:
1. Aviso de privacidad
2. Bienvenida de Brenda
3. Menú de subtemas
4. Selección de cursos
5. Integración con flujo de anuncios
"""

import logging
from typing import Dict, Optional, Tuple, Union, List, Any
from datetime import datetime

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from core.services.database import DatabaseService
from core.agents.agent_tools import AgentTools
from core.services.courseService import CourseService
from core.utils.memory import GlobalMemory, LeadMemory
from core.utils.message_templates import MessageTemplates
from core.utils.course_templates import CourseTemplates
from core.handlers.ads_flow import AdsFlowHandler

logger = logging.getLogger(__name__)

class MenuFlowHandler:
    """
    Maneja el flujo de menú principal para usuarios que inician desde cero.
    """
    
    def __init__(self, db: DatabaseService, agent: AgentTools) -> None:
        self.db = db
        self.agent = agent
        self.course_service = CourseService(db)
        self.global_memory = GlobalMemory()
        self.templates = MessageTemplates()
        self.ads_flow = AdsFlowHandler(db, agent)
        
    async def handle_start_command(self, user_data: dict) -> Tuple[Union[str, List[Dict[str, Any]]], Optional[InlineKeyboardMarkup]]:
        """
        Maneja el comando /start para usuarios que inician desde cero.
        """
        try:
            user_id = str(user_data['id'])
            user_name = user_data.get('first_name', 'Usuario')
            
            # Verificar si ya existe en memoria
            user_memory = self.global_memory.get_lead_memory(user_id)
            if not user_memory:
                user_memory = LeadMemory(user_id=user_id)
                self.global_memory.save_lead_memory(user_id, user_memory)
            
            # Si no ha aceptado privacidad, mostrar aviso
            if not user_memory.privacy_accepted:
                return await self._show_privacy_notice(user_data)
            
            # Si no se ha presentado Brenda, mostrar bienvenida
            if not user_memory.brenda_introduced:
                return await self._show_brenda_welcome(user_data)
            
            # Si no tiene nombre preferido, pedirlo
            if not user_memory.preferred_name:
                return await self._ask_preferred_name(user_data)
            
            # Mostrar menú de cursos directamente (no subtemas)
            return await self._show_courses_menu(user_data)
            
        except Exception as e:
            logger.error(f"Error en handle_start_command: {e}")
            return "Lo siento, hubo un error. Por favor, intenta nuevamente.", None
    
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
    
    async def _show_brenda_welcome(self, user_data: dict) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """Muestra la bienvenida de Brenda."""
        user_name = user_data.get('first_name', 'Usuario')
        user_id = str(user_data['id'])
        
        message = f"""¡Hola {user_name}! 👋

Soy Brenda, parte del equipo automatizado de Aprenda y Aplique IA y te voy a ayudar a encontrar el curso perfecto para ti.

Antes de mostrarte nuestros cursos, ¿cómo te gustaría que te llame? Puedes decirme tu nombre preferido o simplemente responder "está bien" si prefieres que te llame {user_name}."""
        
        # Marcar que Brenda ya se presentó
        user_memory = self.global_memory.get_lead_memory(user_id)
        if user_memory:
            user_memory.brenda_introduced = True
            self.global_memory.save_lead_memory(user_id, user_memory)
        
        return message, None
    
    async def _ask_preferred_name(self, user_data: dict) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """Pide el nombre preferido si no se ha establecido."""
        user_name = user_data.get('first_name', 'Usuario')
        
        message = f"""¿Cómo te gustaría que te llame? Puedes decirme tu nombre preferido o simplemente responder "está bien" si prefieres que te llame {user_name}."""
        
        return message, None
    
    async def _show_courses_menu(self, user_data: dict) -> Tuple[str, InlineKeyboardMarkup]:
        """Muestra el menú de cursos disponibles directamente."""
        try:
            user_id = str(user_data['id'])
            user_memory = self.global_memory.get_lead_memory(user_id)
            preferred_name = user_memory.preferred_name if user_memory else user_data.get('first_name', 'Usuario')
            
            # Obtener cursos directamente de la base de datos
            query = """
            SELECT id, name, short_description, price, currency, level
            FROM ai_courses 
            WHERE status = 'publicado'
            ORDER BY name
            """
            courses = await self.db.fetch_all(query)
            logger.info(f"Cursos obtenidos de la base de datos: {courses}")
            
            if not courses:
                return "Lo siento, no hay cursos disponibles en este momento.", None
            
            message = f"""¡Perfecto {preferred_name}! 🎯

Estos son nuestros cursos disponibles. Selecciona el que más te interese:

"""
            
            # Crear botones para cada curso
            buttons = []
            for course in courses:
                # Formatear precio
                try:
                    price = float(course['price']) if course['price'] else 0
                    currency = course['currency'] or 'USD'
                    price_text = f"${price:.0f} {currency}" if price > 0 else "Consultar precio"
                except (ValueError, TypeError):
                    price_text = "Consultar precio"
                
                button_text = f"🎓 {course['name']}"
                callback_data = f"course_{course['id']}"
                logger.info(f"Generando botón: '{button_text}' con callback_data: '{callback_data}'")
                buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            keyboard = InlineKeyboardMarkup(buttons)
            return message, keyboard
            
        except Exception as e:
            logger.error(f"Error mostrando menú de cursos: {e}")
            return "Lo siento, hubo un error obteniendo los cursos.", None
    
    async def _show_subthemes_menu(self, user_data: dict) -> Tuple[str, InlineKeyboardMarkup]:
        """Muestra el menú de subtemas disponibles."""
        try:
            user_id = str(user_data['id'])
            user_memory = self.global_memory.get_lead_memory(user_id)
            preferred_name = user_memory.preferred_name if user_memory else user_data.get('first_name', 'Usuario')
            
            # Obtener subtemas de la base de datos
            query = """
            SELECT id, name, description 
            FROM ai_subthemes 
            WHERE active = true 
            ORDER BY name
            """
            subthemes = await self.db.fetch_all(query)
            
            if not subthemes:
                return "Lo siento, no hay subtemas disponibles en este momento.", None
            
            message = f"""¡Perfecto {preferred_name}! 🎯

Tenemos varios cursos organizados por categorías. ¿Cuál te interesa más?

Selecciona una categoría para ver los cursos disponibles:"""
            
            # Crear botones para cada subtema
            buttons = []
            for subtheme in subthemes:
                button_text = f"🎯 {subtheme['name']}"
                callback_data = f"subtheme_{subtheme['id']}"
                buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            keyboard = InlineKeyboardMarkup(buttons)
            return message, keyboard
            
        except Exception as e:
            logger.error(f"Error mostrando menú de subtemas: {e}")
            return "Lo siento, hubo un error obteniendo las categorías.", None
    
    async def handle_subtheme_selection(self, user_data: dict, subtheme_id: str) -> Tuple[str, InlineKeyboardMarkup]:
        """Maneja la selección de un subtema y muestra los cursos disponibles."""
        try:
            user_id = str(user_data['id'])
            user_memory = self.global_memory.get_lead_memory(user_id)
            preferred_name = user_memory.preferred_name if user_memory else user_data.get('first_name', 'Usuario')
            
            # Obtener información del subtema
            subtheme_query = """
            SELECT id, name, description 
            FROM ai_subthemes 
            WHERE id = $1
            """
            subtheme = await self.db.fetch_one(subtheme_query, subtheme_id)
            
            if not subtheme:
                return "Lo siento, no pude encontrar esa categoría.", None
            
            # Obtener cursos del subtema
            courses_query = """
            SELECT id, name, short_description, price, currency, level, total_duration_min
            FROM ai_courses 
            WHERE subtheme_id = $1 AND status = 'publicado'
            ORDER BY name
            """
            courses = await self.db.fetch_all(courses_query, subtheme_id)
            
            if not courses:
                return f"Lo siento, no hay cursos disponibles en {subtheme['name']} en este momento.", None
            
            message = f"""🎯 **{subtheme['name']}**

{subtheme['description']}

¡Perfecto {preferred_name}! Estos son los cursos disponibles en esta categoría:

"""
            
            # Crear botones para cada curso
            buttons = []
            for course in courses:
                # Formatear precio
                try:
                    price = float(course['price']) if course['price'] else 0
                    currency = course['currency'] or 'USD'
                    price_text = f"${price:.0f} {currency}" if price > 0 else "Consultar precio"
                except (ValueError, TypeError):
                    price_text = "Consultar precio"
                
                button_text = f"🎓 {course['name']} - {price_text}"
                callback_data = f"course_{course['id']}"
                buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            # Botón para volver al menú principal
            buttons.append([InlineKeyboardButton("🔙 Volver a categorías", callback_data="back_to_subthemes")])
            
            keyboard = InlineKeyboardMarkup(buttons)
            return message, keyboard
            
        except Exception as e:
            logger.error(f"Error manejando selección de subtema: {e}")
            return "Lo siento, hubo un error obteniendo los cursos.", None
    
    async def handle_course_selection(self, user_data: dict, course_id: str) -> Tuple[Union[str, List[Dict[str, Any]]], Optional[InlineKeyboardMarkup]]:
        """Maneja la selección de un curso y lanza el flujo de anuncios."""
        try:
            user_id = str(user_data['id'])
            logger.info(f"Iniciando handle_course_selection para usuario {user_id}, curso {course_id}")
            
            # Guardar el curso seleccionado en memoria
            user_memory = self.global_memory.get_lead_memory(user_id)
            if user_memory:
                user_memory.selected_course = course_id
                self.global_memory.save_lead_memory(user_id, user_memory)
                logger.info(f"Curso {course_id} guardado en memoria para usuario {user_id}")
            
            # Usar el flujo de anuncios para presentar el curso
            logger.info(f"Llamando _present_course para curso {course_id}")
            return await self.ads_flow._present_course(user_data, course_id)
            
        except Exception as e:
            logger.error(f"Error manejando selección de curso: {e}")
            return "Lo siento, hubo un error obteniendo la información del curso.", None
    
    async def handle_privacy_acceptance(self, user_data: dict) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """Maneja la aceptación del aviso de privacidad."""
        try:
            user_id = str(user_data['id'])
            user_memory = self.global_memory.get_lead_memory(user_id)
            
            if user_memory:
                user_memory.privacy_accepted = True
                self.global_memory.save_lead_memory(user_id, user_memory)
            
            return await self._show_brenda_welcome(user_data)
            
        except Exception as e:
            logger.error(f"Error manejando aceptación de privacidad: {e}")
            return "Lo siento, hubo un error. Por favor, intenta nuevamente.", None
    
    async def handle_preferred_name(self, user_data: dict, message_text: str) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """Maneja la respuesta del nombre preferido."""
        try:
            user_id = str(user_data['id'])
            user_memory = self.global_memory.get_lead_memory(user_id)
            
            if message_text.lower() in ['está bien', 'esta bien', 'ok']:
                preferred_name = user_data.get('first_name', 'Usuario')
            else:
                preferred_name = message_text.strip()
            
            if user_memory:
                user_memory.preferred_name = preferred_name
                self.global_memory.save_lead_memory(user_id, user_memory)
            
            return await self._show_courses_menu(user_data)
            
        except Exception as e:
            logger.error(f"Error manejando nombre preferido: {e}")
            return "Lo siento, hubo un error. Por favor, intenta nuevamente.", None