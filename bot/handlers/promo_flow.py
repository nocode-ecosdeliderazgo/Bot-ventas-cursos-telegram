"""
Promotions flow handlers for the Telegram bot.
This module handles all promotion-related interactions.
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from typing import List, Dict, Any
from ..services import get_promotions, get_courses
from ..keyboards import create_courses_list_keyboard, create_contextual_cta_keyboard
from .utils import handle_telegram_errors, send_agent_telegram

logger = logging.getLogger(__name__)

@handle_telegram_errors
async def mostrar_promociones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra las promociones disponibles."""
    promos = get_promotions()
    user_id_str = str(update.effective_user.id) if update.effective_user else ""
    
    if promos:
        promo_text = "💰 **Promociones especiales:**\n\n"
        for promo in promos:
            promo_text += f"🎁 **{promo['name']}**\n"
            promo_text += f"{promo['description']}\n"
            if promo.get('expiry_date'):
                promo_text += f"⏰ Válido hasta: {promo['expiry_date']}\n"
            promo_text += "\n"
        
        keyboard = create_contextual_cta_keyboard("promo", user_id_str)
        if isinstance(keyboard, InlineKeyboardMarkup):
            await send_agent_telegram(update, promo_text, keyboard, msg_critico=True)
        else:
            await send_agent_telegram(update, promo_text, None, msg_critico=True)
    else:
        await send_agent_telegram(
            update,
            "Lo siento, no hay promociones disponibles en este momento. ¿Te gustaría ver nuestros cursos?",
            create_courses_list_keyboard(get_courses()),
            msg_critico=True
        )

@handle_telegram_errors
async def forzar_seleccion_curso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fuerza la selección de un curso antes de mostrar promociones."""
    cursos = get_courses()
    if cursos:
        keyboard = create_courses_list_keyboard(cursos)
        if isinstance(keyboard, InlineKeyboardMarkup):
            await send_agent_telegram(
                update,
                "Para mostrarte las mejores promociones, primero selecciona el curso que te interesa:",
                keyboard,
                msg_critico=True
            )
        else:
            await send_agent_telegram(
                update,
                "Para mostrarte las mejores promociones, primero selecciona el curso que te interesa:",
                None,
                msg_critico=True
            )
    else:
        await send_agent_telegram(
            update,
            "Lo siento, no hay cursos disponibles en este momento.",
            None,
            msg_critico=True
        ) 