"""
Authentication flow handlers for the Telegram bot.
This module handles user authentication, privacy notice, and initial setup.
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from ..memory import Memory
from .utils import handle_telegram_errors, send_message_with_keyboard
from ..keyboards import create_main_keyboard, create_main_inline_keyboard
from typing import Optional

logger = logging.getLogger(__name__)

def ensure_privacy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Verifica si el usuario ya aceptó la privacidad."""
    return getattr(context.bot_data['global_mem'].lead_data, 'privacy_accepted', False)

async def send_privacy_notice(update: Update, context: Optional[ContextTypes.DEFAULT_TYPE] = None) -> None:
    """Envía el aviso de privacidad con botones de aceptación."""
    privacy_text = (
        "🔒 **Aviso de Privacidad**\n\n"
        "Para continuar, necesito que aceptes nuestro aviso de privacidad:\n\n"
        "• Recopilamos tu nombre, email y teléfono para brindarte información sobre nuestros cursos\n"
        "• Tus datos se utilizan únicamente para comunicación relacionada con nuestros servicios\n"
        "• No compartimos tu información con terceros sin tu consentimiento\n"
        "• Puedes solicitar la eliminación de tus datos en cualquier momento\n\n"
        "¿Aceptas que procesemos tus datos según este aviso?"
    )
    privacy_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Acepto y continúo", callback_data="privacy_accept")],
        [InlineKeyboardButton("🔒 Ver Aviso Completo", callback_data="privacy_view")]
    ])
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(privacy_text, reply_markup=privacy_keyboard, parse_mode='Markdown')
    elif hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(privacy_text, reply_markup=privacy_keyboard, parse_mode='Markdown')

async def show_full_privacy_notice(update: Update) -> None:
    """Muestra el aviso de privacidad completo."""
    privacy_text = (
        "🔒 **Aviso de Privacidad Completo**\n\n"
        "**Información que recopilamos:**\n"
        "• Nombre completo\n"
        "• Dirección de correo electrónico\n"
        "• Número de teléfono\n"
        "• Información sobre tus intereses en cursos\n\n"
        "**Cómo utilizamos tu información:**\n"
        "• Para brindarte información sobre nuestros cursos\n"
        "• Para enviarte materiales educativos relevantes\n"
        "• Para contactarte sobre promociones especiales\n"
        "• Para mejorar nuestros servicios\n\n"
        "**Protección de datos:**\n"
        "• Tus datos están seguros y protegidos\n"
        "• No compartimos tu información con terceros\n"
        "• Puedes solicitar la eliminación en cualquier momento\n\n"
        "¿Aceptas que procesemos tus datos según este aviso?"
    )
    privacy_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Acepto y continúo", callback_data="privacy_accept")],
        [InlineKeyboardButton("🔒 Ver Aviso Completo", callback_data="privacy_view")]
    ])
    await send_message_with_keyboard(update, privacy_text, privacy_keyboard, parse_mode='Markdown')

async def request_user_name(update: Update) -> None:
    """Solicita el nombre del usuario."""
    welcome_text = "¡Perfecto! 👋 Ahora puedo ayudarte mejor."
    question_text = "¿Cómo te gustaría que te llame? 😊"
    await send_message_with_keyboard(update, welcome_text, None)
    await send_message_with_keyboard(update, question_text, None)

async def save_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: str, name: str = None) -> None:
    """Guarda o actualiza los datos del usuario en la memoria."""
    if 'global_mem' not in context.bot_data:
        context.bot_data['global_mem'] = Memory()
    if context.bot_data.get('global_user_id') != user_id:
        context.bot_data['global_user_id'] = user_id
        context.bot_data['global_mem'] = Memory()
        context.bot_data['global_mem'].load(user_id)
    
    if name:
        context.bot_data['global_mem'].lead_data.name = name
    context.bot_data['global_mem'].lead_data.user_id = user_id
    context.bot_data['global_mem'].save()

async def redirect_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Redirige al usuario al menú principal."""
    welcome_msg = (
        f"¡Hola {context.bot_data['global_mem'].lead_data.name}! 👋\n\n"
        "¿Qué te gustaría aprender sobre Inteligencia Artificial? "
        "Tenemos cursos de IA práctica, prompts, generación de imágenes y más."
    )
    await send_message_with_keyboard(update, welcome_msg, create_main_keyboard(), msg_critico=True)
    await send_message_with_keyboard(update, "Menú principal:", create_main_inline_keyboard(), msg_critico=True)

@handle_telegram_errors
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start, verifica privacidad y muestra menú principal."""
    if not update.effective_user:
        logger.error("Usuario efectivo es None en start_command")
        return

    user_id_str = str(update.effective_user.id)
    logger.info(f"Comando /start recibido de usuario {user_id_str}")

    # Inicializar memoria del usuario
    await save_user_data(context, user_id_str)

    # Verificar privacidad
    if not context.bot_data['global_mem'].lead_data.privacy_accepted:
        logger.info(f"Usuario {user_id_str} no ha aceptado privacidad, mostrando aviso")
        await send_privacy_notice(update, context)
        return

    # Si no tiene nombre, solicitarlo
    if not context.bot_data['global_mem'].lead_data.name:
        await request_user_name(update)
        context.bot_data['global_mem'].lead_data.stage = "awaiting_name"
        context.bot_data['global_mem'].save()
        return

    # Si ya tiene nombre, mostrar menú principal
    await redirect_to_main_menu(update, context) 