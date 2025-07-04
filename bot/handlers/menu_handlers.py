"""
Menu handlers for the Telegram bot.
This module handles the main menu and basic interactions.
"""

import logging
import time
import os
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
    send_message_with_keyboard,
    send_grouped_messages
)
from .course_flow import mostrar_lista_cursos, mostrar_menu_curso_exploracion
from .faq_flow import mostrar_menu_faq, generar_faq_contexto, mostrar_respuesta_faq
from .contact_flow import contact_advisor_flow, contactar_asesor, editar_datos_contacto
from .promo_flow import mostrar_promociones
from .auth_flow import (
    ensure_privacy,
    send_privacy_notice,
    show_full_privacy_notice,
    handle_privacy_response,
    redirect_to_main_menu,
    start_command
)

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

async def reiniciar_conversacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reinicia la conversación eliminando el archivo de memoria y llamando a start_command."""
    if not update.effective_user:
        return
    
    user_id_str = str(update.effective_user.id)
    memory_file = f"memorias/memory_{user_id_str}.json"
    
    # Eliminar archivo de memoria si existe
    try:
        if os.path.exists(memory_file):
            os.remove(memory_file)
            logger.info(f"Archivo de memoria eliminado para usuario {user_id_str}")
    except Exception as e:
        logger.error(f"Error eliminando archivo de memoria para usuario {user_id_str}: {e}")
    
    # Reiniciar memoria en el contexto
    context.bot_data['global_mem'] = Memory()
    context.bot_data['global_user_id'] = None
    
    # Reiniciar conversación
    await start_command(update, context)

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

    # Manejar comando de reinicio desde texto
    if user_input == "🔄 Reiniciar Conversación":
        await reiniciar_conversacion(update, context)
        return

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
            
            # Verificar si el usuario viene de un anuncio
            from_ad = bool(getattr(context.bot_data['global_mem'].lead_data, 'source', None) and 
                         str(context.bot_data['global_mem'].lead_data.source).startswith('ad_'))
            await redirect_to_main_menu(update, context, from_ad)
        else:
            await send_grouped_messages(
                send_agent_telegram,
                update,
                ["Por favor, ingresa un nombre válido (solo letras y espacios). ¿Cómo te gustaría que te llame? 😊"],
                None,
                msg_critico=True
            )
        return

    # Procesar mensaje con OpenAI y obtener respuesta contextual
    processing_msg = None
    if len(user_input) > 20 or any(word in user_input.lower() for word in ['curso', 'precio', 'módulos', 'comprar', 'promoción']):
        processing_msg = await send_message_with_keyboard(
            update,
            "🤔 Procesando tu solicitud...",
            None
        )

    try:
        response_data = openai_intent_and_response(user_input, "")
        # Guardar historial
        if context.bot_data['global_mem'].lead_data.email:
            history_entry = {
                "user_input": user_input,
                "bot_reply": response_data["response"],
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

        # Enviar respuesta con teclado contextual
        keyboard = create_contextual_cta_keyboard(context_type, user_id_str)
        if processing_msg:
            await processing_msg.delete()
        await send_grouped_messages(send_agent_telegram, update, [response_data["response"]], keyboard, msg_critico=True)

    except Exception as e:
        logger.error(f"Error procesando mensaje: {str(e)}")
        if processing_msg:
            await processing_msg.delete()
        await send_grouped_messages(
            send_agent_telegram,
            update,
            ["Lo siento, tuve un problema procesando tu mensaje. ¿Podrías reformularlo?"],
            create_main_inline_keyboard(),
            msg_critico=True
        )

@handle_telegram_errors
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las interacciones con botones inline."""
    if not update.callback_query or not update.callback_query.data:
        return
    
    query = update.callback_query
    callback_data = str(query.data)  # Asegurar que sea string

    try:
        # Manejar callbacks de privacidad
        if callback_data == "privacy_accept":
            await query.answer("Gracias por aceptar")
            await handle_privacy_response(update, context, True)
            return
        elif callback_data == "privacy_view":
            await query.answer("Mostrando aviso completo")
            await show_full_privacy_notice(update)
            return
        elif callback_data == "privacy_back":
            await query.answer("Volviendo al aviso principal")
            await send_privacy_notice(update, context)
            return

        # Manejar callbacks del menú principal
        if callback_data in ["ver_cursos", "faq", "contacto", "promociones"]:
            await query.answer()
            await handle_menu_selection(update, context, callback_data)
            return
        elif callback_data == "reiniciar":
            await query.answer("Reiniciando conversación...")
            await reiniciar_conversacion(update, context)
            return
        elif callback_data == "menu_principal":
            await query.answer()
            await show_main_menu(update, context)
            return

        # Manejar callbacks de cursos
        if callback_data.startswith("course_"):
            curso_id = callback_data.split("_")[1]
            await query.answer()
            await mostrar_menu_curso_exploracion(update, context, curso_id)
            return
        elif any(callback_data.startswith(prefix) for prefix in ["modules_", "duration_", "price_", "buy_"]):
            curso_id = callback_data.split("_")[1]
            await query.answer()
            await mostrar_menu_curso_exploracion(update, context, curso_id)
            return

        # Otros callbacks
        await query.answer()
        if callback_data.startswith("promo_"):
            await mostrar_promociones(update, context)
        elif callback_data == "contactar_asesor":
            await contactar_asesor(update, context)
        elif callback_data == "editar_datos":
            await editar_datos_contacto(update, context)
        else:
            logger.warning(f"Callback no manejado: {callback_data}")
            await show_main_menu(update, context)

    except Exception as e:
        logger.error(f"Error manejando callback: {str(e)}")
        await query.answer("Hubo un error. Por favor, intenta de nuevo.")
        await show_main_menu(update, context) 