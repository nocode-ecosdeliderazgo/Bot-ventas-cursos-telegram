"""
FAQ flow handlers for the Telegram bot.
This module handles all FAQ-related interactions.
"""

import os
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from .utils import handle_telegram_errors, send_agent_telegram, send_grouped_messages
import logging

logger = logging.getLogger(__name__)

def generar_faq_contexto(pregunta_idx: int) -> str:
    """Genera el contexto para una pregunta FAQ específica."""
    try:
        faq_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "plantillas.json"))
        with open(faq_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            plantillas = data.get("preguntas_frecuentes", [])
        
        if 0 <= pregunta_idx < len(plantillas):
            plantilla = plantillas[pregunta_idx]
            return f"❓ {plantilla['pregunta']}\n\n{plantilla['respuesta']}"
        else:
            return "No se encontró la pregunta solicitada."
    except Exception as e:
        logger.error(f"Error al generar contexto FAQ: {e}")
        return "Lo siento, hubo un error al cargar las preguntas frecuentes."

@handle_telegram_errors
async def mostrar_menu_faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el menú de preguntas frecuentes."""
    try:
        faq_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "plantillas.json"))
        with open(faq_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            plantillas = data.get("preguntas_frecuentes", [])
        
        keyboard_buttons = []
        for i, plantilla in enumerate(plantillas):
            keyboard_buttons.append([InlineKeyboardButton(
                f"❓ {plantilla['pregunta'][:50]}...",
                callback_data=f"faq_q_{i}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton("🏠 Volver al inicio", callback_data="menu_principal")])
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await send_agent_telegram(
            update,
            "🤔 Preguntas Frecuentes\n\nSelecciona una pregunta para ver la respuesta:",
            keyboard,
            msg_critico=True
        )
    except Exception as e:
        logger.error(f"Error al mostrar menú FAQ: {e}")
        await send_agent_telegram(
            update,
            "Lo siento, hubo un error al cargar las preguntas frecuentes.",
            None
        )

@handle_telegram_errors
async def mostrar_respuesta_faq(update: Update, context: ContextTypes.DEFAULT_TYPE, pregunta_idx: int) -> None:
    """Muestra la respuesta a una pregunta específica del FAQ."""
    try:
        respuesta = generar_faq_contexto(pregunta_idx)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ Volver a FAQ", callback_data="faq")],
            [InlineKeyboardButton("🏠 Volver al inicio", callback_data="menu_principal")]
        ])
        
        await send_grouped_messages(
            send_agent_telegram,
            update,
            [respuesta],
            keyboard,
            msg_critico=True
        )
    except Exception as e:
        logger.error(f"Error al mostrar respuesta FAQ: {e}")
        await send_agent_telegram(
            update,
            "Lo siento, hubo un error al mostrar la respuesta.",
            None
        ) 