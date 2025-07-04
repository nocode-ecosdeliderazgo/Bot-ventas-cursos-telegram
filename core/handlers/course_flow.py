"""
Course flow handlers for the Telegram bot.
This module handles all course-related interactions.
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from typing import Optional
from ..services import get_courses, get_course_detail, get_modules
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
        # Obtener módulos de Supabase
        modules = get_modules(course_id)
        modules_text = ""
        if modules:
            for i, module in enumerate(modules, 1):
                modules_text += f"📌 Módulo {i}: {module.get('name', 'Sin nombre')}\n"
                if module.get('duration'):
                    modules_text += f"⏱️ Duración: {module.get('duration')}\n"
                if module.get('description'):
                    modules_text += f"{module.get('description')}\n"
                modules_text += "\n"
        else:
            modules_text = course.get('modules_list', 'Información de módulos no disponible.')
        
        info_text = (
            f"📚 <b>{course.get('name', 'Curso')} - Módulos y Contenido</b>\n\n"
            f"{course.get('long_description', course.get('short_description', 'Descripción no disponible.'))}\n\n"
            f"{modules_text}\n"
            "¿Qué más te gustaría saber sobre el curso?"
        )
    elif show_type == "duration":
        # Obtener información de duración y horarios
        total_duration = course.get('total_duration', 'No especificada')
        schedule = course.get('schedule', 'Información de horarios no disponible.')
        online = course.get('online', True)
        modality = "Online" if online else "Presencial"
        
        info_text = (
            f"⏱️ <b>{course.get('name', 'Curso')} - Duración y Horarios</b>\n\n"
            f"⌛ Duración total: {total_duration}\n"
            f"📅 Modalidad: {modality}\n"
            f"🎯 Nivel: {course.get('level', 'No especificado')}\n\n"
            f"📋 Horarios y Detalles:\n{schedule}\n\n"
            "¿Te gustaría conocer más detalles sobre el curso?"
        )
    elif show_type == "price":
        info_text = (
            f"💰 <b>{course.get('name', 'Curso')} - Precio y Formas de Pago</b>\n\n"
            f"💳 Precio: ${course.get('price_usd', 'No especificado')} {course.get('currency', 'USD')}\n"
            f"💎 El curso incluye:\n{course.get('includes', 'Información no disponible.')}\n\n"
            "Formas de pago disponibles:\n"
            f"{course.get('payment_methods', 'Información no disponible.')}\n\n"
            "¿Te gustaría proceder con la inscripción?"
        )
    elif show_type == "buy":
        purchase_link = course.get('purchase_link')
        if purchase_link:
            info_text = (
                f"🎉 <b>¡Excelente elección!</b>\n\n"
                "Has seleccionado:\n"
                f"<b>{course.get('name', 'Curso')}</b>\n\n"
                f"💳 Precio: ${course.get('price_usd', 'No especificado')} {course.get('currency', 'USD')}\n\n"
                "Para inscribirte ahora:\n"
                f"<a href='{purchase_link}'>👉 Haz clic aquí para proceder con el pago</a>\n\n"
                "O si prefieres, podemos:\n"
                "• Ayudarte con el proceso de pago\n"
                "• Resolver tus dudas\n"
                "• Explicarte los beneficios en detalle\n\n"
                "¿Qué prefieres?"
            )
        else:
            info_text = (
                f"🎉 <b>¡Excelente elección!</b>\n\n"
                "Has seleccionado:\n"
                f"<b>{course.get('name', 'Curso')}</b>\n\n"
                "Para proceder con tu inscripción:\n\n"
                "1️⃣ Un asesor te contactará en breve\n"
                "2️⃣ Te ayudará con el proceso de pago\n"
                "3️⃣ Recibirás acceso inmediato al curso\n\n"
                "¿Prefieres contactar directamente a un asesor?"
            )
    else:
        info_text = (
            f"📚 <b>{course.get('name', 'Curso')}</b>\n\n"
            f"{course.get('short_description', course.get('long_description', 'Descripción no disponible.'))}\n\n"
            "Selecciona una opción para más detalles:"
        )
    
    # Crear el teclado con las opciones
    keyboard = create_course_explore_keyboard(course['id'], course.get('name', 'Curso'))
    
    # Enviar o editar el mensaje según el contexto
    if hasattr(update, 'callback_query') and update.callback_query:
        if isinstance(keyboard, InlineKeyboardMarkup):
            await update.callback_query.edit_message_text(info_text, reply_markup=keyboard, parse_mode='HTML', disable_web_page_preview=True)
        else:
            await update.callback_query.edit_message_text(info_text, parse_mode='HTML', disable_web_page_preview=True)
    else:
        if isinstance(keyboard, InlineKeyboardMarkup):
            await send_agent_telegram(update, info_text, keyboard, msg_critico=True)
        else:
            await send_agent_telegram(update, info_text, None, msg_critico=True) 