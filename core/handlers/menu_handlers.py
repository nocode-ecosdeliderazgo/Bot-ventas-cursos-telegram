"""Manejadores de menús del bot."""
import logging
from typing import Optional
from telegram import Update, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes

from core.utils.error_handlers import handle_telegram_errors
from core.utils.memory import GlobalMemory
from core.utils.message_templates import create_menu_message, create_menu_keyboard
from core.utils.navigation import show_main_menu

logger = logging.getLogger(__name__)

@handle_telegram_errors
async def mostrar_menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

@handle_telegram_errors
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las respuestas a los botones del menú."""
    if not update.callback_query or not update.effective_user:
        logger.error("Callback query o effective_user es None")
        return
        
    query: CallbackQuery = update.callback_query
    callback_data: str = query.data if query.data else ""
    user_id = update.effective_user.id
    
    try:
        # Confirmar recepción del callback
        await query.answer()
        
        # Manejar diferentes tipos de callbacks
        if callback_data.startswith("menu_"):
            if callback_data == "menu_main":
                await show_main_menu(update, context)
            else:
                await handle_menu_callback(update, context, callback_data)
        elif callback_data.startswith("privacy_"):
            await handle_privacy_callback(update, context, callback_data)
        elif callback_data.startswith("course_"):
            await handle_course_callback(update, context, callback_data)
        elif callback_data.startswith("contact_"):
            await handle_contact_callback(update, context, callback_data)
        else:
            logger.warning(f"Callback no manejado: {callback_data}")
            await show_main_menu(update, context)
            
    except Exception as e:
        logger.error(f"Error manejando callback query: {e}")
        raise

@handle_telegram_errors
async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Maneja los callbacks del menú principal."""
    if not update.effective_chat:
        await show_main_menu(update, context)
        return
        
    if callback_data == "menu_courses":
        from core.handlers.course_flow import show_courses
        await show_courses(update, context)
    elif callback_data == "menu_contact":
        from core.handlers.contact_flow import show_contact_options
        await show_contact_options(update, context)
    elif callback_data == "menu_faq":
        from core.handlers.faq_flow import show_faq
        await show_faq(update, context)
    elif callback_data == "menu_privacy":
        from core.handlers.privacy_flow import show_privacy_policy
        await show_privacy_policy(update, context)
    else:
        await show_main_menu(update, context)

@handle_telegram_errors
async def handle_privacy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Maneja los callbacks de la política de privacidad."""
    if not update.effective_chat:
        await show_main_menu(update, context)
        return
        
    from core.handlers.privacy_flow import handle_privacy_response
    await handle_privacy_response(update, context, callback_data)

@handle_telegram_errors
async def handle_course_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Maneja los callbacks relacionados con cursos."""
    if not update.effective_chat:
        await show_main_menu(update, context)
        return
        
    from core.handlers.course_flow import handle_course_selection
    await handle_course_selection(update, context, callback_data)

@handle_telegram_errors
async def handle_contact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Maneja los callbacks de contacto."""
    if not update.effective_chat:
        await show_main_menu(update, context)
        return
        
    from core.handlers.contact_flow import handle_contact_selection
    await handle_contact_selection(update, context, callback_data) 