"""Manejadores para el flujo de contacto - VERSIÓN MIGRADA."""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from core.services.database import DatabaseService
from core.utils.error_handlers import handle_telegram_errors
from core.utils.memory import GlobalMemory
from core.utils.navigation import show_main_menu
from config.settings import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

@handle_telegram_errors
async def show_contact_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra las opciones de contacto."""
    if not update.effective_chat:
        return
        
    message = """¿Cómo prefieres que te contactemos? 📱

Elige la opción que más te convenga:"""
    
    keyboard = [
        [InlineKeyboardButton("📞 Llamada telefónica", callback_data="contact_call")],
        [InlineKeyboardButton("📱 WhatsApp", callback_data="contact_whatsapp")],
        [InlineKeyboardButton("📧 Email", callback_data="contact_email")],
        [InlineKeyboardButton("🔙 Volver al menú", callback_data="menu_main")]
    ]
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Funciones de Ayuda ---

async def get_all_courses(db: DatabaseService):
    """
    Obtiene todos los cursos de la base de datos.
    MIGRADO: Usa ai_courses en lugar de courses
    """
    try:
        async with db.pool.acquire() as connection:
            # Cambio: courses → ai_courses
            rows = await connection.fetch("SELECT id, name FROM ai_courses WHERE status = 'publicado'")
            return [{"id": row['id'], "name": row['name']} for row in rows]
    except Exception as e:
        logger.error(f"Error al obtener los cursos: {e}")
        return []

def send_advisor_email(user_data: dict) -> bool:
    """Envía un correo electrónico a un asesor con los datos del lead."""
    try:
        sender_email = settings.SMTP_USERNAME
        receiver_email = settings.ADVISOR_EMAIL
        password = settings.SMTP_PASSWORD
        
        logger.info(f"Enviando email desde {sender_email} hacia {receiver_email}")

        subject = f"Nuevo Lead Interesado: {user_data.get('name', 'N/A')}"
        body = f"""
        Se ha recibido un nuevo lead interesado en un curso.

        Detalles del Lead:
        - Nombre: {user_data.get('name', 'N/A')}
        - Email: {user_data.get('email', 'N/A')}
        - Teléfono: {user_data.get('phone', 'N/A')}
        - Curso de Interés: {user_data.get('course_name', 'N/A')}

        Por favor, contactar a la brevedad.
        """

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        
        logger.info(f"Correo de lead enviado exitosamente a {receiver_email}")
        return True
    except Exception as e:
        logger.error(f"Error al enviar el correo al asesor: {e}")
        return False

# --- Manejadores de Flujo ---

async def start_contact_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo para contactar a un asesor."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    memory = GlobalMemory().get_lead_memory(user_id)

    if not memory.email or not memory.phone or not memory.selected_course:
        await request_missing_info(update, context)
    else:
        await confirm_contact_details(update, context)

async def request_missing_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicita la información que falta al usuario."""
    query = update.callback_query
    user_id = str(query.from_user.id)
    memory = GlobalMemory().get_lead_memory(user_id)
    
    if not memory.selected_course:
        await request_course_selection(update, context)
    elif not memory.email:
        memory.stage = "awaiting_email"
        GlobalMemory().save_lead_memory(user_id, memory)
        await query.edit_message_text("Por favor, introduce tu correo electrónico:")
    elif not memory.phone:
        memory.stage = "awaiting_phone"
        GlobalMemory().save_lead_memory(user_id, memory)
        await query.edit_message_text("Por favor, introduce tu número de teléfono:")

async def request_course_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los cursos para que el usuario seleccione uno."""
    query = update.callback_query
    db = DatabaseService(settings.DATABASE_URL)
    await db.connect()
    courses = await get_all_courses(db)
    await db.disconnect()

    if not courses:
        await query.edit_message_text("Lo siento, no pude cargar los cursos en este momento.")
        return

    keyboard = []
    for course in courses:
        keyboard.append([InlineKeyboardButton(course['name'], callback_data=f"select_course_{course['id']}")])    
    
    await query.edit_message_text(
        "Por favor, selecciona el curso de tu interés:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_course_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja la selección de un curso por parte del usuario.
    MIGRADO: Usa courseService migrado
    """
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    memory = GlobalMemory().get_lead_memory(user_id)
    
    course_id = query.data.split('_')[-1]
    memory.selected_course = course_id
    
    # Obtener el nombre del curso usando el servicio migrado
    db = DatabaseService(settings.DATABASE_URL)
    await db.connect()
    # Usar el servicio migrado
    from core.services.courseService import CourseService
    course_service = CourseService(db)
    course_details = await course_service.getCourseDetails(course_id)
    await db.disconnect()
    
    if course_details:
        memory.course_name = course_details.get('name')

    GlobalMemory().save_lead_memory(user_id, memory)
    
    await request_missing_info(update, context)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la entrada de texto del usuario para email y teléfono."""
    user_id = str(update.message.from_user.id)
    memory = GlobalMemory().get_lead_memory(user_id)
    text = update.message.text

    if memory.stage == "awaiting_email":
        memory.email = text
        memory.stage = ""
        GlobalMemory().save_lead_memory(user_id, memory)
        await update.message.reply_text("Email registrado. Verificando información...")
        # Continuar el flujo
        await request_missing_info_after_input(update, context)

    elif memory.stage == "awaiting_phone":
        memory.phone = text
        memory.stage = ""
        GlobalMemory().save_lead_memory(user_id, memory)
        await update.message.reply_text("Teléfono registrado. Verificando información...")
        # Continuar el flujo
        await confirm_contact_details_after_input(update, context)

async def request_missing_info_after_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Continúa el flujo después de recibir el email."""
    user_id = str(update.message.from_user.id)
    memory = GlobalMemory().get_lead_memory(user_id)
    
    if not memory.phone:
        memory.stage = "awaiting_phone"
        GlobalMemory().save_lead_memory(user_id, memory)
        await update.message.reply_text("Por favor, introduce tu número de teléfono:")
    else:
        await confirm_contact_details_after_input(update, context)

