"""
FAQ handler module for the Telegram bot.
"""
import json
import logging
from typing import Dict, List, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

def load_faq_templates() -> List[Dict]:
    """Carga las plantillas de FAQ desde el archivo JSON."""
    try:
        with open('data/plantillas.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('faq_templates', [])
    except Exception as e:
        logger.error(f"Error cargando plantillas FAQ: {e}")
        return []

def get_faq_keyboard() -> Optional[InlineKeyboardMarkup]:
    """Crea el teclado con las preguntas frecuentes."""
    templates = load_faq_templates()
    if not templates:
        return None
    
    keyboard = []
    for i, template in enumerate(templates):
        keyboard.append([InlineKeyboardButton(
            template['pregunta'],
            callback_data=f"faq_q_{i}"
        )])
    
    keyboard.append([InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")])
    return InlineKeyboardMarkup(keyboard)

def get_faq_response(template_idx: int, course_data: Optional[Dict] = None) -> Tuple[str, bool]:
    """
    Obtiene la respuesta para una FAQ específica.
    
    Args:
        template_idx: Índice de la plantilla
        course_data: Datos del curso si la pregunta requiere información específica
    
    Returns:
        Tuple[str, bool]: (respuesta, requiere_curso)
    """
    templates = load_faq_templates()
    if not templates or template_idx >= len(templates):
        return "Lo siento, no pude encontrar la respuesta a esa pregunta.", False
    
    template = templates[template_idx]
    respuesta = template['respuesta']
    requiere_curso = template.get('requiere_curso', False)
    
    # Si la plantilla requiere datos del curso pero no los tenemos
    if requiere_curso and not course_data:
        return respuesta, True
    
    # Si tenemos datos del curso, reemplazamos los campos
    if course_data and template['campos']:
        for campo in template['campos']:
            valor = course_data.get(campo, 'No especificado')
            # Manejo especial para algunos campos
            if campo == 'modules_list' and isinstance(valor, list):
                valor = "\n".join([f"• {m}" for m in valor])
            elif campo == 'total_duration' and valor != 'No especificado':
                valor = str(valor)  # Asegurar que sea string
            respuesta = respuesta.replace(f"[{campo}]", str(valor))
    
    return respuesta, False

def format_faq_response(template_idx: int, course_data: Optional[Dict] = None) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """
    Formatea la respuesta de FAQ con el teclado apropiado.
    
    Args:
        template_idx: Índice de la plantilla
        course_data: Datos del curso si están disponibles
    
    Returns:
        Tuple[str, Optional[InlineKeyboardMarkup]]: (mensaje, teclado)
    """
    respuesta, requiere_curso = get_faq_response(template_idx, course_data)
    
    if requiere_curso:
        # Si necesitamos datos del curso, mostrar lista de cursos
        keyboard = [
            [InlineKeyboardButton("📚 Seleccionar Curso", callback_data=f"faq_select_course_{template_idx}")],
            [InlineKeyboardButton("❓ Ver otras preguntas", callback_data="faq")],
            [InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")]
        ]
        mensaje = (
            f"{respuesta}\n\n"
            "Para mostrarte información específica, necesito saber sobre qué curso tienes dudas. "
            "Por favor, selecciona un curso:"
        )
    else:
        # Si no necesitamos datos del curso, mostrar opciones estándar
        keyboard = [
            [InlineKeyboardButton("❓ Ver otras preguntas", callback_data="faq")],
            [InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")]
        ]
        mensaje = respuesta
    
    return mensaje, InlineKeyboardMarkup(keyboard)