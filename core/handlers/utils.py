"""
Utility functions for the Telegram bot handlers.
This module contains common helper functions used across different handlers.
"""

import logging
import asyncio
import httpx
import requests
from functools import wraps
from typing import Optional, List, Callable, Any
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram import Message, ReplyKeyboardMarkup

logger = logging.getLogger(__name__)

def handle_telegram_errors(func):
    """Maneja errores de Telegram con reintentos y feedback al usuario."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except httpx.ReadError as e:
                logger.warning(f"Error de conexión Telegram (intento {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Error fatal de conexión Telegram después de {max_retries} intentos")
                    update = args[0] if args else None
                    if update and hasattr(update, 'message') and update.message:
                        try:
                            await update.message.reply_text("⚠️ Error de conexión. Por favor, intenta de nuevo en unos momentos.")
                        except Exception:
                            pass
                    raise
                await asyncio.sleep(1 * (attempt + 1))
            except Exception as e:
                logger.error(f"Error inesperado en {func.__name__}: {e}", exc_info=True)
                update = args[0] if args else None
                if update and hasattr(update, 'message') and update.message:
                    try:
                        await update.message.reply_text("⚠️ Ocurrió un error inesperado. Por favor, intenta de nuevo más tarde.")
                    except Exception:
                        pass
                raise
    return wrapper

def handle_supabase_errors(func: Callable) -> Callable:
    """Maneja errores de Supabase y los registra en el log."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión Supabase en {func.__name__}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado en {func.__name__}: {e}")
            return None
    return wrapper

@handle_telegram_errors
async def send_agent_telegram(update: Update, msg: str, keyboard: Optional[InlineKeyboardMarkup] = None, msg_critico: bool = False) -> None:
    """Sends a message to the user via Telegram. Si msg_critico=True, muestra el teclado pasado; si False, no muestra teclado."""
    if not update.effective_chat:
        logger.error("No se pudo enviar el mensaje, effective_chat es None")
        return
    try:
        if msg_critico:
            await update.effective_chat.send_message(msg, reply_markup=keyboard)
        else:
            await update.effective_chat.send_message(msg)
        logger.debug(f"Mensaje enviado exitosamente a usuario {update.effective_user.id if update.effective_user else 'unknown'}")
    except Exception as e:
        logger.error(f"Error enviando mensaje a Telegram: {e}")
        raise

@handle_telegram_errors
async def send_processing_message(update: Update) -> None:
    """Envía un mensaje de 'procesando' mientras se genera la respuesta."""
    if not update.effective_chat:
        return
    try:
        await update.effective_chat.send_message("🤔 Procesando tu solicitud...")
    except Exception as e:
        logger.warning(f"No se pudo enviar mensaje de procesamiento: {e}")

@handle_telegram_errors
async def edit_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, new_text: str, keyboard: Optional[InlineKeyboardMarkup] = None) -> None:
    """Edita un mensaje existente usando el contexto."""
    try:
        await context.bot.edit_message_text(new_text, chat_id=chat_id, message_id=message_id, reply_markup=keyboard)
    except Exception as e:
        logger.warning(f"No se pudo editar mensaje: {e}")

async def send_grouped_messages(send_func: Callable, update: Update, messages: List[str], keyboard: Optional[InlineKeyboardMarkup] = None, msg_critico: bool = False) -> None:
    """Envía una lista de mensajes en grupo, con el último mensaje usando el teclado si es necesario."""
    if not messages:
        return
    
    # Enviar todos los mensajes excepto el último sin teclado
    for msg in messages[:-1]:
        await send_func(update, msg, None, False)
    
    # Enviar el último mensaje con el teclado si es msg_critico
    await send_func(update, messages[-1], keyboard, msg_critico)

async def send_message_with_keyboard(
    update: Update,
    text: str,
    keyboard: Optional[InlineKeyboardMarkup | ReplyKeyboardMarkup] = None,
    parse_mode: str = 'HTML',
    msg_critico: bool = False
) -> Message:
    """
    Envía un mensaje con teclado opcional.
    
    Args:
        update: Update de Telegram
        text: Texto del mensaje
        keyboard: Teclado inline o reply opcional
        parse_mode: Modo de parseo del texto
        msg_critico: Si es True, siempre muestra el teclado
        
    Returns:
        Message: Mensaje enviado
    """
    if not update.effective_chat:
        logger.error("No se pudo enviar el mensaje, effective_chat es None")
        raise ValueError("effective_chat is None")

    try:
        if msg_critico or keyboard:
            return await update.effective_chat.send_message(
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        else:
            return await update.effective_chat.send_message(
                text=text,
                parse_mode=parse_mode
            )
    except Exception as e:
        logger.error(f"Error enviando mensaje a Telegram: {e}")
        raise

def validate_email(email: str) -> bool:
    """Valida el formato de un correo electrónico."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Valida un número de teléfono."""
    return len(phone.strip()) >= 8 and any(c.isdigit() for c in phone) 

def detect_negative_feedback(text: str) -> bool:
    """Detecta feedback negativo en el texto del usuario."""
    negative_words = [
        "no me gusta", "malo", "pésimo", "terrible", "horrible",
        "no funciona", "error", "problema", "mal", "peor",
        "no sirve", "inútil", "basura", "pésima", "horrible",
        "no entiendo", "confuso", "difícil", "complicado"
    ]
    text_lower = text.lower()
    return any(word in text_lower for word in negative_words) 