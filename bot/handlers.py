# ==============================
# HANDLERS PRINCIPALES DEL BOT DE TELEGRAM
# ==============================
# Este módulo contiene los decoradores de manejo de errores, los handlers de comandos y mensajes,
# y los helpers de integración con la lógica de negocio y memoria.

import os
import json
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from functools import wraps
import asyncio
import httpx
import requests
import re
import time
from typing import Optional, List, Dict, Any
from config.settings import settings
from .memory import Memory
from .keyboards import (
    create_main_keyboard, create_main_inline_keyboard, create_courses_list_keyboard, create_contextual_cta_keyboard, create_course_selection_keyboard, create_course_explore_keyboard
)
from .services import (
    get_courses, get_course_detail, get_modules, get_promotions, notify_advisor_contact_request, openai_intent_and_response, save_lead, notify_advisor_reservation_request, get_interest_score, UMBRAL_PROMO
)
from .utils import send_grouped_messages, detect_negative_feedback
from .faq import generar_faq_contexto
import logging

logger = logging.getLogger(__name__)

# ==============================
# ERROR HANDLING DECORATORS
# ==============================
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

def handle_supabase_errors(func):
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

# ==============================
# FUTURE INTEGRATIONS (just markers for now)
# ==============================
# DONE: Integrate with python-telegram-bot for Telegram interface
# TODO: Integrate with Stripe API for payments and mark purchase as "paid"
# TODO: Add LLM-powered personalized sales flows (already partially done below)
# TODO: Store conversations/user state in DB for multidevice/multi-session memory

def ensure_privacy(update, context) -> bool:
    """Verifica si el usuario ya aceptó la privacidad."""
    return getattr(context.bot_data['global_mem'].lead_data, 'privacy_accepted', False)

async def send_privacy_notice(update, context=None) -> None:
    """Envía el aviso de privacidad con botones de aceptación."""
    privacy_text = (
        "🔒 **Aviso de Privacidad**\n\n"
        "Para continuar, necesito que aceptes nuestro aviso de privacidad:\n\n"
        "• Recopilamos tu nombre, email y teléfono para brindarte información sobre nuestros cursos\n"
        "• Tus datos se utilizan únicamente para comunicación relacionada con nuestros servicios\n"
        "• No compartimos tu información con terceros sin tu consentimiento\n"
        "• Puedes solicitar la eliminación de tus datos en cualquier momento\n\n"
        "¿Aceptas que procesemos tus datos según este aviso?"
    )
    privacy_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Acepto y continúo", callback_data="privacy_accept")],
        [InlineKeyboardButton("🔒 Ver Aviso Completo", callback_data="privacy_view")]
    ])
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(privacy_text, reply_markup=privacy_keyboard, parse_mode='Markdown')
    elif hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(privacy_text, reply_markup=privacy_keyboard, parse_mode='Markdown')

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
        await send_agent_telegram(update, welcome_text, None, msg_critico=True)
        await send_agent_telegram(update, question_text, None, msg_critico=True)
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
    await send_agent_telegram(update, welcome_msg, keyboard, msg_critico=True)
    context.bot_data['global_mem'].save()

