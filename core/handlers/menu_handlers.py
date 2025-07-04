"""
Menu handlers for the Telegram bot.
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from typing import Optional
from .utils import send_agent_telegram, handle_telegram_errors

logger = logging.getLogger(__name__)

@handle_telegram_errors
async def mostrar_menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el menú principal del bot."""
    keyboard = [
        [InlineKeyboardButton("📚 Ver Cursos", callback_data="ver_cursos")],
        [InlineKeyboardButton("💰 Ver Promociones", callback_data="promociones")],
        [InlineKeyboardButton("❓ FAQ", callback_data="faq")],
        [InlineKeyboardButton("👨‍💼 Hablar con Asesor", callback_data="contacto")],
        [InlineKeyboardButton("🔄 Reiniciar Conversación", callback_data="reiniciar")]
    ]
    
    await send_agent_telegram(
        update,
        "¿En qué puedo ayudarte hoy?",
        InlineKeyboardMarkup(keyboard),
        msg_critico=True
    )

@handle_telegram_errors
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los callbacks de los botones inline."""
    if not update.callback_query:
        return
    
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    if not callback_data:
        logger.warning("Callback sin datos")
        return
    
    logger.debug(f"Callback recibido: {callback_data}")
    
    try:
        # === Callbacks de FAQ ===
        if callback_data == "faq":
            from .faq_flow import mostrar_faq
            await mostrar_faq(update, context)
            return
        
        if callback_data.startswith("faq_q_"):
            from .faq_flow import responder_faq
            template_idx = int(callback_data.split("_")[2])
            await responder_faq(update, context, template_idx)
            return
        
        if callback_data.startswith("faq_select_course_"):
            from .faq_flow import mostrar_cursos_para_faq
            template_idx = int(callback_data.split("_")[3])
            await mostrar_cursos_para_faq(update, context, template_idx)
            return
        
        if callback_data.startswith("faq_course_"):
            from .faq_flow import responder_faq
            parts = callback_data.split("_")
            template_idx = int(parts[2])
            course_id = parts[3]
            await responder_faq(update, context, template_idx, course_id)
            return
        
        # === Callbacks de Cursos ===
        if callback_data == "ver_cursos":
            from .course_flow import mostrar_lista_cursos
            await mostrar_lista_cursos(update, context)
            return
        
        if callback_data.startswith("course_"):
            from .course_flow import mostrar_menu_curso_exploracion
            course_id = callback_data.split("_")[1]
            await mostrar_menu_curso_exploracion(update, context, course_id)
            return
        
        if any(callback_data.startswith(prefix) for prefix in ["modules_", "duration_", "price_", "buy_"]):
            from .course_flow import mostrar_menu_curso_exploracion
            course_id = callback_data.split("_")[1]
            await mostrar_menu_curso_exploracion(update, context, course_id)
            return
        
        # === Callbacks de Promociones ===
        if callback_data == "promociones":
            from .promo_flow import mostrar_promociones
            await mostrar_promociones(update, context)
            return
        
        # === Callbacks de Contacto ===
        if callback_data == "contacto":
            from .contact_flow import contact_advisor_flow
            await contact_advisor_flow(update, context)
            return
        
        # === Callbacks de Menú Principal ===
        if callback_data == "cta_inicio" or callback_data == "menu_principal":
            await mostrar_menu_principal(update, context)
            return
        
        # === Callback no manejado ===
        logger.warning(f"Callback no manejado: {callback_data}")
        await mostrar_menu_principal(update, context)
        
    except Exception as e:
        logger.error(f"Error manejando callback {callback_data}: {e}")
        await send_agent_telegram(
            update,
            "Lo siento, hubo un error procesando tu selección. Por favor, intenta nuevamente.",
            None
        ) 