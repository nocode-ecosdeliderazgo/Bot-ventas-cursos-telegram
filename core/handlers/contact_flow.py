"""Manejadores para el flujo de contacto."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from core.utils.error_handlers import handle_telegram_errors
from core.utils.memory import GlobalMemory
from core.utils.navigation import show_main_menu

logger = logging.getLogger(__name__)

@handle_telegram_errors
async def show_contact_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra las opciones de contacto."""
    if not update.effective_chat:
        return
        
    message = """¿Cómo prefieres que te contactemos? 📱

Elige la opción que más te convenga:"""
    
    keyboard = [
        [InlineKeyboardButton("📞 Llamada telefónica", callback_data="contact_call")],
        [InlineKeyboardButton("📱 WhatsApp", callback_data="contact_whatsapp")],
        [InlineKeyboardButton("📧 Email", callback_data="contact_email")],
        [InlineKeyboardButton("🔙 Volver al menú", callback_data="menu_main")]
    ]
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@handle_telegram_errors
async def handle_contact_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Maneja la selección del método de contacto."""
    if not update.effective_chat or not update.callback_query:
        return
        
    query = update.callback_query
    
    if callback_data == "contact_call":
        message = """Por favor, envíame tu número de teléfono para que podamos llamarte.
        
📱 Formato: +XX XXXXXXXXXX"""
        
    elif callback_data == "contact_whatsapp":
        message = """Por favor, envíame tu número de WhatsApp.
        
📱 Formato: +XX XXXXXXXXXX"""
        
    elif callback_data == "contact_email":
        message = """Por favor, envíame tu dirección de email.
        
📧 Formato: tu@email.com"""
        
    else:  # menu_main
        await show_main_menu(update, context)
        return
    
    await query.edit_message_text(
        text=message,
        reply_markup=None
    ) 