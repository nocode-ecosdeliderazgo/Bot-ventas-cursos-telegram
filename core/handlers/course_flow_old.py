"""Manejadores para el flujo de cursos."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from core.utils.error_handlers import handle_telegram_errors
from core.utils.memory import GlobalMemory

logger = logging.getLogger(__name__)

# Datos de cursos reales
COURSES = {
    "ia_chatgpt": {
        "id": "a392bf83-4908-4807-89a9-95d0acc807c9",
        "name": "ChatGPT para Profesionales",
        "description": "Domina el uso profesional de ChatGPT y la IA generativa",
        "price": 199,
        "duration": "8 semanas",
        "level": "Intermedio"
    },
    "prompts": {
        "id": "b00f3d1c-e876-4bac-b734-2715110440a0",
        "name": "Ingeniería de Prompts",
        "description": "Optimiza tus prompts para obtener mejores resultados con IA",
        "price": 149,
        "duration": "6 semanas",
        "level": "Intermedio-Avanzado"
    },
    "imagenes": {
        "id": "2715110440a0-b734-b00f3d1c-e876-4bac",
        "name": "Generación de Imágenes con IA",
        "description": "Crea imágenes profesionales usando herramientas de IA",
        "price": 179,
        "duration": "6 semanas",
        "level": "Intermedio"
    },
    "automatizacion": {
        "id": "4bac-2715110440a0-b734-b00f3d1c-e876",
        "name": "Automatización Inteligente",
        "description": "Automatiza tareas y procesos usando asistentes de IA",
        "price": 229,
        "duration": "10 semanas",
        "level": "Avanzado"
    },
    "nuevo": {
        "id": "d7ab3f21-5c6e-4d89-91f3-7a2b4e5c8d9f",
        "name": "Nombre del Nuevo Curso",
        "description": "Descripción del nuevo curso",
        "price": 0,  # Actualizar con el precio correcto
        "duration": "Por definir",
        "level": "Por definir"
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