"""Manejadores para el flujo de privacidad."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from core.utils.error_handlers import handle_telegram_errors
from core.utils.memory import GlobalMemory
from core.utils.message_templates import MessageTemplates

logger = logging.getLogger(__name__)
templates = MessageTemplates()

@handle_telegram_errors
async def show_privacy_policy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra la política de privacidad."""
    if not update.effective_chat or not update.effective_user:
        return
        
    user_name = update.effective_user.first_name
    message = templates.get_privacy_notice_message(user_name)
    
    keyboard = [
        [InlineKeyboardButton("✅ Acepto", callback_data="privacy_accept")],
        [InlineKeyboardButton("❌ No acepto", callback_data="privacy_decline")]
    ]
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@handle_telegram_errors
async def handle_privacy_response(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Maneja la respuesta del usuario a la política de privacidad."""
    if not update.effective_chat or not update.callback_query:
        return
        
    query = update.callback_query
    
    if callback_data == "privacy_accept":
        # Guardar aceptación en memoria
        if context.bot_data.get('global_mem'):
            mem: GlobalMemory = context.bot_data['global_mem']
            mem.set_privacy_accepted(update.effective_chat.id, True)
        
        # Mostrar siguiente paso
        await query.edit_message_text(
            text="¡Gracias por aceptar! 🎉\n\nAhora podemos continuar con el proceso.",
            reply_markup=None
        )
        
        # Solicitar nombre
        if update.effective_user:
            message = templates.get_name_request_message(update.effective_user.first_name)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message
            )
            
    else:  # privacy_decline
        message = templates.get_privacy_declined_message()
        await query.edit_message_text(
            text=message,
            reply_markup=None
        ) 