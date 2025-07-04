# ==============================
# TECLADOS Y BOTONES INTERACTIVOS DE TELEGRAM
# ==============================
# Este módulo define los teclados principales, contextuales y dinámicos usados en el bot.

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from typing import List, Dict, Optional
from .services import get_interest_score as get_interest_score_func, supabase_query, UMBRAL_PROMO, cache
from config.settings import settings
import logging
logger = logging.getLogger(__name__)

# ==============================
# TELEGRAM INTERACTIVE BUTTONS
# ==============================
def create_main_keyboard():
    """Teclado principal con opciones de cursos, promociones, FAQ, asesor y reinicio."""
    keyboard = [
        [KeyboardButton("📚 Ver Cursos"), KeyboardButton("💰 Ver Promociones")],
        [KeyboardButton("❓ FAQ"), KeyboardButton("👨‍💼 Hablar con Asesor")],
        [KeyboardButton("🔄 Reiniciar Conversación")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def create_main_inline_keyboard():
    """Teclado inline principal con opciones de cursos, promociones, FAQ, asesor y reinicio."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Ver Cursos", callback_data="ver_cursos"), 
         InlineKeyboardButton("💰 Ver Promociones", callback_data="promociones")],
        [InlineKeyboardButton("❓ FAQ", callback_data="faq"), 
         InlineKeyboardButton("👨‍💼 Hablar con Asesor", callback_data="contacto")],
        [InlineKeyboardButton("🔄 Reiniciar Conversación", callback_data="reiniciar")]
    ])

def create_course_keyboard(course_id: str):
    """Teclado específico para un curso con opciones de compra, módulos, promoción e info."""
    keyboard = [
        [InlineKeyboardButton("💳 Comprar Ahora", callback_data=f"buy_course_{course_id}")],
        [InlineKeyboardButton("📋 Ver Módulos", callback_data=f"modules_{course_id}")],
        [InlineKeyboardButton("💰 Aplicar Promoción", callback_data=f"promo_{course_id}")],
        [InlineKeyboardButton("❓ Más Información", callback_data=f"info_{course_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_courses_list_keyboard(courses: List[Dict]):
    """Teclado con la lista de cursos disponibles (máx 5)."""
    keyboard = []
    for i, course in enumerate(courses[:5]):
        keyboard.append([InlineKeyboardButton(
            f"{i+1}. {course['name']}", 
            callback_data=f"course_{course['id']}"
        )])
    keyboard.append([InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")])
    return InlineKeyboardMarkup(keyboard)

def create_cta_keyboard(context_type="default", user_id=None):
    """Teclado de CTAs dinámico según contexto y score de interés."""
    score = get_interest_score_func(user_id) if user_id is not None else None
    cta_buttons = get_cta_buttons(context_type)
    # Si el score es bajo, filtra los botones de promociones
    if score is None or score < UMBRAL_PROMO:
        cta_buttons = [b for b in cta_buttons if 'promo' not in b['callback_data'] and 'descuento' not in b['callback_data']]
    keyboard = []
    for button in cta_buttons:
        keyboard.append([InlineKeyboardButton(
            button["text"], 
            callback_data=button["callback_data"]
        )])
    return InlineKeyboardMarkup(keyboard) if keyboard else None

def create_contextual_cta_keyboard(context_type: str, user_id: Optional[str] = None) -> InlineKeyboardMarkup:
    """Teclado contextual de CTAs según el contexto conversacional y el interés del usuario."""
    buttons = []
    if context_type == "privacy_pending":
        buttons = [
            [InlineKeyboardButton("✅ Acepto y continúo", callback_data="privacy_accept")],
            [InlineKeyboardButton("🔒 Ver Aviso Completo", callback_data="privacy_view")]
        ]
    elif context_type == "default":
        buttons = [
            [InlineKeyboardButton("📚 Ver Cursos", callback_data="cta_ver_cursos")],
            [InlineKeyboardButton("👨‍💼 Hablar con Asesor", callback_data="cta_asesor")],
            [InlineKeyboardButton("💰 Ver Promociones", callback_data="cta_promociones")]
        ]
    elif context_type == "course_selected":
        buttons = [
            [InlineKeyboardButton("💳 Comprar Curso", callback_data="cta_comprar_curso")],
            [InlineKeyboardButton("📋 Ver Módulos", callback_data="cta_ver_modulos")],
            [InlineKeyboardButton("🎯 Aplicar Descuento", callback_data="cta_descuento")]
        ]
    elif context_type == "pricing_inquiry":
        buttons = [
            [InlineKeyboardButton("💳 Comprar Ahora", callback_data="cta_comprar_ahora")],
            [InlineKeyboardButton("📅 Plan de Pagos", callback_data="cta_plan_pagos")],
            [InlineKeyboardButton("🎫 Usar Cupón", callback_data="cta_cupon")]
        ]
    elif context_type == "purchase_intent":
        buttons = [
            [InlineKeyboardButton("✅ Finalizar Compra", callback_data="cta_finalizar_compra")],
            [InlineKeyboardButton("🤝 Negociar Precio", callback_data="cta_negociar")],
            [InlineKeyboardButton("👨‍💼 Asesor Especializado", callback_data="cta_asesor_curso")]
        ]
    elif context_type == "high_interest":
        buttons = [
            [InlineKeyboardButton("🎯 Reservar Lugar", callback_data="cta_reservar")],
            [InlineKeyboardButton("📞 Llamada Inmediata", callback_data="cta_llamar")]
        ]
    elif context_type == "post_buy":
        buttons = [
            [InlineKeyboardButton("📚 Ver Cursos", callback_data="cta_ver_cursos")],
            [InlineKeyboardButton("👨‍💼 Hablar con Asesor", callback_data="cta_asesor")],
            [InlineKeyboardButton("💰 Ver Promociones", callback_data="cta_promociones")]
        ]
    elif context_type == "error":
        buttons = [
            [InlineKeyboardButton("👨‍💼 Contactar Asesor", callback_data="cta_asesor")],
            [InlineKeyboardButton("🔄 Reintentar", callback_data="cta_reiniciar")]
        ]
    
    # Verificar interest_score para high_interest
    if context_type == "high_interest" and user_id:
        score = get_interest_score_func(user_id)
        if score is None or score < 30:
            buttons = [
                [InlineKeyboardButton("✅ Finalizar Compra", callback_data="cta_finalizar_compra")],
                [InlineKeyboardButton("🤝 Negociar Precio", callback_data="cta_negociar")],
                [InlineKeyboardButton("👨‍💼 Asesor Especializado", callback_data="cta_asesor_curso")]
            ]
    
    # Añadir botón universal de inicio si no está presente
    if not any(btn.callback_data == "cta_inicio" for row in buttons for btn in row):
        buttons.append([InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")])
    
    return InlineKeyboardMarkup(buttons)

def create_promotion_keyboard(promotion_id: str, user_id=None):
    """Teclado para promociones con opciones de aplicar y ver otras."""
    score = get_interest_score_func(user_id) if user_id is not None else None
    if score is None or score < UMBRAL_PROMO:
        return None
    keyboard = [
        [InlineKeyboardButton("✅ Aplicar Promoción", callback_data=f"apply_promo_{promotion_id}")],
        [InlineKeyboardButton("🔙 Ver Otras Promociones", callback_data="cta_promociones")],
        [InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ==============================
# BOTONES CTA DINÁMICOS DESDE SUPABASE
# ==============================
def get_cta_buttons(context_type="default"):
    cache_key = f"cta_buttons_{context_type}"
    cached_result = cache.get(cache_key)
    if cached_result:
        cta_buttons = cached_result
    else:
        try:
            filters = {"active": "eq.TRUE", "context_type": f"eq.{context_type}"}
            cta_buttons = supabase_query("cta_buttons", filters)
            if not cta_buttons:
                filters = {"active": "eq.TRUE", "context_type": "eq.default"}
                cta_buttons = supabase_query("cta_buttons", filters)
            if cta_buttons:
                cta_buttons.sort(key=lambda x: x.get('priority', 999))
                cache.set(cache_key, cta_buttons)
            else:
                cta_buttons = [
                    {"text": "✅ Reservar mi lugar", "callback_data": "cta_reservar", "priority": 1},
                    {"text": "📄 Quiero la info completa", "callback_data": "cta_info_completa", "priority": 2},
                    {"text": "🤝 Que me contacte un asesor", "callback_data": "cta_asesor", "priority": 3},
                    {"text": "📚 Ver más cursos", "callback_data": "cta_ver_cursos", "priority": 4},
                    {"text": "🏠 Volver al inicio", "callback_data": "cta_inicio", "priority": 5}
                ]
        except Exception as e:
            logger.error(f"Error obteniendo botones CTA: {e}")
            cta_buttons = [
                {"text": "✅ Reservar mi lugar", "callback_data": "cta_reservar", "priority": 1},
                {"text": "📄 Quiero la info completa", "callback_data": "cta_info_completa", "priority": 2},
                {"text": "🤝 Que me contacte un asesor", "callback_data": "cta_asesor", "priority": 3},
                {"text": "📚 Ver más cursos", "callback_data": "cta_ver_cursos", "priority": 4},
                {"text": "🏠 Volver al inicio", "callback_data": "cta_inicio", "priority": 5}
            ]
    # Filtrar botones de promociones
    cta_buttons = [b for b in cta_buttons if 'promo' not in b['callback_data'] and 'descuento' not in b['callback_data']]
    # Asegurar que los botones clave estén presentes
    has_inicio = any(b["callback_data"] == "cta_inicio" for b in cta_buttons)
    has_ver_cursos = any(b["callback_data"] == "cta_ver_cursos" for b in cta_buttons)
    if not has_ver_cursos:
        cta_buttons.append({"text": "📚 Ver más cursos", "callback_data": "cta_ver_cursos", "priority": 98})
    if not has_inicio:
        cta_buttons.append({"text": "🏠 Volver al inicio", "callback_data": "cta_inicio", "priority": 99})
    cta_buttons.sort(key=lambda x: x.get('priority', 999))
    return cta_buttons

def create_course_selection_keyboard(course_id: str, course_name: str):
    """Teclado para submenús de selección de curso."""
    keyboard = [
        [InlineKeyboardButton("📋 Ver Módulos", callback_data=f"modules_{course_id}")],
        [InlineKeyboardButton("❓ Más Información", callback_data=f"info_{course_id}")],
        [InlineKeyboardButton("✅ Seleccionar este curso", callback_data=f"select_course_{course_id}")],
        [InlineKeyboardButton("🔙 Cambiar de curso", callback_data="change_course")],
        [InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_course_explore_keyboard(course_id: str, course_name: str):
    """Teclado para explorar un curso específico."""
    keyboard = [
        [InlineKeyboardButton("📋 Ver Módulos y Contenido", callback_data=f"modules_{course_id}")],
        [InlineKeyboardButton("⏱️ Duración y Horarios", callback_data=f"duration_{course_id}")],
        [InlineKeyboardButton("💰 Ver Precio y Formas de Pago", callback_data=f"price_{course_id}")],
        [InlineKeyboardButton("💳 ¡Quiero Inscribirme!", callback_data=f"buy_{course_id}")],
        [InlineKeyboardButton("🔙 Ver otros cursos", callback_data="ver_cursos")],
        [InlineKeyboardButton("🏠 Volver al inicio", callback_data="menu_principal")]
    ]
    return InlineKeyboardMarkup(keyboard)
