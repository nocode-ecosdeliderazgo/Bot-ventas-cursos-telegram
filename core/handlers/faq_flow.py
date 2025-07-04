"""
Manejadores para el flujo de preguntas frecuentes.
"""

import logging
from typing import Dict, Optional, TypedDict, Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.utils.error_handlers import handle_telegram_errors

logger = logging.getLogger(__name__)

class FAQCategory(TypedDict):
    title: str
    questions: Dict[str, str]

FAQ_DATA: Dict[str, FAQCategory] = {
    "general": {
        "title": "❓ Preguntas Generales",
        "questions": {
            "faq_what": "¿Qué son los cursos de IA?",
            "faq_who": "¿Para quién son estos cursos?",
            "faq_prereq": "¿Necesito conocimientos previos?"
        }
    },
    "technical": {
        "title": "💻 Preguntas Técnicas",
        "questions": {
            "faq_tech_req": "¿Qué requisitos técnicos necesito?",
            "faq_software": "¿Qué software utilizaremos?",
            "faq_practice": "¿Habrá ejercicios prácticos?"
        }
    },
    "logistics": {
        "title": "📅 Logística y Horarios",
        "questions": {
            "faq_schedule": "¿Cuál es el horario de clases?",
            "faq_duration": "¿Cuánto dura el curso?",
            "faq_cert": "¿Recibo certificación?"
        }
    }
}

@handle_telegram_errors
async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra las categorías de preguntas frecuentes.

    Args:
        update: Objeto Update de Telegram
        context: Contexto del bot
    """
    if not update.effective_chat:
        return

    message = """📚 Preguntas Frecuentes

Selecciona una categoría para ver las preguntas:"""

    keyboard = [
        [InlineKeyboardButton(
            FAQ_DATA["general"]["title"],
            callback_data="faq_cat_general"
        )],
        [InlineKeyboardButton(
            FAQ_DATA["technical"]["title"],
            callback_data="faq_cat_technical"
        )],
        [InlineKeyboardButton(
            FAQ_DATA["logistics"]["title"],
            callback_data="faq_cat_logistics"
        )],
        [InlineKeyboardButton("🔙 Volver al menú", callback_data="menu_main")]
    ]

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@handle_telegram_errors
async def handle_faq_category(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    category: str
) -> None:
    """
    Muestra las preguntas de una categoría específica.

    Args:
        update: Objeto Update de Telegram
        context: Contexto del bot
        category: Categoría de preguntas a mostrar
    """
    if not update.effective_chat or not update.callback_query:
        return

    query = update.callback_query
    cat_data = FAQ_DATA.get(category.replace("faq_cat_", ""))

    if not cat_data:
        await query.answer("Categoría no encontrada")
        return

    message = f"{cat_data['title']}\n\nSelecciona una pregunta:"

    keyboard = [
        [InlineKeyboardButton(text, callback_data=callback)]
        for callback, text in cat_data["questions"].items()
    ]
    keyboard.append([
        InlineKeyboardButton("🔙 Volver a categorías", callback_data="faq_back")
    ])

    await query.edit_message_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@handle_telegram_errors
async def handle_faq_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    question: str
) -> None:
    """
    Muestra la respuesta a una pregunta específica.

    Args:
        update: Objeto Update de Telegram
        context: Contexto del bot
        question: Identificador de la pregunta a responder
    """
    if not update.effective_chat or not update.callback_query:
        return

    query = update.callback_query
    answers = get_faq_answers()
    answer = answers.get(question, "Lo siento, no encontré la respuesta a esa pregunta.")

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Volver a preguntas", callback_data="faq_back")
    ]])

    await query.edit_message_text(
        text=answer,
        reply_markup=keyboard,
        parse_mode='HTML'
    )

def get_faq_answers() -> Dict[str, str]:
    """
    Retorna el diccionario de respuestas a preguntas frecuentes.

    Returns:
        Diccionario con las respuestas a cada pregunta
    """
    return {
        "faq_what": """Los cursos de IA son programas especializados que te enseñan a:

• Comprender los fundamentos de la IA
• Implementar soluciones prácticas
• Optimizar procesos con tecnología
• Crear aplicaciones inteligentes""",
        "faq_who": """Estos cursos están diseñados para:

• Profesionales que quieren actualizarse
• Emprendedores buscando innovar
• Estudiantes interesados en tecnología
• Cualquier persona curiosa por la IA""",
        "faq_prereq": """No necesitas conocimientos previos específicos.
Solo necesitas:

• Computadora con internet
• Ganas de aprender
• Dedicación al curso""",
        "faq_tech_req": """Requisitos técnicos básicos:

• Computadora (Windows/Mac/Linux)
• Conexión estable a internet
• Navegador web actualizado
• 4GB RAM mínimo""",
        "faq_software": """Utilizaremos herramientas accesibles:

• Plataformas web de IA
• Editores de código online
• Jupyter Notebooks
• Google Colab""",
        "faq_practice": """¡Sí! El curso es muy práctico:

• Ejercicios en cada módulo
• Proyectos reales
• Feedback personalizado
• Práctica guiada""",
        "faq_schedule": """Horarios flexibles:

• Clases en vivo: 2 veces por semana
• Grabaciones disponibles
• Horarios adaptables
• Soporte continuo""",
        "faq_duration": """Duración del curso:

• 12 semanas en total
• 2 horas por clase
• Acceso de por vida
• Ritmo personalizado""",
        "faq_cert": """Certificación incluida:

• Certificado digital
• Avalado por la institución
• Válido internacionalmente
• Verificable online"""
    } 