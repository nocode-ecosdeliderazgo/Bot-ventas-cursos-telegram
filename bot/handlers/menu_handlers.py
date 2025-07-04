"""
Menu handlers for the Telegram bot.
This module handles the main menu and basic interactions.
"""

import logging
import time
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Optional, List, Dict, Any, Union, cast
from ..memory import Memory
from ..services import openai_intent_and_response, get_interest_score, UMBRAL_PROMO
from ..keyboards import (
    create_main_keyboard,
    create_main_inline_keyboard,
    create_contextual_cta_keyboard
)
from .utils import (
    handle_telegram_errors,
    send_agent_telegram,
    send_processing_message,
    send_grouped_messages
)
from .course_flow import mostrar_lista_cursos, mostrar_menu_curso_exploracion
from .faq_flow import mostrar_menu_faq, generar_faq_contexto
from .contact_flow import contact_advisor_flow, contactar_asesor, editar_datos_contacto
from .promo_flow import mostrar_promociones
from .auth_flow import ensure_privacy, send_privacy_notice, show_full_privacy_notice

logger = logging.getLogger(__name__)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el menú principal con ambos tipos de teclado."""
    user_id_str = str(update.effective_user.id) if update.effective_user else "unknown"
    welcome_msg = (
        f"¡Hola {context.bot_data['global_mem'].lead_data.name}! 👋\n\n"
        "¿Qué te gustaría aprender sobre Inteligencia Artificial? "
        "Tenemos cursos de IA práctica, prompts, generación de imágenes y más."
    )
    keyboard_main = create_main_keyboard()
    keyboard_inline = create_main_inline_keyboard()
    
    # Enviar mensaje principal sin teclado inline
    await send_agent_telegram(update, welcome_msg, None, msg_critico=True)
    
    # Enviar teclado inline por separado
    if isinstance(keyboard_inline, InlineKeyboardMarkup):
        await send_agent_telegram(update, "Menú principal:", keyboard_inline, msg_critico=True)

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, selection: str) -> None:
    """Maneja la selección de opciones del menú principal."""
    menu_handlers = {
        "ver_cursos": mostrar_lista_cursos,
        "faq": mostrar_menu_faq,
        "contacto": contact_advisor_flow,
        "promociones": mostrar_promociones
    }
    
    handler = menu_handlers.get(selection)
    if handler:
        await handler(update, context)
    else:
        logger.warning(f"Opción de menú no reconocida: {selection}")
        await show_main_menu(update, context)

@handle_telegram_errors
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start, verifica privacidad y muestra menú principal."""
    if not update.effective_user:
        logger.error("Usuario efectivo es None en start_command")
        return
    user_id_str = str(update.effective_user.id)
    logger.info(f"Comando /start recibido de usuario {user_id_str}")

    # Ensure memory is loaded for this specific user
    if 'global_user_id' not in context.bot_data:
        context.bot_data['global_user_id'] = None
    if 'global_mem' not in context.bot_data:
        context.bot_data['global_mem'] = Memory()
    if context.bot_data['global_user_id'] != user_id_str or not context.bot_data['global_mem'].lead_data.user_id:
        context.bot_data['global_user_id'] = user_id_str
        context.bot_data['global_mem'] = Memory()
        context.bot_data['global_mem'].load(context.bot_data['global_user_id'])
        context.bot_data['global_mem'].lead_data.user_id = user_id_str
        if not context.bot_data['global_mem'].lead_data.user_id:
            context.bot_data['global_mem'].lead_data.user_id = user_id_str
            context.bot_data['global_mem'].lead_data.stage = "inicio"
            context.bot_data['global_mem'].save()

    # Verificar si ya aceptó la privacidad
    if not ensure_privacy(update, context):
        logger.info(f"Usuario {user_id_str} no ha aceptado privacidad, mostrando aviso")
        await send_privacy_notice(update, context)
        return

    # Si ya aceptó privacidad, continuar con el flujo normal
    if not context.bot_data['global_mem'].lead_data.name:
        welcome_text = "¡Perfecto! 👋 Ahora puedo ayudarte mejor."
        question_text = "¿Cómo te gustaría que te llame? 😊"
        await send_grouped_messages(send_agent_telegram, update, [welcome_text, question_text], None, msg_critico=True)
        context.bot_data['global_mem'].lead_data.stage = "awaiting_name"
        context.bot_data['global_mem'].save()
        return

    # Si ya tiene nombre, mostrar menú principal
    welcome_msg = (
        f"¡Hola {context.bot_data['global_mem'].lead_data.name or 'amigo'}! 👋\n\n"
        "¿Qué te gustaría aprender sobre Inteligencia Artificial? "
        "Tenemos cursos de IA práctica, prompts, generación de imágenes y más."
    )
    keyboard = create_contextual_cta_keyboard("default", user_id_str)
    if isinstance(keyboard, InlineKeyboardMarkup):
        await send_grouped_messages(send_agent_telegram, update, [welcome_msg], keyboard, msg_critico=True)
    else:
        await send_grouped_messages(send_agent_telegram, update, [welcome_msg], None, msg_critico=True)
    context.bot_data['global_mem'].save()

