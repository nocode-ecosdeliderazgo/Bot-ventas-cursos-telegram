"""Utilidades de navegación para el bot."""
import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.utils.error_handlers import handle_telegram_errors
from core.utils.message_templates import create_menu_message, create_menu_keyboard

logger = logging.getLogger(__name__)

@handle_telegram_errors
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el menú principal."""
    if not update.effective_chat:
        logger.error("No se pudo mostrar el menú: effective_chat es None")
        return
    
    try:
        # Obtener mensaje y teclado del menú
        menu_message = create_menu_message()
        keyboard = create_menu_keyboard()
        
        # Enviar menú
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=menu_message,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error mostrando menú principal: {e}")
        raise 