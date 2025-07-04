"""
FAQ flow handlers for the Telegram bot.
"""

import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Optional
from ..services import get_courses, get_course_detail
from ..faq import get_faq_keyboard, format_faq_response
from .utils import send_agent_telegram, handle_telegram_errors
from .course_flow import mostrar_lista_cursos

logger = logging.getLogger(__name__)

@handle_telegram_errors
async def mostrar_faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra la lista de preguntas frecuentes."""
    keyboard = get_faq_keyboard()
    if keyboard:
        await send_agent_telegram(
            update,
            "Selecciona una pregunta para ver la respuesta:",
            keyboard,
            msg_critico=True
        )
    else:
        await send_agent_telegram(
            update,
            "Lo siento, no pude cargar las preguntas frecuentes en este momento.",
            None
        )

@handle_telegram_errors
async def responder_faq(update: Update, context: ContextTypes.DEFAULT_TYPE, template_idx: int, course_id: Optional[str] = None) -> None:
    """Responde a una pregunta frecuente específica."""
    course_data = None
    if course_id:
        course_data = get_course_detail(course_id)
    
    mensaje, keyboard = format_faq_response(template_idx, course_data)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        if isinstance(keyboard, InlineKeyboardMarkup):
            await update.callback_query.edit_message_text(
                mensaje,
                reply_markup=keyboard,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
        else:
            await update.callback_query.edit_message_text(
                mensaje,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
    else:
        if isinstance(keyboard, InlineKeyboardMarkup):
            await send_agent_telegram(update, mensaje, keyboard, msg_critico=True)
        else:
            await send_agent_telegram(update, mensaje, None, msg_critico=True)

@handle_telegram_errors
async def mostrar_cursos_para_faq(update: Update, context: ContextTypes.DEFAULT_TYPE, template_idx: int) -> None:
    """Muestra la lista de cursos para responder una FAQ específica."""
    cursos = get_courses()
    if not cursos:
        await send_agent_telegram(update, "Por el momento no hay cursos disponibles.")
        return
    
    keyboard = []
    for curso in cursos:
        keyboard.append([InlineKeyboardButton(
            curso['name'],
            callback_data=f"faq_course_{template_idx}_{curso['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("❓ Ver otras preguntas", callback_data="faq")])
    keyboard.append([InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")])
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            "Selecciona un curso para ver la información específica:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    else:
        await send_agent_telegram(
            update,
            "Selecciona un curso para ver la información específica:",
            InlineKeyboardMarkup(keyboard),
            msg_critico=True
        ) 