async def confirm_contact_details_after_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Muestra confirmación después de recibir datos por texto.
    MIGRADO: Usa courseService migrado
    """
    user_id = str(update.message.from_user.id)
    memory = GlobalMemory().get_lead_memory(user_id)

    # Obtener nombre del curso si no está disponible
    if not hasattr(memory, 'course_name') or not memory.course_name:
        db = DatabaseService(settings.DATABASE_URL)
        await db.connect()
        # Usar el servicio migrado
        from core.services.courseService import CourseService
        course_service = CourseService(db)
        course_details = await course_service.getCourseDetails(memory.selected_course)
        await db.disconnect()
        memory.course_name = course_details.get('name') if course_details else "No especificado"
        GlobalMemory().save_lead_memory(user_id, memory)

    message = f"""Por favor, confirma que tus datos son correctos:
    
- Nombre: {memory.name}
- Email: {memory.email}
- Teléfono: {memory.phone}
- Curso: {memory.course_name}
    
¿Son correctos estos datos?"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Sí, son correctos", callback_data="confirm_contact_yes")],
        [InlineKeyboardButton("✏️ No, quiero editarlos", callback_data="confirm_contact_no")]
    ]
    
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

async def confirm_contact_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Muestra al usuario los datos recopilados y pide confirmación.
    MIGRADO: Usa courseService migrado
    """
    query = update.callback_query
    user_id = str(query.from_user.id)
    memory = GlobalMemory().get_lead_memory(user_id)

    # Obtener nombre del curso si no está disponible
    if not hasattr(memory, 'course_name') or not memory.course_name:
        db = DatabaseService(settings.DATABASE_URL)
        await db.connect()
        # Usar el servicio migrado
        from core.services.courseService import CourseService
        course_service = CourseService(db)
        course_details = await course_service.getCourseDetails(memory.selected_course)
        await db.disconnect()
        memory.course_name = course_details.get('name') if course_details else "No especificado"
        GlobalMemory().save_lead_memory(user_id, memory)

    message = f"""Por favor, confirma que tus datos son correctos:
    
- Nombre: {memory.name}
- Email: {memory.email}
- Teléfono: {memory.phone}
- Curso: {memory.course_name}
    
¿Son correctos estos datos?"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Sí, son correctos", callback_data="confirm_contact_yes")],
        [InlineKeyboardButton("✏️ No, quiero editarlos", callback_data="confirm_contact_no")]
    ]
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la confirmación final del usuario."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    memory = GlobalMemory().get_lead_memory(user_id)

    if query.data == "confirm_contact_yes":
        user_data = {
            "name": memory.name,
            "email": memory.email,
            "phone": memory.phone,
            "course_name": memory.course_name
        }
        if send_advisor_email(user_data):
            # 🔄 LIMPIAR STAGE PARA REACTIVAR EL AGENTE
            memory.stage = ""
            GlobalMemory().save_lead_memory(user_id, memory)
            logger.info(f"✅ Flujo de contacto completado - agente reactivado para usuario {user_id}")
            await query.edit_message_text("¡Gracias! Un asesor se pondrá en contacto contigo a la brevedad.")
        else:
            await query.edit_message_text("Lo siento, hubo un error al enviar tu solicitud. Por favor, inténtalo de nuevo más tarde.")
    
    elif query.data == "confirm_contact_no":
        # Borrar datos para volver a pedirlos
        memory.email = None
        memory.phone = None
        memory.selected_course = None
        memory.course_name = None
        # 🔄 LIMPIAR STAGE PARA REACTIVAR EL AGENTE
        memory.stage = ""
        GlobalMemory().save_lead_memory(user_id, memory)
        logger.info(f"🔄 Flujo de contacto cancelado - agente reactivado para usuario {user_id}")
        await request_missing_info(update, context)

@handle_telegram_errors
async def handle_contact_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Maneja la selección del método de contacto."""
    if not update.effective_chat or not update.callback_query:
        return
        
    query = update.callback_query
    
    if callback_data == "contact_call":
        message = """Por favor, envíame tu número de teléfono para que podamos llamarte.
        
📱 Formato: +XX XXXXXXXXXX"""
        
    elif callback_data == "contact_whatsapp":
        message = """Por favor, envíame tu número de WhatsApp.
        
📱 Formato: +XX XXXXXXXXXX"""
        
    elif callback_data == "contact_email":
        message = """Por favor, envíame tu dirección de email.
        
📧 Formato: tu@email.com"""
        
    else:  # menu_main
        await show_main_menu(update, context)
        return
    
    await query.edit_message_text(
        text=message,
        reply_markup=None
    ) 