"""
Course flow handlers for the Telegram bot.
This module handles all course-related interactions.
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from typing import Optional
from ..services import get_courses, get_course_detail
from ..keyboards import create_courses_list_keyboard, create_course_explore_keyboard
from .utils import send_agent_telegram, handle_telegram_errors, send_grouped_messages

logger = logging.getLogger(__name__)

@handle_telegram_errors
async def mostrar_lista_cursos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra la lista de cursos disponibles con teclado inline."""
    cursos = get_courses()
    if not cursos:
        await send_agent_telegram(update, "Por el momento no hay cursos disponibles.")
        return
    
    keyboard = create_courses_list_keyboard(cursos)
    if isinstance(keyboard, InlineKeyboardMarkup):
        await send_agent_telegram(update, "Selecciona un curso para más información:", keyboard, msg_critico=True)
    else:
        await send_agent_telegram(update, "Selecciona un curso para más información:", None, msg_critico=True)

@handle_telegram_errors
async def mostrar_menu_curso_exploracion(update: Update, context: ContextTypes.DEFAULT_TYPE, course_id: str) -> None:
    """Muestra el menú de curso con diferentes opciones según el contexto."""
    course = get_course_detail(course_id)
    if not course:
        await send_agent_telegram(update, "Lo siento, no pude encontrar la información del curso.")
        return
    
    # Determinar el tipo de visualización basado en el callback_data
    show_type = "general"
    if hasattr(update, 'callback_query') and update.callback_query and update.callback_query.data:
        callback_data = update.callback_query.data
        if callback_data.startswith("modules_"):
            show_type = "modules"
        elif callback_data.startswith("duration_"):
            show_type = "duration"
        elif callback_data.startswith("price_"):
            show_type = "price"
        elif callback_data.startswith("buy_"):
            show_type = "buy"
    
    # Preparar el texto según el tipo de visualización
    if show_type == "modules":
        modules_list = course.get('modules_list', '• Módulo 1: Fundamentos\n• Módulo 2: Aplicaciones Prácticas\n• Módulo 3: Proyectos Reales')
        info_text = (
            f"📚 <b>{course.get('name', 'Curso')} - Módulos y Contenido</b>\n\n"
            f"{course.get('modules_description', 'Módulos del curso:')}\n\n"
            f"{modules_list}\n\n"
            "¿Qué más te gustaría saber?"
        )
    elif show_type == "duration":
        schedule_info = course.get('schedule_info', 'Acceso 24/7 al contenido. Estudia a tu propio ritmo.')
        info_text = (
            f"⏱️ <b>{course.get('name', 'Curso')} - Duración y Horarios</b>\n\n"
            f"⌛ Duración total: {course.get('duration', '40 horas')}\n"
            f"📅 Modalidad: {course.get('modality', 'Online, a tu ritmo')}\n"
            f"🎯 Nivel: {course.get('level', 'Todos los niveles')}\n\n"
            f"{schedule_info}\n\n"
            "¿Qué más te gustaría saber?"
        )
    elif show_type == "price":
        includes = course.get('includes', '• Acceso de por vida\n• Certificado digital\n• Soporte personalizado')
        payment_methods = course.get('payment_methods', '• Tarjeta de crédito/débito\n• PayPal\n• Transferencia bancaria')
        info_text = (
            f"💰 <b>{course.get('name', 'Curso')} - Precio y Formas de Pago</b>\n\n"
            f"💳 Precio: {course.get('price', 'Consultar precio')}\n"
            f"💎 Incluye:\n{includes}\n\n"
            f"Formas de pago disponibles:\n"
            f"{payment_methods}\n\n"
            "¿Te gustaría inscribirte o saber más?"
        )
    elif show_type == "buy":
        info_text = (
            f"🎉 <b>¡Excelente elección!</b>\n\n"
            f"Has seleccionado el curso:\n"
            f"<b>{course.get('name', 'Curso')}</b>\n\n"
            f"Para proceder con tu inscripción:\n\n"
            f"1️⃣ Un asesor te contactará en breve\n"
            f"2️⃣ Te ayudará con el proceso de pago\n"
            f"3️⃣ Recibirás acceso inmediato al curso\n\n"
            f"¿Prefieres contactar directamente a un asesor?"
        )
    else:
        info_text = (
            f"📚 <b>{course.get('name', 'Curso')}</b>\n\n"
            f"{course.get('short_description', '')}\n\n"
            "Selecciona una opción para más detalles:"
        )
    
    # Crear el teclado con las opciones
    keyboard = create_course_explore_keyboard(course['id'], course.get('name', 'Curso'))
    
    # Enviar o editar el mensaje según el contexto
    if hasattr(update, 'callback_query') and update.callback_query:
        if isinstance(keyboard, InlineKeyboardMarkup):
            await update.callback_query.edit_message_text(info_text, reply_markup=keyboard, parse_mode='HTML')
        else:
            await update.callback_query.edit_message_text(info_text, parse_mode='HTML')
    else:
        if isinstance(keyboard, InlineKeyboardMarkup):
            await send_agent_telegram(update, info_text, keyboard, msg_critico=True)
        else:
            await send_agent_telegram(update, info_text, None, msg_critico=True) 