@handle_telegram_errors
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa mensajes de usuario de forma robusta, con manejo de sesión, validaciones y CTAs contextuales."""
    if not update.message or not update.message.text:
        logger.warning("Mensaje o texto del mensaje es None")
        return
    if not update.effective_user:
        logger.error("Usuario efectivo es None")
        return

    user_input = update.message.text
    user_id_str = str(update.effective_user.id)
    logger.info(f"Mensaje recibido de usuario {user_id_str}: '{user_input[:50]}...'")

    # Cada vez que el usuario regrese al menú de inicio (por ejemplo, tras Reiniciar Conversación o pulsar un botón de inicio), muestra ambos menús igual
    # Ejemplo para el flujo de reinicio:
    if user_input.strip() == "🔄 Reiniciar Conversación":
        user_memory_file = os.path.join("memorias", f"memory_{user_id_str}.json")
        if os.path.exists(user_memory_file):
            os.remove(user_memory_file)
        context.bot_data['global_mem'] = Memory()
        context.bot_data['global_mem'].load(user_id_str)
        context.bot_data['global_mem'].lead_data.user_id = user_id_str
        context.bot_data['global_mem'].lead_data.stage = "inicio"
        context.bot_data['global_mem'].save()
        await send_agent_telegram(update, "¡Conversación reiniciada!", create_main_keyboard(), msg_critico=True)
        await send_agent_telegram(update, "Menú principal:", create_main_inline_keyboard(), msg_critico=True)
        await send_privacy_notice(update, context)
        return

    # Si el usuario pide ver todos los cursos, resetea el curso seleccionado
    if user_input.strip().lower() == 'ver todos los cursos':
        context.bot_data['global_mem'].lead_data.selected_course = None
        context.bot_data['global_mem'].save()

    # --- NUEVO: Mapeo de intenciones a flujos de botones ---
    input_lower = user_input.strip().lower()
    # Frases exactas
    if input_lower in ["ver todos los cursos", "ver cursos", "cursos", "lista de cursos", "quiero ver cursos"]:
        await send_processing_message(update)
        cursos = get_courses()
        if cursos:
            keyboard = create_courses_list_keyboard(cursos)
            await send_grouped_messages(send_agent_telegram, update, ["Te muestro todos los cursos disponibles:"], keyboard, msg_critico=True)
        else:
            await send_agent_telegram(update, "Por el momento no hay cursos disponibles.")
        return
    elif input_lower in ["hablar con asesor", "asesor", "contactar asesor", "quiero hablar con asesor"]:
        await contact_advisor_flow(update, context)
        return
    elif input_lower in ["ver promociones", "promociones", "descuentos", "ver descuentos", "💰 promociones", "💰 promociones"]:
        # Usar el mismo flujo que el callback 'cta_promociones'
        promos = get_promotions()
        if promos:
            promo_text = "💰 **Promociones especiales:**\n\n"
            for promo in promos:
                promo_text += f"🎁 **{promo['name']}**\n"
                promo_text += f"{promo['description']}\n"
                if promo.get('code'):
                    promo_text += f"Código: `{promo['code']}`\n"
                promo_text += "\n"
            keyboard = create_contextual_cta_keyboard("pricing_inquiry", user_id_str)
            await send_grouped_messages(send_agent_telegram, update, [promo_text], keyboard, msg_critico=True)
        else:
            await send_agent_telegram(update, "Por el momento no hay promociones activas, pero puedes contactar a un asesor para consultar descuentos especiales.", create_contextual_cta_keyboard("default", user_id_str))
        return
    elif input_lower in ["preguntas frecuentes", "faq", "❓ preguntas frecuentes"]:
        faq_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "plantillas.json"))
        with open(faq_path, "r", encoding="utf-8") as f:
            plantillas = json.load(f)
        buttons = [[InlineKeyboardButton(p['pregunta'], callback_data=f"faq_q_{i}")] for i, p in enumerate(plantillas)]
        buttons.append([InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")])
        keyboard = InlineKeyboardMarkup(buttons)
        await send_agent_telegram(update, "❓ Preguntas Frecuentes: Elige una pregunta:", keyboard, msg_critico=True)
        return
    # --- NUEVO: Clasificación de intención con OpenAI para frases ambiguas o con errores ---
    else:
        # Prompt para clasificación de intención
        intent_prompt = (
            "Clasifica la intención del siguiente mensaje de usuario en una de estas categorías: "
            "'ver_cursos', 'hablar_asesor', 'ver_promociones', 'otra'. "
            "Responde solo con la categoría, sin explicación. Mensaje: " + user_input
        )
        intent_result = openai_intent_and_response(user_input, intent_prompt)
        intent = intent_result.get("response", "otra").strip().lower()
        if "ver_cursos" in intent:
            await send_processing_message(update)
            cursos = get_courses()
            if cursos:
                keyboard = create_courses_list_keyboard(cursos)
                await send_grouped_messages(send_agent_telegram, update, ["Te muestro todos los cursos disponibles:"], keyboard, msg_critico=True)
            else:
                await send_agent_telegram(update, "Por el momento no hay cursos disponibles.")
            return
        elif "asesor" in intent:
            await send_agent_telegram(update, "¡Listo! Un asesor de Aprende y Aplica IA te contactará muy pronto para resolver todas tus dudas y apoyarte en tu inscripción. 😊", create_main_keyboard(), msg_critico=True)
            user_data = {
                'user_id': context.bot_data['global_mem'].lead_data.user_id,
                'name': context.bot_data['global_mem'].lead_data.name,
                'email': context.bot_data['global_mem'].lead_data.email,
                'phone': context.bot_data['global_mem'].lead_data.phone,
                'selected_course': context.bot_data['global_mem'].lead_data.selected_course,
                'stage': context.bot_data['global_mem'].lead_data.stage
            }
            notify_advisor_contact_request(user_data)
            return
        elif "promocion" in intent or "descuento" in intent:
            promos = get_promotions()
            if promos:
                promo_text = "💰 **Promociones especiales:**\n\n"
                for promo in promos:
                    promo_text += f"🎁 **{promo['name']}**\n"
                    promo_text += f"{promo['description']}\n"
                    if promo.get('code'):
                        promo_text += f"Código: `{promo['code']}`\n"
                    promo_text += "\n"
                keyboard = create_contextual_cta_keyboard("pricing_inquiry", user_id_str)
                await send_grouped_messages(send_agent_telegram, update, [promo_text], keyboard, msg_critico=True)
            else:
                await send_agent_telegram(update, "Por el momento no hay promociones activas, pero puedes contactar a un asesor para consultar descuentos especiales.", create_contextual_cta_keyboard("default", user_id_str))
            return
    # Si no se detecta intención clara, sigue el flujo conversacional normal

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

    # --- FLUJO ESPECIAL: DETECCIÓN DE HASHTAGS DE ANUNCIO ---
    hashtag_match = re.search(r"#([A-Z0-9_]+).*#([A-Z0-9_]+)", user_input)
    if hashtag_match:
        codigo_curso = hashtag_match.group(1)
        codigo_anuncio = hashtag_match.group(2)
        logger.info(f"Detectado flujo de anuncio: curso={codigo_curso}, anuncio={codigo_anuncio}")
        id_curso = CURSOS_MAP.get(codigo_curso)
        if not id_curso:
            await send_agent_telegram(update, "¡Gracias por tu interés! En breve un asesor te contactará con más información.")
            return
        curso_info = get_course_detail(id_curso)
        if not curso_info:
            await send_agent_telegram(update, "No se encontró información del curso en la base de datos. Un asesor te contactará.")
            return
        context.bot_data['global_mem'].lead_data.selected_course = id_curso
        context.bot_data['global_mem'].lead_data.stage = "info"
        nombre_usuario = update.effective_user.first_name if update.effective_user and update.effective_user.first_name else None
        context.bot_data['global_mem'].lead_data.name = nombre_usuario or "Usuario"
        context.bot_data['global_mem'].lead_data.interests = [codigo_anuncio]
        save_lead(context.bot_data['global_mem'].lead_data)
        context.bot_data['global_mem'].save()
        saludo = f"Hola {nombre_usuario or 'amigo'} 😄 ¿cómo estás? Mi nombre es Brenda. Soy un sistema inteligente, parte del equipo de Aprende y Aplica IA. Recibí tu solicitud de información sobre el curso: *{curso_info['name']}*. ¡Con gusto te ayudo!"
        await send_agent_telegram(update, saludo, None)
        await send_agent_telegram(update, "Antes de continuar, ¿cómo te gustaría que te llame?", create_main_keyboard())
        context.bot_data['global_mem'].lead_data.stage = "awaiting_preferred_name"
        context.bot_data['global_mem'].save()
        return

    # --- FLUJO DE CAPTURA DE DATOS PARA CONTACTO DE ASESOR ---
    if context.bot_data['global_mem'].lead_data.stage == "awaiting_email_contact":
        from bot.utils import validar_email
        if validar_email(user_input):
            context.bot_data['global_mem'].lead_data.email = user_input
            context.bot_data['global_mem'].lead_data.stage = "awaiting_phone_contact"
            context.bot_data['global_mem'].save()
            await send_agent_telegram(update, "¡Gracias! Ahora, por favor ingresa tu número de teléfono:")
        else:
            await send_agent_telegram(update, "¿Podrías ingresar un correo válido, por favor? Debe tener formato usuario@dominio.com")
        return
    elif context.bot_data['global_mem'].lead_data.stage == "awaiting_phone_contact":
        telefono = user_input.strip()
        if len(telefono) >= 8 and any(c.isdigit() for c in telefono):
            context.bot_data['global_mem'].lead_data.phone = telefono
            context.bot_data['global_mem'].lead_data.stage = "awaiting_course_contact"
            context.bot_data['global_mem'].save()
            cursos = get_courses()
            if cursos:
                keyboard = create_courses_list_keyboard(cursos)
                await send_agent_telegram(update, "¡Perfecto! Ahora selecciona el curso de tu interés:", keyboard, msg_critico=True)
            else:
                await send_agent_telegram(update, "No hay cursos disponibles en este momento.")
        else:
            await send_agent_telegram(update, "Por favor ingresa un número de teléfono válido (al menos 8 dígitos).")
        return
    elif context.bot_data['global_mem'].lead_data.stage == "awaiting_course_contact":
        cursos = get_courses()
        if cursos:
            keyboard = create_courses_list_keyboard(cursos)
            await send_agent_telegram(update, "Selecciona el curso de tu interés:", keyboard, msg_critico=True)
        else:
            await send_agent_telegram(update, "No hay cursos disponibles en este momento.")
        return
    # El stage 'awaiting_contact_confirmation' se maneja por callback

    # --- FLUJO NORMAL: NOMBRE, EMAIL, TELÉFONO, ETC. ---
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
            await send_agent_telegram(update, mensaje_bienvenida, create_main_keyboard(), msg_critico=True)
            await send_agent_telegram(update, "Menú principal:", create_main_inline_keyboard(), msg_critico=True)
        else:
            await send_agent_telegram(update, "Por favor, ingresa un nombre válido (solo letras y espacios).", None, msg_critico=True)
        return

    # --- FLUJO DE NOMBRE PREFERIDO ---
    if context.bot_data['global_mem'].lead_data.stage == "awaiting_preferred_name":
        nombre_preferido = user_input.strip()
        if len(nombre_preferido) > 1 and not any(x in nombre_preferido.lower() for x in ["no", "igual", "como quieras", "da igual", "me da igual"]):
            context.bot_data['global_mem'].lead_data.name = nombre_preferido.title()
            context.bot_data['global_mem'].lead_data.stage = "info"
            context.bot_data['global_mem'].save()
            await send_agent_telegram(update, f"¡Perfecto, {context.bot_data['global_mem'].lead_data.name}! A partir de ahora me dirigiré a ti así. 😊")
        else:
            nombre_telegram = update.effective_user.first_name if update.effective_user and update.effective_user.first_name else "amigo"
            context.bot_data['global_mem'].lead_data.name = nombre_telegram
            context.bot_data['global_mem'].lead_data.stage = "info"
            context.bot_data['global_mem'].save()
            await send_agent_telegram(update, f"¡Perfecto! Me dirigiré a ti como {context.bot_data['global_mem'].lead_data.name}.")
        curso_info = get_course_detail(context.bot_data['global_mem'].lead_data.selected_course)
        if curso_info:
            messages = []
            try:
                with open(os.path.join("data", "imagen_prueba.jpg"), 'rb') as img_file:
                    await update.message.reply_photo(img_file)
            except Exception as e:
                logger.warning(f"No se pudo enviar imagen: {e}")
            try:
                with open(os.path.join("data", "pdf_prueba.pdf"), 'rb') as pdf_file:
                    await update.message.reply_document(pdf_file)
            except Exception as e:
                logger.warning(f"No se pudo enviar PDF: {e}")
            messages.append(f"{context.bot_data['global_mem'].lead_data.name}, aquí tienes toda la información detallada y el temario del curso. Si tienes alguna pregunta, ¡estoy para ayudarte en todo momento!")
            resumen = (
                f"*Modalidad:* {curso_info.get('modality', 'No especificado')}\n"
                f"*Duración:* {curso_info.get('total_duration', 'N/A')} horas\n"
                f"*Horario:* {curso_info.get('schedule', 'A consultar')}\n"
                f"*Precio:* {curso_info.get('price_usd', 'N/A')} {curso_info.get('currency', '')}\n"
                f"*Incluye:* {curso_info.get('includes', 'Material, acceso a grabaciones, soporte')}\n"
            )
            messages.append(resumen)
            keyboard = create_contextual_cta_keyboard("course_selected", user_id_str)
            await send_grouped_messages(send_agent_telegram, update, messages, keyboard, msg_critico=True)
        else:
            await send_agent_telegram(update, "¿Sobre qué curso te gustaría saber más?", create_contextual_cta_keyboard("default", user_id_str))
        return

    # --- MENSAJE DE PROCESANDO SI ES NECESARIO ---
    processing_msg = None
    if len(user_input) > 20 or any(word in user_input.lower() for word in ['curso', 'precio', 'módulos', 'comprar', 'promoción']):
        processing_msg = await send_processing_message(update)

    # --- PROCESAMIENTO PRINCIPAL Y RESPUESTA ---
    try:
        bot_reply = openai_intent_and_response(user_input, "")
        if context.bot_data['global_mem'].lead_data.email:
            context.bot_data['global_mem'].history.append({
                "user_input": user_input,
                "bot_reply": bot_reply,
                "timestamp": time.time()
            })
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
        await send_grouped_messages(send_agent_telegram, update, [bot_reply], keyboard, msg_critico=True)
    except Exception as e:
        logger.error(f"Error procesando mensaje del usuario {user_id_str}: {e}", exc_info=True)
        error_msg = "Lo siento, hubo un problema técnico. ¿Te gustaría que un asesor humano te contacte?"
        keyboard = keyboard if 'keyboard' in locals() else None
        await send_grouped_messages(send_agent_telegram, update, [error_msg], keyboard, msg_critico=True)

    # --- Interest Score: NEGATIVE ---
    if detect_negative_feedback(user_input):
        logger.info(f"NEGATIVE feedback detectado para usuario {user_id_str}")
    # --- Interest Score: READ_VALUE ---
    if hasattr(context.bot_data['global_mem'].lead_data, 'awaiting_ack') and context.bot_data['global_mem'].lead_data.awaiting_ack:
        last_ack = getattr(context.bot_data['global_mem'].lead_data, 'last_ack_time', None)
        if last_ack and (time.time() - last_ack < 600):
            logger.info(f"READ_VALUE disparado para usuario {user_id_str}")
        context.bot_data['global_mem'].lead_data.awaiting_ack = False
        context.bot_data['global_mem'].save()

@handle_telegram_errors
async def send_agent_telegram(update: Update, msg: str, keyboard=None, msg_critico=False) -> None:
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
async def edit_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, new_text: str, keyboard=None) -> None:
    """Edita un mensaje existente usando el contexto. Si no se pasa teclado, agrega el de navegación persistente."""
    try:
        if keyboard is None:
            keyboard = create_main_keyboard()
        await context.bot.edit_message_text(new_text, chat_id=chat_id, message_id=message_id, reply_markup=keyboard)
    except Exception as e:
        logger.warning(f"No se pudo editar mensaje: {e}")

@handle_telegram_errors
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las respuestas a botones interactivos con nuevos CTAs y privacidad."""
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
    
    try:
        # --- FLUJO DE PRIVACIDAD ---
        if query.data == "privacy_accept":
            context.bot_data['global_mem'].lead_data.privacy_accepted = True
            context.bot_data['global_mem'].save()
            logger.info(f"Usuario {user_id_str} aceptó la privacidad")
            # Enviar nuevo mensaje de bienvenida con botones, sin editar el aviso
            if not context.bot_data['global_mem'].lead_data.name:
                welcome_text = "¡Perfecto! 👋 Ahora puedo ayudarte mejor."
                question_text = "¿Cómo te gustaría que te llame? 😊"
                await send_agent_telegram(update, welcome_text, None, msg_critico=True)
                await send_agent_telegram(update, question_text, None, msg_critico=True)
                context.bot_data['global_mem'].lead_data.stage = "awaiting_name"
                context.bot_data['global_mem'].save()
            else:
                welcome_msg = (
                    f"¡Hola {context.bot_data['global_mem'].lead_data.name}! 👋\n\n"
                    "¿Qué te gustaría aprender sobre Inteligencia Artificial? "
                    "Tenemos cursos de IA práctica, prompts, generación de imágenes y más."
                )
                keyboard = create_contextual_cta_keyboard("default", user_id_str)
                await send_agent_telegram(update, welcome_msg, keyboard, msg_critico=True)
            return
            
        elif query.data == "privacy_view":
            # Re-enviar el aviso de privacidad
            privacy_text = (
                "🔒 **Aviso de Privacidad Completo**\n\n"
                "**Información que recopilamos:**\n"
                "• Nombre completo\n"
                "• Dirección de correo electrónico\n"
                "• Número de teléfono\n"
                "• Información sobre tus intereses en cursos\n\n"
                "**Cómo utilizamos tu información:**\n"
                "• Para brindarte información sobre nuestros cursos\n"
                "• Para enviarte materiales educativos relevantes\n"
                "• Para contactarte sobre promociones especiales\n"
                "• Para mejorar nuestros servicios\n\n"
                "**Protección de datos:**\n"
                "• Tus datos están seguros y protegidos\n"
                "• No compartimos tu información con terceros\n"
                "• Puedes solicitar la eliminación en cualquier momento\n\n"
                "¿Aceptas que procesemos tus datos según este aviso?"
            )
            privacy_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Acepto y continúo", callback_data="privacy_accept")],
                [InlineKeyboardButton("🔒 Ver Aviso Completo", callback_data="privacy_view")]
            ])
            await query.edit_message_text(privacy_text, reply_markup=privacy_keyboard, parse_mode='Markdown')
            return
        
        # --- FLUJO DE BOTONES CTA EXISTENTES ---
        elif query.data in ["cta_reservar"]:
            await query.edit_message_text("¡Perfecto! 🎉 Hemos registrado tu interés en reservar tu lugar. Un asesor se pondrá en contacto contigo para finalizar el proceso. ¿Te gustaría dejar tu número de WhatsApp o prefieres que te contactemos por aquí?", reply_markup=None)
            user_data = {
                'user_id': context.bot_data['global_mem'].lead_data.user_id,
                'name': context.bot_data['global_mem'].lead_data.name,
                'email': context.bot_data['global_mem'].lead_data.email,
                'phone': context.bot_data['global_mem'].lead_data.phone,
                'selected_course': context.bot_data['global_mem'].lead_data.selected_course,
                'stage': context.bot_data['global_mem'].lead_data.stage
            }
            notify_advisor_reservation_request(user_data)
            return
            
        elif query.data in ["cta_info_completa"]:
            # Disparador de evento: MORE_INFO
            await query.edit_message_text("Aquí tienes la información completa del curso. Si tienes alguna pregunta, ¡estoy para ayudarte!", reply_markup=None)
            try:
                # Chequeo robusto de chat_id
                chat_id = None
                if query.message is not None and hasattr(query.message, "chat") and query.message.chat is not None:
                    chat_id = query.message.chat.id  # type: ignore
                if chat_id:
                    with open(os.path.join("data", "pdf_prueba.pdf"), 'rb') as pdf_file:
                        await context.bot.send_document(chat_id=chat_id, document=pdf_file)
                    # Chequeo de umbral para sugerir llamada
                    score = get_interest_score(user_id_str)
                    if score is not None and score >= 20:
                        await context.bot.send_message(chat_id=chat_id, text="¡Veo que estás muy interesado! ¿Te gustaría agendar una llamada con un asesor humano?")
            except Exception as e:
                logger.warning(f"No se pudo enviar PDF info completa o checar interest_score: {e}")
            return
            
        elif query.data in ["cta_asesor", "cta_asesor_curso", "cta_asistencia", "cta_llamar", "cta_plan_pagos", "cta_negociar", "cta_reservar", "cta_finalizar_compra", "cta_inscribirse"]:
            await contactar_asesor(update, context)
            return
        # En FAQ, solo mostrar_lista_cursos y responder FAQ, nunca contacto
        elif query.data in ["cta_faq", "faq_menu"]:
            faq_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "plantillas.json"))
            with open(faq_path, "r", encoding="utf-8") as f:
                plantillas = json.load(f)
            buttons = [[InlineKeyboardButton(p['pregunta'], callback_data=f"faq_q_{i}")] for i, p in enumerate(plantillas)]
            buttons.append([InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")])
            keyboard = InlineKeyboardMarkup(buttons)
            await query.edit_message_text("❓ Preguntas Frecuentes: Elige una pregunta:", reply_markup=keyboard)
            return
        elif query.data.startswith("faq_q_"):
            faq_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "plantillas.json"))
            with open(faq_path, "r", encoding="utf-8") as f:
                plantillas = json.load(f)
            idx = int(query.data.replace("faq_q_", ""))
            plantilla = plantillas[idx]
            pregunta = plantilla['pregunta']
            respuesta = plantilla['respuesta']
            campos = plantilla.get('campos', [])
            # Si la respuesta requiere datos de curso, SIEMPRE pedir al usuario que seleccione un curso
            if campos and any(c in ['price_usd', 'currency', 'total_duration', 'level', 'language', 'modules_list', 'purchase_link', 'demo_request_link'] for c in campos):
                await mostrar_lista_cursos(update, context, mensaje="Por favor, selecciona el curso sobre el que quieres saber:")
                context.bot_data['faq_pending'] = idx
                return
            else:
                buttons = [
                    [InlineKeyboardButton("🔙 Volver a Preguntas Frecuentes", callback_data="faq_menu")],
                    [InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")]
                ]
                keyboard = InlineKeyboardMarkup(buttons)
                await query.edit_message_text(f"❓ {pregunta}\n\n{respuesta}", reply_markup=keyboard)
                return
        elif query.data.startswith("course_") and 'faq_pending' in context.bot_data:
            course_id = query.data.replace("course_", "")
            context.bot_data['global_mem'].lead_data.selected_course = course_id
            context.bot_data['global_mem'].save()
            idx = context.bot_data.pop('faq_pending')
            faq_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "plantillas.json"))
            with open(faq_path, "r", encoding="utf-8") as f:
                plantillas = json.load(f)
            plantilla = plantillas[idx]
            pregunta = plantilla['pregunta']
            respuesta = plantilla['respuesta']
            campos = plantilla.get('campos', [])
            course = get_course_detail(course_id)
            for campo in campos:
                valor = course.get(campo, f"[{campo}]") if course else f"[{campo}]"
                respuesta = respuesta.replace(f"[{campo}]", str(valor))
            buttons = [
                [InlineKeyboardButton("🔙 Volver a Preguntas Frecuentes", callback_data="faq_menu")],
                [InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")]
            ]
            keyboard = InlineKeyboardMarkup(buttons)
            await query.edit_message_text(f"❓ {pregunta}\n\n{respuesta}", reply_markup=keyboard)
            return
            
        elif query.data in ["cta_ver_cursos", "cta_otros_cursos"]:
            await query.edit_message_text("Te muestro todos los cursos disponibles:", reply_markup=None)
            cursos = get_courses()
            if cursos and query.message and query.message.chat:
                keyboard = create_courses_list_keyboard(cursos)
                await context.bot.send_message(chat_id=query.message.chat.id, text="Selecciona un curso para más información:", reply_markup=keyboard)
            elif query.message and query.message.chat:
                await context.bot.send_message(chat_id=query.message.chat.id, text="Por el momento no hay otros cursos disponibles.")
            return
            
        elif query.data in ["cta_inicio"]:
            await query.edit_message_text("Has vuelto al inicio. ¿En qué puedo ayudarte hoy?", reply_markup=None)
            keyboard = create_main_keyboard()
            inline_keyboard = create_main_inline_keyboard()
            if query.message and query.message.chat:
                await context.bot.send_message(chat_id=query.message.chat.id, text="Menú principal:", reply_markup=keyboard)
                await context.bot.send_message(chat_id=query.message.chat.id, text="Menú principal:", reply_markup=inline_keyboard)
            return
            
        # --- NUEVOS CTAs CONTEXTUALES ---
        elif query.data in ["cta_comprar_curso", "cta_comprar_ahora", "cta_finalizar_compra", "cta_inscribirse"]:
            course_id = context.bot_data['global_mem'].lead_data.selected_course
            if course_id:
                course = get_course_detail(course_id)
                # Simular siempre un enlace de compra aunque no exista en la base
                purchase_link = course.get("purchase_link") if course else None
                if not purchase_link:
                    purchase_link = "https://www.ejemplo.com/compra-curso"
                buy_msg = (
                    f"💳 <b>Comprar: {course['name'] if course else 'Curso seleccionado'}</b>\n\n"
                    f"Precio: ${course['price_usd'] if course else 'N/A'} {course['currency'] if course else ''}\n\n"
                    f"<a href='{purchase_link}'>Haz clic aquí para comprar</a>\n\n"
                    f"Después de la compra, recibirás acceso inmediato al curso. "
                    f"¿Necesitas ayuda con algo más?"
                )
                # Teclado útil después de comprar
                post_buy_keyboard = create_contextual_cta_keyboard("post_buy", user_id_str)
                await query.edit_message_text(buy_msg, reply_markup=post_buy_keyboard, parse_mode='HTML')
            else:
                await query.edit_message_text("Primero necesitas seleccionar un curso. ¿Cuál te interesa?", reply_markup=create_contextual_cta_keyboard("default", user_id_str))
            return
            
        elif query.data in ["cta_ver_modulos"]:
            course_id = context.bot_data['global_mem'].lead_data.selected_course
            if course_id:
                modules = get_modules(course_id)
                if modules:
                    modules_text = "📋 **Módulos del curso:**\n\n"
                    for i, module in enumerate(modules, 1):
                        modules_text += f"{i}. **{module['name']}**\n"
                        modules_text += f"   Duración: {module.get('duration', 'N/A')} horas\n"
                        modules_text += f"   {module.get('description', '')}\n\n"
                    
                    keyboard = create_contextual_cta_keyboard("course_selected", user_id_str)
                    await query.edit_message_text(modules_text, reply_markup=keyboard, parse_mode='Markdown')
                else:
                    await query.edit_message_text("No se encontraron módulos para este curso. Un asesor te contactará con más información.", reply_markup=None)
            else:
                await query.edit_message_text("Primero necesitas seleccionar un curso. ¿Cuál te interesa?", reply_markup=create_contextual_cta_keyboard("default", user_id_str))
            return
            
        elif query.data in ["cta_descuento", "cta_cupon"]:
            promos = get_promotions()
            if promos:
                promo_text = "🎯 **Promociones disponibles:**\n\n"
                for promo in promos:
                    promo_text += f"• **{promo['name']}**: {promo['description']}\n"
                    if promo.get('code'):
                        promo_text += f"  Código: `{promo['code']}`\n"
                    promo_text += "\n"
                
                keyboard = create_contextual_cta_keyboard("pricing_inquiry", user_id_str)
                await query.edit_message_text(promo_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await query.edit_message_text("Por el momento no hay promociones activas, pero puedes contactar a un asesor para consultar descuentos especiales.", reply_markup=create_contextual_cta_keyboard("default", user_id_str))
            return
            
        elif query.data in ["cta_promociones"]:
            promos = get_promotions()
            if promos:
                promo_text = "💰 **Promociones especiales:**\n\n"
                for promo in promos:
                    promo_text += f"🎁 **{promo['name']}**\n"
                    promo_text += f"{promo['description']}\n"
                    if promo.get('code'):
                        promo_text += f"Código: `{promo['code']}`\n"
                    promo_text += "\n"
                keyboard = create_contextual_cta_keyboard("pricing_inquiry", user_id_str)
                await query.edit_message_text(promo_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await query.edit_message_text("Por el momento no hay promociones activas, pero puedes contactar a un asesor para consultar descuentos especiales.", reply_markup=create_contextual_cta_keyboard("default", user_id_str))
            return

        elif query.data.startswith("course_"):
            # Nuevo flujo: mostrar menú de opciones del curso sin contactar a un asesor
            course_id = query.data.replace("course_", "")
            course = get_course_detail(course_id)
            if course:
                context.bot_data['global_mem'].lead_data.selected_course = course_id
                context.bot_data['global_mem'].lead_data.stage = "exploring_course"
                context.bot_data['global_mem'].save()
                # Mostrar menú de opciones del curso (exploración)
                keyboard = create_course_explore_keyboard(course_id, course.get('name', 'Curso'))
                info_text = f"<b>{course.get('name', 'Curso')}</b>\n\n{course.get('short_description', '')}\n\n¿Qué te gustaría hacer?"
                await query.edit_message_text(info_text, reply_markup=keyboard, parse_mode='HTML')
            else:
                await query.edit_message_text("No se encontró información del curso. ¿Te gustaría ver otros cursos disponibles?", reply_markup=create_courses_list_keyboard(get_courses()))
            return
        elif query.data.startswith("modules_") and context.bot_data['global_mem'].lead_data.stage in ["awaiting_course_contact", "exploring_course"]:
            course_id = query.data.replace("modules_", "")
            modules = get_modules(course_id)
            if modules:
                modules_text = "📋 <b>Módulos del curso:</b>\n\n"
                for i, module in enumerate(modules, 1):
                    modules_text += f"{i}. <b>{module['name']}</b>\n   Duración: {module.get('duration', 'N/A')} horas\n   {module.get('description', '')}\n\n"
                keyboard = create_course_selection_keyboard(course_id, "")
                await query.edit_message_text(modules_text, reply_markup=keyboard, parse_mode='HTML')
            else:
                await query.edit_message_text("No se encontraron módulos para este curso.", reply_markup=None)
            return
        elif query.data.startswith("info_") and context.bot_data['global_mem'].lead_data.stage in ["awaiting_course_contact", "exploring_course"]:
            course_id = query.data.replace("info_", "")
            course = get_course_detail(course_id)
            if course:
                info_text = (
                    f"<b>Información del curso:</b>\n\n"
                    f"{course.get('long_description', course.get('short_description', ''))}\n\n"
                )
                keyboard = create_course_selection_keyboard(course_id, course.get('name', 'Curso'))
                await query.edit_message_text(info_text, reply_markup=keyboard, parse_mode='HTML')
            else:
                await query.edit_message_text("No se encontró información adicional para este curso.", reply_markup=None)
            return
        elif query.data.startswith("select_course_") and context.bot_data['global_mem'].lead_data.stage == "exploring_course":
            course_id = query.data.replace("select_course_", "")
            context.bot_data['global_mem'].lead_data.selected_course = course_id
            context.bot_data['global_mem'].save()
            # Volver a mostrar el menú de opciones del curso
            course = get_course_detail(course_id)
            if course:
                keyboard = create_course_selection_keyboard(course_id, course.get('name', 'Curso'))
                info_text = f"<b>{course.get('name', 'Curso')}</b>\n\n{course.get('short_description', '')}\n\n¿Qué te gustaría hacer?"
                await query.edit_message_text(info_text, reply_markup=keyboard, parse_mode='HTML')
            else:
                await query.edit_message_text("No se encontró información del curso. ¿Te gustaría ver otros cursos disponibles?", reply_markup=create_courses_list_keyboard(get_courses()))
            return
        elif query.data == "change_course" and context.bot_data['global_mem'].lead_data.stage in ["awaiting_course_contact", "exploring_course"]:
            cursos = get_courses()
            if cursos:
                keyboard = create_courses_list_keyboard(cursos)
                await query.edit_message_text("Selecciona el curso de tu interés:", reply_markup=keyboard)
            else:
                await query.edit_message_text("No hay cursos disponibles en este momento.")
            return
        elif query.data == "confirm_contact_data" and context.bot_data['global_mem'].lead_data.stage == "awaiting_contact_confirmation":
            lead = context.bot_data['global_mem'].lead_data
            user_data = {
                'user_id': lead.user_id,
                'name': lead.name,
                'email': lead.email,
                'phone': lead.phone,
                'selected_course': lead.selected_course,
                'stage': lead.stage
            }
            notify_advisor_contact_request(user_data)
            lead.stage = "info"
            context.bot_data['global_mem'].save()
            await query.edit_message_text("¡Listo! Un asesor se pondrá en contacto contigo pronto.")
            await context.bot.send_message(chat_id=query.message.chat.id, text="¿Puedo ayudarte en algo más?")
            keyboard = create_main_keyboard()
            inline_keyboard = create_main_inline_keyboard()
            await context.bot.send_message(chat_id=query.message.chat.id, text="Menú principal:", reply_markup=keyboard)
            await context.bot.send_message(chat_id=query.message.chat.id, text="Menú principal:", reply_markup=inline_keyboard)
            return
        elif query.data == "edit_contact_data" and context.bot_data['global_mem'].lead_data.stage == "awaiting_contact_confirmation":
            lead = context.bot_data['global_mem'].lead_data
            lead.email = ""
            lead.phone = ""
            lead.selected_course = None
            lead.stage = "awaiting_email_contact"
            context.bot_data['global_mem'].save()
            await query.edit_message_text("Vamos a corregir tus datos. Por favor, ingresa tu correo electrónico:")
            return
        elif query.data in ["cta_faq", "faq_menu"]:
            faq_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "plantillas.json"))
            with open(faq_path, "r", encoding="utf-8") as f:
                plantillas = json.load(f)
            buttons = [[InlineKeyboardButton(p['pregunta'], callback_data=f"faq_q_{i}")] for i, p in enumerate(plantillas)]
            buttons.append([InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")])
            keyboard = InlineKeyboardMarkup(buttons)
            await query.edit_message_text("❓ Preguntas Frecuentes: Elige una pregunta:", reply_markup=keyboard)
            return
        elif query.data.startswith("faq_q_"):
            faq_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "plantillas.json"))
            with open(faq_path, "r", encoding="utf-8") as f:
                plantillas = json.load(f)
            idx = int(query.data.replace("faq_q_", ""))
            plantilla = plantillas[idx]
            pregunta = plantilla['pregunta']
            respuesta = plantilla['respuesta']
            campos = plantilla.get('campos', [])
            # Si la respuesta requiere datos de curso, SIEMPRE pedir al usuario que seleccione un curso
            if campos and any(c in ['price_usd', 'currency', 'total_duration', 'level', 'language', 'modules_list', 'purchase_link', 'demo_request_link'] for c in campos):
                cursos = get_courses()
                keyboard = create_courses_list_keyboard(cursos)
                # Guardar el índice de la FAQ pendiente
                context.bot_data['faq_pending'] = idx
                await query.edit_message_text("Por favor, selecciona el curso sobre el que quieres saber:", reply_markup=keyboard)
                return
            else:
                # Si no requiere datos de curso, responder directamente
                buttons = [
                    [InlineKeyboardButton("🔙 Volver a Preguntas Frecuentes", callback_data="faq_menu")],
                    [InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")]
                ]
                keyboard = InlineKeyboardMarkup(buttons)
                await query.edit_message_text(f"❓ {pregunta}\n\n{respuesta}", reply_markup=keyboard)
                return
        elif query.data.startswith("buy_course_") and context.bot_data['global_mem'].lead_data.stage == "exploring_course":
            course_id = query.data.replace("buy_course_", "")
            course = get_course_detail(course_id)
            user_id_str = str(update.effective_user.id) if update.effective_user else ""
            if course:
                purchase_link = course.get("purchase_link") if course else None
                if not purchase_link:
                    purchase_link = "https://www.ejemplo.com/compra-curso"
                buy_msg = (
                    f"💳 <b>Comprar: {course['name'] if course else 'Curso seleccionado'}</b>\n\n"
                    f"Precio: ${course['price_usd'] if course else 'N/A'} {course['currency'] if course else ''}\n\n"
                    f"<a href='{purchase_link}'>Haz clic aquí para comprar</a>\n\n"
                    f"Después de la compra, recibirás acceso inmediato al curso. "
                    f"¿Necesitas ayuda con algo más?"
                )
                post_buy_keyboard = create_contextual_cta_keyboard("post_buy", user_id_str)
                await query.edit_message_text(buy_msg, reply_markup=post_buy_keyboard, parse_mode='HTML')
            else:
                await query.edit_message_text("No se encontró información del curso para comprar.")
            return
        else:
            # Callback no reconocido
            logger.warning(f"Callback no reconocido: {query.data}")
            await query.edit_message_text("Opción no disponible. ¿En qué puedo ayudarte?", reply_markup=create_contextual_cta_keyboard("default", user_id_str))
            return
            
    except Exception as e:
        logger.error(f"Error en handle_callback_query: {e}", exc_info=True)
        await query.edit_message_text("Lo siento, hubo un problema técnico. ¿Te gustaría que un asesor humano te contacte?", reply_markup=create_contextual_cta_keyboard("default", user_id_str))

# --- Disparador: QUIZ ---
@handle_telegram_errors
async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja respuestas a encuestas tipo quiz."""
    user_id = str(update.effective_user.id) if update.effective_user else None
    poll_id = getattr(getattr(update, 'poll_answer', None), 'poll_id', None)
    if user_id and poll_id:
        logger.info(f"PollAnswer recibido de usuario {user_id}")

# --- Disparador: PAYMENT (webhook) ---
def handle_payment_webhook(user_id: str, payment_data: dict) -> None:
    """Llamar cuando se reciba un pago exitoso (webhook externo)."""
    if user_id:
        logger.info(f"Pago registrado para usuario {user_id}")

# --- NUEVAS FUNCIONES REUTILIZABLES ---
async def mostrar_lista_cursos(update, context, mensaje="Selecciona el curso de tu interés:"):
    cursos = get_courses()
    if cursos:
        keyboard = create_courses_list_keyboard(cursos)
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(mensaje, reply_markup=keyboard)
        else:
            await send_agent_telegram(update, mensaje, keyboard, msg_critico=True)
    else:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text("No hay cursos disponibles en este momento.")
        else:
            await send_agent_telegram(update, "No hay cursos disponibles en este momento.")

async def solicitar_datos_contacto(update, context):
    lead = context.bot_data['global_mem'].lead_data
    if not lead.email:
        lead.stage = "awaiting_email_contact"
        context.bot_data['global_mem'].save()
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text("Para que un asesor pueda contactarte, necesito algunos datos.")
            await context.bot.send_message(chat_id=update.callback_query.message.chat.id, text="Por favor, ingresa tu correo electrónico:")
        else:
            await send_agent_telegram(update, "Para que un asesor pueda contactarte, necesito algunos datos.")
            await send_agent_telegram(update, "Por favor, ingresa tu correo electrónico:")
        return False
    if not lead.phone:
        lead.stage = "awaiting_phone_contact"
        context.bot_data['global_mem'].save()
        if hasattr(update, 'callback_query') and update.callback_query:
            await context.bot.send_message(chat_id=update.callback_query.message.chat.id, text="Ahora, por favor ingresa tu número de teléfono:")
        else:
            await send_agent_telegram(update, "Ahora, por favor ingresa tu número de teléfono:")
        return False
    return True

async def contactar_asesor(update, context):
    if not await solicitar_datos_contacto(update, context):
        return
    lead = context.bot_data['global_mem'].lead_data
    user_data = {
        'user_id': lead.user_id,
        'name': lead.name,
        'email': lead.email,
        'phone': lead.phone,
        'selected_course': lead.selected_course,
        'stage': lead.stage
    }
    notify_advisor_contact_request(user_data)
    lead.stage = "info"
    context.bot_data['global_mem'].save()
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text("¡Listo! Un asesor se pondrá en contacto contigo pronto.")
        await context.bot.send_message(chat_id=update.callback_query.message.chat.id, text="¿Puedo ayudarte en algo más?")
        keyboard = create_main_keyboard()
        inline_keyboard = create_main_inline_keyboard()
        await context.bot.send_message(chat_id=update.callback_query.message.chat.id, text="Menú principal:", reply_markup=keyboard)
        await context.bot.send_message(chat_id=update.callback_query.message.chat.id, text="Menú principal:", reply_markup=inline_keyboard)
    else:
        await send_agent_telegram(update, "¡Listo! Un asesor se pondrá en contacto contigo pronto.")
        await send_agent_telegram(update, "¿Puedo ayudarte en algo más?")
        await send_agent_telegram(update, "Menú principal:", create_main_keyboard())
        await send_agent_telegram(update, "Menú principal:", create_main_inline_keyboard())

# --- USO EN FLUJOS ---
# En FAQ: nunca llamar a contactar_asesor ni solicitar_datos_contacto, solo mostrar_lista_cursos y responder FAQ.
# En promociones y submenús de contacto: reemplaza la lógica por llamadas a solicitar_datos_contacto y contactar_asesor según corresponda.

# --- REEMPLAZO EN FLUJOS DE PROMOCIONES Y CONTACTO ---
# Ejemplo para un flujo de contacto:
# await contactar_asesor(update, context)
# Ejemplo para mostrar cursos:
# await mostrar_lista_cursos(update, context)

CURSOS_MAP = {
    "CURSO_IA_CHATGPT": "a392bf83-4908-4807-89a9-95d0acc807c9"
}

async def contact_advisor_flow(update, context, query=None):
    lead = context.bot_data['global_mem'].lead_data
    missing = []
    if not lead.email:
        missing.append('email')
    if not lead.phone:
        missing.append('phone')
    if not lead.selected_course:
        missing.append('selected_course')
    chat_id = None
    if query and query.message and query.message.chat:
        chat_id = query.message.chat.id
    elif update and update.effective_chat:
        chat_id = update.effective_chat.id
    else:
        chat_id = None
    if missing:
        if query:
            await query.edit_message_text("Para que un asesor pueda contactarte, necesito algunos datos.")
        else:
            await send_agent_telegram(update, "Para que un asesor pueda contactarte, necesito algunos datos.")
        if 'email' in missing:
            lead.stage = "awaiting_email_contact"
            context.bot_data['global_mem'].save()
            await context.bot.send_message(chat_id=chat_id, text="Por favor, ingresa tu correo electrónico:")
            return
        elif 'phone' in missing:
            lead.stage = "awaiting_phone_contact"
            context.bot_data['global_mem'].save()
            await context.bot.send_message(chat_id=chat_id, text="Ahora, por favor ingresa tu número de teléfono:")
            return
        elif 'selected_course' in missing:
            lead.stage = "awaiting_course_contact"
            context.bot_data['global_mem'].save()
            cursos = get_courses()
            if cursos:
                keyboard = create_courses_list_keyboard(cursos)
                await context.bot.send_message(chat_id=chat_id, text="Selecciona el curso de tu interés:", reply_markup=keyboard)
            else:
                await context.bot.send_message(chat_id=chat_id, text="No hay cursos disponibles en este momento.")
            return
    # Si ya tiene todos los datos, mostrar confirmación
    lead.stage = "awaiting_contact_confirmation"
    context.bot_data['global_mem'].save()
    resumen = f"Por favor confirma que tus datos son correctos:\n\n" \
        f"Correo: {lead.email or 'No proporcionado'}\n" \
        f"Teléfono: {lead.phone or 'No proporcionado'}\n" \
        f"Curso: {lead.selected_course or 'No seleccionado'}\n\n" \
        f"¿Son correctos?"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Sí, son correctos", callback_data="confirm_contact_data")],
        [InlineKeyboardButton("❌ No, quiero corregirlos", callback_data="edit_contact_data")]
    ])
    await context.bot.send_message(chat_id=chat_id, text=resumen, reply_markup=keyboard)
    return
