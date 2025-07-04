"""
Contact flow handlers for the Telegram bot.
This module handles all advisor contact related interactions.
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from typing import Optional, Dict
from ..services import get_courses, notify_advisor_contact_request
from ..keyboards import create_courses_list_keyboard, create_main_keyboard, create_main_inline_keyboard
from .utils import send_agent_telegram, handle_telegram_errors

logger = logging.getLogger(__name__)

@handle_telegram_errors
async def contact_advisor_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia el flujo de contacto con asesor."""
    lead = context.bot_data['global_mem'].lead_data
    missing = []
    if not lead.email:
        missing.append('email')
    if not lead.phone:
        missing.append('phone')
    if not lead.selected_course:
        missing.append('curso')

    if missing:
        await solicitar_datos_contacto(update, context, missing)
    else:
        await mostrar_confirmacion_datos(update, context)

@handle_telegram_errors
async def solicitar_datos_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE, missing: list) -> None:
    """Solicita los datos faltantes para el contacto."""
    lead = context.bot_data['global_mem'].lead_data
    
    if 'curso' in missing:
        keyboard = create_courses_list_keyboard(get_courses())
        if isinstance(keyboard, InlineKeyboardMarkup):
            await send_agent_telegram(
                update,
                "Primero, selecciona el curso que te interesa:",
                keyboard,
                msg_critico=True
            )
        return
    
    if 'email' in missing:
        context.bot_data['global_mem'].lead_data.stage = "awaiting_email"
        context.bot_data['global_mem'].save()
        await send_agent_telegram(
            update,
            "Por favor, comparte tu correo electrónico para que un asesor pueda contactarte:",
            None,
            msg_critico=True
        )
        return
    
    if 'phone' in missing:
        context.bot_data['global_mem'].lead_data.stage = "awaiting_phone"
        context.bot_data['global_mem'].save()
        await send_agent_telegram(
            update,
            "Por favor, comparte tu número de teléfono para que un asesor pueda contactarte:",
            None,
            msg_critico=True
        )
        return

@handle_telegram_errors
async def mostrar_confirmacion_datos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra los datos recopilados y pide confirmación."""
    lead = context.bot_data['global_mem'].lead_data
    confirmation_text = (
        "📋 Por favor, confirma tus datos:\n\n"
        f"👤 Nombre: {lead.name}\n"
        f"📧 Email: {lead.email}\n"
        f"📱 Teléfono: {lead.phone}\n"
        f"📚 Curso: {lead.selected_course}\n\n"
        "¿Están correctos los datos?"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar datos", callback_data="confirm_contact_data")],
        [InlineKeyboardButton("✏️ Editar datos", callback_data="edit_contact_data")]
    ])
    
    await send_agent_telegram(update, confirmation_text, keyboard, msg_critico=True)

@handle_telegram_errors
async def contactar_asesor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa la solicitud de contacto con asesor."""
    lead = context.bot_data['global_mem'].lead_data
    try:
        notify_advisor_contact_request(lead)
        success_msg = (
            "✅ ¡Gracias por tu interés!\n\n"
            "Un asesor se pondrá en contacto contigo pronto para brindarte más información "
            "y resolver todas tus dudas sobre el curso.\n\n"
            "¿Hay algo más en lo que pueda ayudarte?"
        )
        keyboard = create_main_inline_keyboard()
        if isinstance(keyboard, InlineKeyboardMarkup):
            await send_agent_telegram(update, success_msg, keyboard, msg_critico=True)
        else:
            await send_agent_telegram(update, success_msg, None, msg_critico=True)
    except Exception as e:
        logger.error(f"Error al notificar asesor: {e}")
        error_msg = (
            "Lo siento, hubo un problema al procesar tu solicitud. "
            "Por favor, intenta de nuevo más tarde."
        )
        await send_agent_telegram(update, error_msg, None, msg_critico=True)

@handle_telegram_errors
async def editar_datos_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None) -> None:
    """Permite editar los datos de contacto."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📧 Editar email", callback_data="edit_email")],
        [InlineKeyboardButton("📱 Editar teléfono", callback_data="edit_phone")],
        [InlineKeyboardButton("📚 Cambiar curso", callback_data="change_course")],
        [InlineKeyboardButton("🔙 Volver", callback_data="show_contact_confirmation")]
    ])
    
    edit_msg = (
        "¿Qué información deseas modificar?\n\n"
        "Selecciona una opción:"
    )
    
    if query:
        await query.edit_message_text(edit_msg, reply_markup=keyboard)
    else:
        await send_agent_telegram(update, edit_msg, keyboard, msg_critico=True) 