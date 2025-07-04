"""
Course flow handlers for the Telegram bot.
This module handles all course-related interactions.
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from typing import Optional
from ..services import get_courses, get_course_detail
from ..keyboards import create_courses_list_keyboard, create_course_explore_keyboard, create_course_selection_keyboard
from .utils import send_agent_telegram, handle_telegram_errors

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
    show_modules = False
    show_info = False
    show_purchase = False
    
    if hasattr(update, 'callback_query') and update.callback_query and update.callback_query.data:
        if update.callback_query.data.startswith("modules_"):
            show_modules = True
        elif update.callback_query.data.startswith("info_"):
            show_info = True
        elif update.callback_query.data.startswith("buy_course_"):
            show_purchase = True
    
    # Preparar el texto según el tipo de visualización
    if show_modules:
        info_text = (
            f"<b>{course.get('name', 'Curso')} - Módulos</b>\n\n"
            f"{course.get('modules_description', 'No hay información de módulos disponible.')}\n\n"
            "¿Qué te gustaría hacer?"
        )
    elif show_info:
        info_text = (
            f"<b>{course.get('name', 'Curso')} - Información Detallada</b>\n\n"
            f"{course.get('full_description', course.get('short_description', ''))}\n\n"
            "¿Qué te gustaría hacer?"
        )
    elif show_purchase:
        info_text = (
            f"<b>{course.get('name', 'Curso')} - Información de Compra</b>\n\n"
            f"Precio: {course.get('price', 'Consultar precio')}\n"
            f"Duración: {course.get('duration', 'Consultar duración')}\n"
            f"Modalidad: {course.get('modality', 'Consultar modalidad')}\n\n"
            f"{course.get('purchase_info', '')}\n\n"
            "¿Qué te gustaría hacer?"
        )
    else:
        info_text = (
            f"<b>{course.get('name', 'Curso')}</b>\n\n"
            f"{course.get('short_description', '')}\n\n"
            "¿Qué te gustaría hacer?"
        )
    
    # Crear el teclado con las opciones correspondientes
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

@handle_telegram_errors
async def mostrar_menu_curso_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE, course_id: str) -> None:
    """Muestra el menú de curso con botón 'Seleccionar este curso' (contacto/promociones)."""
    course = get_course_detail(course_id)
    if not course:
        await send_agent_telegram(update, "Lo siento, no pude encontrar la información del curso.")
        return
    
    keyboard = create_course_selection_keyboard(course['id'], course.get('name', 'Curso'))
    info_text = f"<b>{course.get('name', 'Curso')}</b>\n\n{course.get('short_description', '')}\n\n¿Qué te gustaría hacer?"
    
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