@handle_telegram_errors
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa mensajes de usuario y maneja el flujo de conversación."""
    if not update.message or not update.message.text:
        logger.warning("Mensaje o texto del mensaje es None")
        return
    if not update.effective_user:
        logger.error("Usuario efectivo es None")
        return

    user_input = update.message.text
    user_id_str = str(update.effective_user.id)
    logger.info(f"Mensaje recibido de usuario {user_id_str}: '{user_input[:50]}...'")

    # Ensure memory is loaded
    if 'global_user_id' not in context.bot_data:
        context.bot_data['global_user_id'] = None
    if 'global_mem' not in context.bot_data:
        context.bot_data['global_mem'] = Memory()
    if context.bot_data['global_user_id'] != user_id_str or not context.bot_data['global_mem'].lead_data.user_id:
        context.bot_data['global_user_id'] = user_id_str
        context.bot_data['global_mem'] = Memory()
        context.bot_data['global_mem'].load(context.bot_data['global_user_id'])
        context.bot_data['global_mem'].lead_data.user_id = user_id_str
        if not context.bot_data['global_mem'].lead_data.user_id:
            context.bot_data['global_mem'].lead_data.user_id = user_id_str
            context.bot_data['global_mem'].lead_data.stage = "inicio"
            context.bot_data['global_mem'].save()

    # Verificar privacidad
    if not ensure_privacy(update, context):
        await send_privacy_notice(update, context)
        return

    # Procesar el mensaje según el estado actual
    if context.bot_data['global_mem'].lead_data.stage == "awaiting_name":
        nombre = user_input.strip()
        if len(nombre) > 1 and all(x.isalpha() or x.isspace() for x in nombre):
            context.bot_data['global_mem'].lead_data.name = nombre.title()
            context.bot_data['global_mem'].lead_data.stage = "info"
            context.bot_data['global_mem'].save()
            mensaje_bienvenida = (
                f"¡Gracias, {context.bot_data['global_mem'].lead_data.name}! 🎉 Ahora sí, dime ¿qué te gustaría aprender sobre Inteligencia Artificial? "
                "Tenemos cursos prácticos, generación de imágenes, prompts y mucho más para que lleves tu conocimiento al siguiente nivel."
            )
            keyboard_inline = create_main_inline_keyboard()
            if isinstance(keyboard_inline, InlineKeyboardMarkup):
                await send_grouped_messages(send_agent_telegram, update, [mensaje_bienvenida], keyboard_inline, msg_critico=True)
            else:
                await send_grouped_messages(send_agent_telegram, update, [mensaje_bienvenida], None, msg_critico=True)
        else:
            await send_grouped_messages(send_agent_telegram, update, ["Por favor, ingresa un nombre válido (solo letras y espacios)."], None, msg_critico=True)
        return

    # Procesar mensaje con OpenAI y obtener respuesta contextual
    processing_msg = None
    if len(user_input) > 20 or any(word in user_input.lower() for word in ['curso', 'precio', 'módulos', 'comprar', 'promoción']):
        processing_msg = await send_processing_message(update)

    try:
        bot_reply = openai_intent_and_response(user_input, "")
        # Guardar historial
        if context.bot_data['global_mem'].lead_data.email:
            history_entry = {
                "user_input": user_input,
                "bot_reply": bot_reply,
                "timestamp": time.time()
            }
            context.bot_data['global_mem'].history.append(history_entry)
            context.bot_data['global_mem'].save()

        # Determinar el tipo de contexto para los CTAs
        context_type = "default"
        if context.bot_data['global_mem'].lead_data.selected_course:
            context_type = "course_selected"
        if any(word in user_input.lower() for word in ['precio', 'costo', 'cuánto', 'cuanto', 'pagar']):
            context_type = "pricing_inquiry"
        interest_score = get_interest_score(user_id_str) or 0
        if interest_score >= UMBRAL_PROMO:
            context_type = "purchase_intent"
        if interest_score >= 30:
            context_type = "high_interest"

        keyboard = create_contextual_cta_keyboard(context_type, user_id_str)
        if isinstance(keyboard, InlineKeyboardMarkup):
            await send_grouped_messages(send_agent_telegram, update, [str(bot_reply)], keyboard, msg_critico=True)
        else:
            await send_grouped_messages(send_agent_telegram, update, [str(bot_reply)], None, msg_critico=True)

    except Exception as e:
        logger.error(f"Error procesando mensaje del usuario {user_id_str}: {e}", exc_info=True)
        error_msg = "Lo siento, hubo un problema técnico. ¿Te gustaría que un asesor humano te contacte?"
        keyboard = create_contextual_cta_keyboard("error", user_id_str)
        if isinstance(keyboard, InlineKeyboardMarkup):
            await send_grouped_messages(send_agent_telegram, update, [error_msg], keyboard, msg_critico=True)
        else:
            await send_grouped_messages(send_agent_telegram, update, [error_msg], None, msg_critico=True)

@handle_telegram_errors
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las respuestas a botones interactivos."""
    query = update.callback_query
    if not query:
        logger.warning("Callback query es None")
        return

    await query.answer()  # Acknowledge the callback

    if not query.data:
        return

    user_id_str = str(query.from_user.id)
    logger.info(f"Callback recibido de usuario {user_id_str}: {query.data}")

    # Ensure memory is loaded
    if 'global_user_id' not in context.bot_data:
        context.bot_data['global_user_id'] = None
    if 'global_mem' not in context.bot_data:
        context.bot_data['global_mem'] = Memory()
    if context.bot_data['global_user_id'] != user_id_str or not context.bot_data['global_mem'].lead_data.user_id:
        context.bot_data['global_user_id'] = user_id_str
        context.bot_data['global_mem'] = Memory()
        context.bot_data['global_mem'].load(context.bot_data['global_user_id'])
        context.bot_data['global_mem'].lead_data.user_id = user_id_str
        if not context.bot_data['global_mem'].lead_data.user_id:
            context.bot_data['global_mem'].lead_data.user_id = user_id_str
            context.bot_data['global_mem'].lead_data.stage = "inicio"
            context.bot_data['global_mem'].save()

    # Procesar el callback según el tipo
    try:
        # Manejo de privacidad
        if query.data == "privacy_accept":
            context.bot_data['global_mem'].lead_data.privacy_accepted = True
            context.bot_data['global_mem'].save()
            if not context.bot_data['global_mem'].lead_data.name:
                welcome_text = "¡Perfecto! 👋 Ahora puedo ayudarte mejor."
                question_text = "¿Cómo te gustaría que te llame? 😊"
                await send_grouped_messages(send_agent_telegram, update, [welcome_text, question_text], None, msg_critico=True)
                context.bot_data['global_mem'].lead_data.stage = "awaiting_name"
                context.bot_data['global_mem'].save()
            else:
                await show_main_menu(update, context)
        elif query.data == "privacy_view":
            await show_full_privacy_notice(update)
            return

        # Manejo del menú principal
        elif query.data == "cta_ver_cursos":
            await mostrar_lista_cursos(update, context)
        elif query.data == "cta_promociones":
            await mostrar_promociones(update, context)
        elif query.data == "cta_faq":
            await mostrar_menu_faq(update, context)
        elif query.data == "cta_asesor":
            await contact_advisor_flow(update, context)
        elif query.data == "cta_reiniciar":
            await start_command(update, context)
        elif query.data == "cta_inicio":
            await show_main_menu(update, context)

        # Manejo de cursos
        elif query.data.startswith("course_"):
            course_id = query.data.split("_")[1]
            await mostrar_menu_curso_exploracion(update, context, course_id)
        elif query.data.startswith("modules_"):
            course_id = query.data.split("_")[1]
            await mostrar_menu_curso_exploracion(update, context, course_id)
        elif query.data.startswith("info_"):
            course_id = query.data.split("_")[1]
            await mostrar_menu_curso_exploracion(update, context, course_id)
        elif query.data.startswith("buy_course_"):
            course_id = query.data.split("_")[2]
            await mostrar_menu_curso_exploracion(update, context, course_id)
        elif query.data == "change_course":
            await mostrar_lista_cursos(update, context)

        # Si no se reconoce el callback, mostrar menú principal
        else:
            logger.warning(f"Callback no reconocido: {query.data}")
            await show_main_menu(update, context)

    except Exception as e:
        logger.error(f"Error procesando callback {query.data}: {e}", exc_info=True)
        error_msg = "Lo siento, hubo un problema técnico. ¿Te gustaría que un asesor humano te contacte?"
        keyboard = create_contextual_cta_keyboard("error", user_id_str)
        if isinstance(keyboard, InlineKeyboardMarkup):
            await send_grouped_messages(send_agent_telegram, update, [error_msg], keyboard, msg_critico=True)
        else:
            await send_grouped_messages(send_agent_telegram, update, [error_msg], None, msg_critico=True) 