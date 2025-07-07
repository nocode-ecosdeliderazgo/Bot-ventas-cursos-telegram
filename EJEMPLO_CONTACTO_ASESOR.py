
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from core.services.database import DatabaseService
from core.utils.memory import GlobalMemory
from config.settings import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# --- Funciones de Ayuda ---

async def get_all_courses(db: DatabaseService):
    """Obtiene todos los cursos de la base de datos."""
    try:
        async with db.pool.acquire() as connection:
            rows = await connection.fetch("SELECT id, name FROM courses")
            return [{"id": row['id'], "name": row['name']} for row in rows]
    except Exception as e:
        logger.error(f"Error al obtener los cursos: {e}")
        return []

def send_advisor_email(user_data: dict):
    """Envía un correo electrónico a un asesor con los datos del lead."""
    try:
        sender_email = settings.EMAIL_HOST_USER
        receiver_email = "destinatario@example.com"  # Cambiar por el email del asesor
        password = settings.EMAIL_HOST_PASSWORD

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

        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
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
    """Maneja la selección de un curso por parte del usuario."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    memory = GlobalMemory().get_lead_memory(user_id)
    
    course_id = query.data.split('_')[-1]
    memory.selected_course = course_id
    
    # Aquí podrías obtener y guardar el nombre del curso también si lo necesitas
    db = DatabaseService(settings.DATABASE_URL)
    await db.connect()
    course_details = await db.get_course_details(course_id) # Suponiendo que tienes esta función
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
        # Simular un callback para continuar el flujo
        fake_update = Update(update.update_id, callback_query=update.message)
        fake_update.callback_query.from_user = update.message.from_user
        await request_missing_info(fake_update, context)

    elif memory.stage == "awaiting_phone":
        memory.phone = text
        memory.stage = ""
        GlobalMemory().save_lead_memory(user_id, memory)
        # Simular un callback para continuar el flujo
        fake_update = Update(update.update_id, callback_query=update.message)
        fake_update.callback_query.from_user = update.message.from_user
        await confirm_contact_details(fake_update, context)


async def confirm_contact_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra al usuario los datos recopilados y pide confirmación."""
    query = update.callback_query
    user_id = str(query.from_user.id)
    memory = GlobalMemory().get_lead_memory(user_id)

    # Asumiendo que ya tienes el nombre del curso en memoria
    if not hasattr(memory, 'course_name') or not memory.course_name:
        db = DatabaseService(settings.DATABASE_URL)
        await db.connect()
        course_details = await db.get_course_details(memory.selected_course)
        await db.disconnect()
        memory.course_name = course_details.get('name') if course_details else "No especificado"
        GlobalMemory().save_lead_memory(user_id, memory)

    message = f"""
    Por favor, confirma que tus datos son correctos:
    
    - Nombre: {memory.name}
    - Email: {memory.email}
    - Teléfono: {memory.phone}
    - Curso: {memory.course_name}
    
    ¿Son correctos estos datos?
    """
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
            await query.edit_message_text("¡Gracias! Un asesor se pondrá en contacto contigo a la brevedad.")
        else:
            await query.edit_message_text("Lo siento, hubo un error al enviar tu solicitud. Por favor, inténtalo de nuevo más tarde.")
    
    elif query.data == "confirm_contact_no":
        # Borrar datos para volver a pedirlos
        memory.email = None
        memory.phone = None
        memory.selected_course = None
        memory.course_name = None
        GlobalMemory().save_lead_memory(user_id, memory)
        await request_missing_info(update, context)

