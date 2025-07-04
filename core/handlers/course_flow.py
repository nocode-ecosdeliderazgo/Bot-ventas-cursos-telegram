"""Manejadores para el flujo de cursos."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from core.utils.error_handlers import handle_telegram_errors
from core.utils.memory import GlobalMemory

logger = logging.getLogger(__name__)

# Datos de ejemplo de cursos
COURSES = {
    "ia_basic": {
        "name": "Fundamentos de IA",
        "description": "Curso básico para comenzar en el mundo de la IA",
        "price": 99,
        "duration": "4 semanas",
        "level": "Principiante"
    },
    "ia_inter": {
        "name": "IA Intermedia",
        "description": "Profundiza en algoritmos y aplicaciones de IA",
        "price": 199,
        "duration": "8 semanas",
        "level": "Intermedio"
    },
    "ia_adv": {
        "name": "IA Avanzada",
        "description": "Domina técnicas avanzadas y proyectos complejos",
        "price": 299,
        "duration": "12 semanas",
        "level": "Avanzado"
    }
}

@handle_telegram_errors
async def show_courses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra la lista de cursos disponibles."""
    if not update.effective_chat:
        return
        
    message = """🎓 Cursos Disponibles

Selecciona un curso para ver más detalles:"""
    
    keyboard = [
        [InlineKeyboardButton(f"{course['name']} ({course['level']})", 
                            callback_data=f"course_{code}")]
        for code, course in COURSES.items()
    ]
    keyboard.append([InlineKeyboardButton("🔙 Volver al menú", callback_data="menu_main")])
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@handle_telegram_errors
async def handle_course_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Maneja la selección de un curso específico."""
    if not update.effective_chat or not update.callback_query:
        return
        
    query = update.callback_query
    course_code = callback_data.replace("course_", "")
    course = COURSES.get(course_code)
    
    if not course:
        await query.answer("Curso no encontrado")
        return
        
    message = f"""📚 {course['name']}

{course['description']}

📋 Detalles del curso:
• Nivel: {course['level']}
• Duración: {course['duration']}
• Inversión: ${course['price']} USD

¿Te gustaría recibir más información?"""
    
    keyboard = [
        [InlineKeyboardButton("📱 Contactar Asesor", callback_data="contact_course")],
        [InlineKeyboardButton("🔙 Ver otros cursos", callback_data="menu_courses")]
    ]
    
    await query.edit_message_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    ) 