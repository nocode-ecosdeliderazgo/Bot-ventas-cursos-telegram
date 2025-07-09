"""Manejadores para el flujo de cursos - VERSIÓN MIGRADA."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from core.utils.error_handlers import handle_telegram_errors
from core.utils.memory import GlobalMemory
from core.services.database import DatabaseService
from core.services.courseService import CourseService
from core.utils.course_templates import CourseTemplates
from config.settings import settings

logger = logging.getLogger(__name__)

# Datos de cursos reales - MANTENIDO para compatibilidad
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
    """
    Muestra la lista de cursos disponibles.
    MIGRADO: Obtiene cursos desde ai_courses
    """
    if not update.effective_chat:
        return
        
    try:
        # Obtener cursos desde nueva estructura de base de datos
        db = DatabaseService(settings.DATABASE_URL)
        await db.connect()
        course_service = CourseService(db)
        
        # Buscar todos los cursos publicados
        courses = await course_service.searchCourses("")
        await db.disconnect()
        
        if not courses:
            # Usar datos estáticos como respaldo
            message = """🎓 Cursos Disponibles

Selecciona un curso para ver más detalles:"""
            
            keyboard = [
                [InlineKeyboardButton(f"{course['name']} ({course['level']})", 
                                    callback_data=f"course_{code}")]
                for code, course in COURSES.items()
            ]
            keyboard.append([InlineKeyboardButton("🔙 Volver al menú", callback_data="menu_main")])
        else:
            # Usar cursos desde base de datos
            message = f"""🎓 Cursos Disponibles ({len(courses)} cursos)

Selecciona un curso para ver más detalles:"""
            
            keyboard = []
            for course in courses[:10]:  # Mostrar máximo 10 cursos
                button_text = f"{course['name']} ({course.get('level', 'N/A')})"
                callback_data = f"course_db_{course['id']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            keyboard.append([InlineKeyboardButton("🔙 Volver al menú", callback_data="menu_main")])
            
    except Exception as e:
        logger.error(f"Error obteniendo cursos: {e}")
        # Fallback a datos estáticos
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
    """
    Maneja la selección de un curso específico.
    MIGRADO: Usa courseService migrado y plantillas actualizadas
    """
    if not update.effective_chat or not update.callback_query:
        return
        
    query = update.callback_query
    
    # Determinar si es un curso de base de datos o estático
    if callback_data.startswith("course_db_"):
        # Curso desde base de datos
        course_id = callback_data.replace("course_db_", "")
        await handle_db_course_selection(update, context, course_id)
    else:
        # Curso estático (fallback)
        course_code = callback_data.replace("course_", "")
        await handle_static_course_selection(update, context, course_code)

async def handle_db_course_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, course_id: str) -> None:
    """
    Maneja la selección de un curso desde la base de datos.
    MIGRADO: Usa nueva estructura de base de datos
    """
    query = update.callback_query
    
    try:
        # Obtener detalles del curso desde nueva estructura
        db = DatabaseService(settings.DATABASE_URL)
        await db.connect()
        course_service = CourseService(db)
        
        course_details = await course_service.getCourseDetails(course_id)
        await db.disconnect()
        
        if not course_details:
            await query.answer("Curso no encontrado")
            return
        
        # Guardar curso seleccionado en memoria
        user_id = str(query.from_user.id)
        memory = GlobalMemory().get_lead_memory(user_id)
        if memory:
            memory.selected_course = course_id
            GlobalMemory().save_lead_memory(user_id, memory)
        
        # Usar plantillas migradas para formatear información
        message = CourseTemplates.format_course_details_with_benefits(course_details)
        
        keyboard = [
            [InlineKeyboardButton("📱 Contactar Asesor", callback_data="contact_course")],
            [InlineKeyboardButton("📚 Ver Sesiones", callback_data=f"show_sessions_{course_id}")],
            [InlineKeyboardButton("💰 Ver Precios", callback_data=f"show_pricing_{course_id}")],
            [InlineKeyboardButton("🔙 Ver otros cursos", callback_data="menu_courses")]
        ]
        
        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo detalles del curso {course_id}: {e}")
        await query.answer("Error obteniendo información del curso")

async def handle_static_course_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, course_code: str) -> None:
    """
    Maneja la selección de un curso estático (fallback).
    MANTENIDO: Para compatibilidad con cursos hardcodeados
    """
    query = update.callback_query
    course = COURSES.get(course_code)
    
    if not course:
        await query.answer("Curso no encontrado")
        return
    
    # Guardar curso seleccionado en memoria
    user_id = str(query.from_user.id)
    memory = GlobalMemory().get_lead_memory(user_id)
    if memory:
        memory.selected_course = course['id']
        GlobalMemory().save_lead_memory(user_id, memory)
        
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

@handle_telegram_errors
async def handle_course_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE, course_id: str) -> None:
    """
    Muestra las sesiones de un curso específico.
    NUEVO: Funcionalidad agregada para nueva estructura
    """
    if not update.effective_chat or not update.callback_query:
        return
        
    query = update.callback_query
    
    try:
        # Obtener sesiones del curso desde nueva estructura
        db = DatabaseService(settings.DATABASE_URL)
        await db.connect()
        course_service = CourseService(db)
        
        course_details = await course_service.getCourseDetails(course_id)
        await db.disconnect()
        
        if not course_details or not course_details.get('sessions'):
            await query.answer("No se encontraron sesiones para este curso")
            return
        
        # Usar plantillas migradas para formatear sesiones
        message = CourseTemplates.format_course_modules_detailed(course_details)
        
        keyboard = [
            [InlineKeyboardButton("🔙 Volver al curso", callback_data=f"course_db_{course_id}")],
            [InlineKeyboardButton("📱 Contactar Asesor", callback_data="contact_course")]
        ]
        
        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo sesiones del curso {course_id}: {e}")
        await query.answer("Error obteniendo sesiones del curso")

@handle_telegram_errors
async def handle_course_pricing(update: Update, context: ContextTypes.DEFAULT_TYPE, course_id: str) -> None:
    """
    Muestra información de precios de un curso específico.
    NUEVO: Funcionalidad agregada para nueva estructura
    """
    if not update.effective_chat or not update.callback_query:
        return
        
    query = update.callback_query
    
    try:
        # Obtener detalles del curso desde nueva estructura
        db = DatabaseService(settings.DATABASE_URL)
        await db.connect()
        course_service = CourseService(db)
        
        course_details = await course_service.getCourseDetails(course_id)
        await db.disconnect()
        
        if not course_details:
            await query.answer("Curso no encontrado")
            return
        
        # Usar plantillas migradas para formatear precios
        message = CourseTemplates.format_course_pricing(course_details)
        
        keyboard = [
            [InlineKeyboardButton("💳 Inscribirme", callback_data=f"enroll_{course_id}")],
            [InlineKeyboardButton("🔙 Volver al curso", callback_data=f"course_db_{course_id}")],
            [InlineKeyboardButton("📱 Contactar Asesor", callback_data="contact_course")]
        ]
        
        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo precios del curso {course_id}: {e}")
        await query.answer("Error obteniendo información de precios")
