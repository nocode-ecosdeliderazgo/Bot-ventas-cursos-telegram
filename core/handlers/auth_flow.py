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
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def ensure_privacy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Verifica si el usuario ya aceptó la privacidad."""
    return getattr(context.bot_data['global_mem'].lead_data, 'privacy_accepted', False)

async def send_privacy_notice(update: Update, context: Optional[ContextTypes.DEFAULT_TYPE] = None) -> None:
    """Envía el aviso de privacidad con botones de aceptación."""
    privacy_text = (
        "🔒 **Aviso de Privacidad**\n\n"
        "Para brindarte la mejor experiencia, necesito que aceptes nuestro aviso de privacidad:\n\n"
        "• Recopilamos tu nombre y preferencias para personalizar tu experiencia\n"
        "• Tus datos se utilizan únicamente para mejorar nuestro servicio\n"
        "• No compartimos tu información con terceros\n"
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
        "• Preferencias de aprendizaje\n"
        "• Interacciones con el bot\n"
        "• Información sobre tus intereses en cursos\n\n"
        "**Cómo utilizamos tu información:**\n"
        "• Para personalizar tu experiencia de aprendizaje\n"
        "• Para recomendarte cursos relevantes\n"
        "• Para mejorar nuestros servicios educativos\n"
        "• Para enviarte información sobre promociones especiales\n\n"
        "**Protección de datos:**\n"
        "• Tus datos están seguros y encriptados\n"
        "• No compartimos tu información con terceros\n"
        "• Puedes solicitar la eliminación en cualquier momento\n"
        "• Cumplimos con las regulaciones de protección de datos\n\n"
        "¿Aceptas que procesemos tus datos según este aviso?"
    )
    privacy_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Acepto y continúo", callback_data="privacy_accept")],
        [InlineKeyboardButton("« Volver", callback_data="privacy_back")]
    ])
    await send_message_with_keyboard(update, privacy_text, privacy_keyboard, parse_mode='Markdown')

async def handle_privacy_response(update: Update, context: ContextTypes.DEFAULT_TYPE, accepted: bool) -> None:
    """Maneja la respuesta del usuario al aviso de privacidad."""
    if not accepted:
        await send_privacy_notice(update, context)
        return
    
    context.bot_data['global_mem'].lead_data.privacy_accepted = True
    context.bot_data['global_mem'].save()
    await request_user_name(update)

async def request_user_name(update: Update) -> None:
    """Solicita el nombre del usuario."""
    welcome_text = (
        "¡Perfecto! 👋 Me alegro de que podamos comenzar.\n\n"
        "Para personalizar tu experiencia, ¿cómo te gustaría que te llame? 😊"
    )
    await send_message_with_keyboard(update, welcome_text, None)

async def save_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: str, data: Optional[Dict[str, Any]] = None) -> None:
    """Guarda o actualiza los datos del usuario en la memoria."""
    if 'global_mem' not in context.bot_data:
        context.bot_data['global_mem'] = Memory()
    if context.bot_data.get('global_user_id') != user_id:
        context.bot_data['global_user_id'] = user_id
        context.bot_data['global_mem'] = Memory()
        context.bot_data['global_mem'].load(user_id)
    
    if data:
        for key, value in data.items():
            setattr(context.bot_data['global_mem'].lead_data, key, value)
    
    context.bot_data['global_mem'].lead_data.user_id = user_id
    context.bot_data['global_mem'].save()

async def redirect_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, from_ad: bool = False) -> None:
    """Redirige al usuario al menú principal."""
    name = context.bot_data['global_mem'].lead_data.name
    
    if from_ad:
        welcome_msg = (
            f"¡Hola {name}! 👋\n\n"
            "Me alegra que te intereses en nuestros cursos de Inteligencia Artificial. "
            "¿Te gustaría conocer más detalles sobre algún curso en específico?"
        )
    else:
        welcome_msg = (
            f"¡Hola {name}! 👋\n\n"
            "¿Qué te gustaría aprender sobre Inteligencia Artificial? "
            "Tenemos cursos de IA práctica, prompts, generación de imágenes y más."
        )
    
    await send_message_with_keyboard(update, welcome_msg, create_main_keyboard(), msg_critico=True)
    await send_message_with_keyboard(update, "Menú principal:", create_main_inline_keyboard(), msg_critico=True)

@handle_telegram_errors
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start y los parámetros de inicio profundo."""
    if not update.effective_user:
        logger.error("Usuario efectivo es None en start_command")
        return

    user_id_str = str(update.effective_user.id)
    logger.info(f"Comando /start recibido de usuario {user_id_str}")

    # Inicializar memoria del usuario
    await save_user_data(context, user_id_str)
    
    # Verificar si viene de un anuncio (deep linking)
    from_ad = False
    if context.args and context.args[0].startswith('ad_'):
        from_ad = True
        campaign_id = context.args[0]
        context.bot_data['global_mem'].lead_data.source = campaign_id
        context.bot_data['global_mem'].save()

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
    await redirect_to_main_menu(update, context, from_ad) 

if __name__ == "__main__":
    print("Este módulo no debe ejecutarse directamente. Por favor, ejecuta agente_ventas_telegram.py") 