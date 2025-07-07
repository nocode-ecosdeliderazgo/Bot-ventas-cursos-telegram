"""Bot de ventas para Telegram que utiliza un agente inteligente para convertir leads."""

import os
import logging
import asyncio
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from core.services.database import DatabaseService
from core.agents.agent_tools import AgentTools
from core.agents.smart_sales_agent import SmartSalesAgent
from core.utils.memory import GlobalMemory
from core.utils.message_parser import extract_hashtags, get_course_from_hashtag
from core.handlers.ads_flow import AdsFlowHandler
from config.settings import settings

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
        
    ]
)
logger = logging.getLogger(__name__)

class VentasBot:
    def __init__(self):
        # Verificar variables de entorno
        if not settings.DATABASE_URL:
            raise ValueError("DATABASE_URL no encontrado en variables de entorno")
        # Inicializar servicios
        self.db = DatabaseService(settings.DATABASE_URL)
        self.agent_tools = None
        self.ventas_bot = None
        self.ads_flow_handler = None
        self.global_memory = GlobalMemory()
        self.templates = None

    async def setup(self):
        # Inicializar el pool de conexiones
        await self.db.connect()
        # Ahora sí, inicializar los servicios que usan la base de datos
        self.agent_tools = AgentTools(self.db, None)  # Se actualizará con la API de Telegram
        self.ventas_bot = SmartSalesAgent(self.db, self.agent_tools)
        self.ads_flow_handler = AdsFlowHandler(self.db, self.agent_tools)
        
        # Importar templates para privacidad
        from core.utils.message_templates import MessageTemplates
        self.templates = MessageTemplates()

    async def handle_message(self, update: Update, context):
        """
        Maneja todos los mensajes entrantes.
        Detecta si el mensaje viene de un anuncio y lo procesa adecuadamente.
        """
        if self.ventas_bot is None:
            await self.setup()
        # Ahora sí, seguro que self.ventas_bot está inicializado
        message = None
        try:
            message = update.message
            if not message or not message.text:
                return
                
            user = message.from_user
            if not user:
                return
                
            # Actualizar memoria global
            self.global_memory.set_current_lead(
                str(user.id),
                name=user.first_name or '',
                username=user.username or ''
            )
            
            # NUEVO: Detección de hashtags para flujo de anuncios
            hashtags = extract_hashtags(message.text)
            logger.info(f"Hashtags detectados: {hashtags}")
            
            # Verificar si es un mensaje de anuncio (#curso: y #anuncio:)
            has_course_hashtag = any(tag.startswith('curso:') or tag.startswith('CURSO_') for tag in hashtags)
            has_ad_hashtag = any(tag.startswith('anuncio:') or tag.startswith('ADSIM_') for tag in hashtags)
            
            # Preparar datos del mensaje y usuario
            message_data = {
                'text': message.text,
                'chat_id': message.chat_id,
                'message_id': message.message_id,
                'from': {
                    'id': user.id,
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                    'username': user.username or ''
                }
            }
            
            user_data = {
                'id': user.id,
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'username': user.username or ''
            }
            
            # Obtener memoria del usuario para decidir routing
            user_memory = self.global_memory.get_lead_memory(str(user.id))
            
            # Verificar si el usuario está en proceso de proporcionar su nombre
            if user_memory.privacy_accepted and user_memory.stage == "waiting_for_name":
                # El usuario está proporcionando su nombre
                response, keyboard = await self.handle_name_input(message_data, user_data)
            elif has_course_hashtag and has_ad_hashtag:
                # Flujo de anuncios - verificar estado del usuario
                if user_memory.privacy_accepted and user_memory.name:
                    # Usuario ya completó el flujo anteriormente - mostrar directamente secuencia post-nombre
                    logger.info(f"Usuario {user.id} con memoria existente, mostrando secuencia directa")
                    response, keyboard = await self.handle_returning_user_with_ads(user_data)
                else:
                    # Usuario nuevo o incompleto - procesar con ads_flow normal
                    logger.info(f"Usuario {user.id} viene de anuncio, procesando con ads_flow")
                    response, keyboard = await self.handle_ad_flow(message_data, user_data, hashtags)
            else:
                # Flujo conversacional normal
                logger.info(f"Usuario {user.id} en conversación normal")
                if self.ventas_bot:
                    response, keyboard = await self.ventas_bot.handle_conversation(message_data, user_data)
                else:
                    response, keyboard = "Error: Bot no inicializado correctamente.", None
            
            # Manejar respuesta que puede ser string o lista de diccionarios
            if isinstance(response, str):
                # Enviar respuesta de texto
                if keyboard:
                    await message.reply_text(
                        response,
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                else:
                    await message.reply_text(
                        response,
                        parse_mode='Markdown'
                    )
            elif isinstance(response, list):
                # Enviar múltiples mensajes (para archivos multimedia)
                for item in response:
                    if item.get('type') == 'text':
                        await message.reply_text(
                            item['content'],
                            parse_mode='Markdown'
                        )
                    elif item.get('type') == 'image':
                        # Manejar tanto URLs como archivos locales
                        if item.get('url'):
                            await message.reply_photo(
                                photo=item['url'],
                                caption=item.get('caption', '')
                            )
                        elif item.get('path'):
                            try:
                                with open(item['path'], 'rb') as img_file:
                                    await message.reply_photo(
                                        photo=img_file,
                                        caption=item.get('caption', '')
                                    )
                            except FileNotFoundError:
                                logger.warning(f"Archivo de imagen no encontrado: {item['path']}")
                    elif item.get('type') == 'document':
                        # Manejar tanto URLs como archivos locales
                        if item.get('url'):
                            try:
                                await message.reply_document(
                                    document=item['url'],
                                    caption=item.get('caption', '')
                                )
                            except Exception as e:
                                logger.error(f"Error enviando documento desde URL: {e}")
                                await message.reply_text(f"❌ Error enviando documento: {item.get('caption', 'Documento')}")
                        elif item.get('path'):
                            try:
                                # Verificar que el archivo existe
                                if not os.path.exists(item['path']):
                                    logger.warning(f"Archivo no encontrado: {item['path']}")
                                    await message.reply_text(f"❌ Archivo no encontrado: {item.get('caption', 'Documento')}")
                                else:
                                    # Verificar el tamaño del archivo
                                    file_size = os.path.getsize(item['path'])
                                    if file_size > 50 * 1024 * 1024:  # 50MB limit for Telegram
                                        logger.warning(f"Archivo muy grande: {item['path']} ({file_size} bytes)")
                                        await message.reply_text(f"❌ Archivo muy grande para enviar: {item.get('caption', 'Documento')}")
                                    else:
                                        with open(item['path'], 'rb') as doc_file:
                                            await message.reply_document(
                                                document=doc_file,
                                                caption=item.get('caption', ''),
                                                filename=os.path.basename(item['path'])
                                            )
                            except FileNotFoundError:
                                logger.warning(f"Archivo PDF no encontrado: {item['path']}")
                                await message.reply_text(f"❌ Archivo no encontrado: {item.get('caption', 'Documento')}")
                            except Exception as e:
                                logger.error(f"Error enviando documento {item['path']}: {e}")
                                await message.reply_text(f"❌ Error enviando documento: {item.get('caption', 'Documento')}")

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            if message:
                await message.reply_text(
                    "Lo siento, hubo un error procesando tu mensaje. Por favor, intenta nuevamente."
                )

    async def handle_returning_user_with_ads(self, user_data: dict):
        """
        Maneja usuarios que ya completaron el flujo pero envían hashtags de anuncio nuevamente.
        Muestra directamente la secuencia post-nombre usando información de memoria.
        """
        try:
            user_id = str(user_data['id'])
            user_memory = self.global_memory.get_lead_memory(user_id)
            
            # Usar nombre de memoria
            user_name = user_memory.name or user_data.get('first_name', 'Usuario')
            
            logger.info(f"Usuario {user_id} regresando con memoria existente, nombre: {user_name}")
            
            # Preparar secuencia de bienvenida personalizada + archivos (igual que handle_name_input)
            welcome_message = f"""¡Hola de nuevo {user_name}! 😊

Soy Brenda, parte del equipo automatizado de Aprenda y Aplique IA y te voy a ayudar.

A continuación te comparto toda la información del curso:"""
            
            # Obtener información del curso desde Supabase
            course_id = "a392bf83-4908-4807-89a9-95d0acc807c9"  # ID del curso IA ChatGPT
            course_info_text = ""
            
            try:
                if self.ads_flow_handler:
                    from core.services.courseService import CourseService
                    course_service = CourseService(self.ads_flow_handler.db)
                    course_data = await course_service.getCourseBasicInfo(course_id)
                    if course_data:
                        # Construir mensaje dinámicamente desde la base de datos
                        course_info_text = await self._build_course_info_message(course_data)
                    else:
                        # Fallback si no se encuentra el curso
                        course_info_text = """🎓 dato no encontrado

dato no encontrado

⏱️ Duración: dato no encontrado
📊 Nivel: dato no encontrado
💰 Inversión: dato no encontrado


¿Qué te gustaría saber más sobre este curso?"""
            except Exception as e:
                logger.error(f"Error obteniendo datos del curso: {e}")
                # Fallback si hay error
                course_info_text = """🎓 dato no encontrado

dato no encontrado

⏱️ Duración: dato no encontrado
📊 Nivel: dato no encontrado
💰 Inversión: dato no encontrado


¿Qué te gustaría saber más sobre este curso?"""
            
            # Preparar respuesta con archivos de data + información del curso
            response = [
                {"type": "text", "content": welcome_message},
                {"type": "document", "path": "data/pdf_prueba.pdf", "caption": "📄 Aquí tienes el PDF descriptivo del curso"},
                {"type": "image", "path": "data/imagen_prueba.jpg", "caption": "🎯 Imagen del curso"},
                {"type": "text", "content": course_info_text}
            ]
            
            return response, None
            
        except Exception as e:
            logger.error(f"Error en handle_returning_user_with_ads: {e}")
            return "Error procesando tu solicitud. Por favor, intenta nuevamente.", None

    async def handle_name_input(self, message_data: dict, user_data: dict):
        """
        Maneja la entrada del nombre del usuario después de aceptar privacidad.
        """
        try:
            user_id = str(user_data['id'])
            user_name = message_data['text'].strip()
            
            # Actualizar memoria con el nombre
            user_memory = self.global_memory.get_lead_memory(user_id)
            user_memory.name = user_name
            user_memory.stage = "name_collected"
            self.global_memory.save_lead_memory(user_id, user_memory)
            
            logger.info(f"Nombre almacenado para usuario {user_id}: {user_name}")
            
            # Preparar secuencia de bienvenida personalizada + archivos
            welcome_message = f"""¡Gracias {user_name}! 😊

Soy Brenda, parte del equipo automatizado de Aprenda y Aplique IA y te voy a ayudar.

A continuación te comparto toda la información del curso:"""
            
            # Obtener información del curso desde Supabase
            course_id = "a392bf83-4908-4807-89a9-95d0acc807c9"  # ID del curso IA ChatGPT
            course_info_text = ""
            
            try:
                if self.ads_flow_handler:
                    from core.services.courseService import CourseService
                    course_service = CourseService(self.ads_flow_handler.db)
                    course_data = await course_service.getCourseBasicInfo(course_id)
                    if course_data:
                        # Construir mensaje dinámicamente desde la base de datos
                        course_info_text = await self._build_course_info_message(course_data)
                    else:
                        # Fallback si no se encuentra el curso
                        course_info_text = """🎓 dato no encontrado

dato no encontrado

⏱️ Duración: dato no encontrado
📊 Nivel: dato no encontrado
💰 Inversión: dato no encontrado


¿Qué te gustaría saber más sobre este curso?"""
            except Exception as e:
                logger.error(f"Error obteniendo datos del curso: {e}")
                # Fallback si hay error
                course_info_text = """🎓 dato no encontrado

dato no encontrado

⏱️ Duración: dato no encontrado
📊 Nivel: dato no encontrado
💰 Inversión: dato no encontrado


¿Qué te gustaría saber más sobre este curso?"""
            
            # Preparar respuesta con archivos de data + información del curso
            response = [
                {"type": "text", "content": welcome_message},
                {"type": "document", "path": "data/pdf_prueba.pdf", "caption": "📄 Aquí tienes el PDF descriptivo del curso"},
                {"type": "image", "path": "data/imagen_prueba.jpg", "caption": "🎯 Imagen del curso"},
                {"type": "text", "content": course_info_text}
            ]
            
            return response, None
            
        except Exception as e:
            logger.error(f"Error en handle_name_input: {e}")
            return "Error procesando tu nombre. Por favor, intenta nuevamente.", None

    async def handle_ad_flow(self, message_data: dict, user_data: dict, hashtags: list):
        """
        Maneja el flujo específico de usuarios que vienen de anuncios.
        Extrae información de curso y campaña de los hashtags.
        """
        try:
            # Extraer curso y campaña de hashtags
            course_info = ""
            campaign_info = ""
            
            for tag in hashtags:
                if tag.startswith('curso:') or tag.startswith('CURSO_'):
                    course_info = tag
                elif tag.startswith('anuncio:') or tag.startswith('ADSIM_'):
                    campaign_info = tag
            
            logger.info(f"Procesando anuncio - Curso: {course_info}, Campaña: {campaign_info}")
            
            # Usar el ads_flow_handler para procesar
            if self.ads_flow_handler and course_info and campaign_info:
                return await self.ads_flow_handler.process_ad_message(
                    message_data, user_data, course_info, campaign_info
                )
            else:
                # Fallback si no hay ads_flow_handler o faltan datos
                if self.ventas_bot:
                    return await self.ventas_bot.handle_conversation(message_data, user_data)
                else:
                    return "Error: Bot no inicializado correctamente.", None
                
        except Exception as e:
            logger.error(f"Error en handle_ad_flow: {e}")
            # Fallback a conversación normal
            if self.ventas_bot:
                return await self.ventas_bot.handle_conversation(message_data, user_data)
            else:
                return "Error: Bot no inicializado correctamente.", None

    async def handle_callback_query(self, update: Update, context):
        """Maneja las consultas de callback de botones inline."""
        if self.ventas_bot is None:
            await self.setup()
        # Ahora sí, seguro que self.ventas_bot está inicializado
        try:
            query = update.callback_query
            if query:
                await query.answer()
                
                # Preparar datos del usuario
                user_data = {
                    'id': query.from_user.id,
                    'first_name': query.from_user.first_name or '',
                    'last_name': query.from_user.last_name or '',
                    'username': query.from_user.username or ''
                }
                
                # NUEVO: Manejar callbacks específicos de privacidad
                if query.data in ['privacy_accept', 'privacy_decline', 'privacy_full']:
                    response, keyboard = await self._handle_privacy_callback(query.data, user_data)
                else:
                    # Preparar datos del mensaje para otros callbacks
                    message_data = {
                        'text': query.data,
                        'chat_id': query.message.chat.id if query.message else 0,
                        'message_id': query.message.message_id if query.message else 0,
                        'from': user_data
                    }
                    
                    # Procesar la consulta con el agente
                    if self.ventas_bot:
                        response, keyboard = await self.ventas_bot.handle_conversation(message_data, user_data)
                    else:
                        response, keyboard = "Error: Bot no inicializado correctamente.", None
                
                # Manejar respuesta
                if isinstance(response, str):
                    if keyboard:
                        await query.edit_message_text(
                            text=response,
                            reply_markup=keyboard,
                            parse_mode='Markdown'
                        )
                    else:
                        await query.edit_message_text(
                            text=response,
                            parse_mode='Markdown'
                        )
                elif isinstance(response, list):
                    for item in response:
                        if item.get('type') == 'text':
                            await context.bot.send_message(
                                chat_id=query.message.chat.id if query.message else user_data['id'],
                                text=item['content'],
                                parse_mode='Markdown'
                            )
                        elif item.get('type') == 'image':
                            with open(item['path'], 'rb') as img_file:
                                await context.bot.send_photo(
                                    chat_id=query.message.chat.id if query.message else user_data['id'],
                                    photo=img_file
                                )
                        elif item.get('type') == 'document':
                            with open(item['path'], 'rb') as doc_file:
                                await context.bot.send_document(
                                    chat_id=query.message.chat.id if query.message else user_data['id'],
                                    document=doc_file
                                )
            
        except Exception as e:
            logger.error(f"Error handling callback query: {str(e)}", exc_info=True)
            if update.callback_query:
                await update.callback_query.answer("Error procesando la selección")

    async def _handle_privacy_callback(self, callback_data: str, user_data: dict):
        """Maneja los callbacks relacionados con privacidad."""
        user_id = str(user_data['id'])
        user_memory = self.global_memory.get_lead_memory(user_id)
        
        if callback_data == "privacy_accept":
            # Marcar privacidad como aceptada y establecer etapa para pedir nombre
            if user_memory:
                user_memory.privacy_accepted = True
                user_memory.stage = "waiting_for_name"
                self.global_memory.save_lead_memory(user_id, user_memory)
            
            # Pedir el nombre del usuario
            message = "¡Gracias por aceptar! 😊\n\n¿Cómo te gustaría que te llame?"
            return message, None
            
        elif callback_data == "privacy_decline":
            message = """Respeto tu decisión. 

Si cambias de opinión y quieres conocer más sobre nuestros cursos de IA, estaremos aquí para ayudarte.

¡Que tengas un excelente día! 😊
"""
            return message, None
            
        elif callback_data == "privacy_full":
            # Mostrar aviso completo de privacidad
            if self.templates:
                message = self.templates.get_full_privacy_policy()
            else:
                message = "Aviso de privacidad no disponible temporalmente."
            
            # Mantener los botones para que el usuario pueda aceptar o rechazar
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Acepto", callback_data="privacy_accept")],
                [InlineKeyboardButton("❌ No acepto", callback_data="privacy_decline")]
            ])
            return message, keyboard
        
        return "Opción no reconocida.", None

    async def _build_course_info_message(self, course_data: dict) -> str:
        """
        Construye el mensaje de información del curso dinámicamente desde la base de datos.
        Reutilizable para cualquier curso.
        """
        try:
            # Extraer datos del curso con fallbacks a "dato no encontrado"
            course_name = course_data.get('name', 'dato no encontrado')
            course_description = course_data.get('short_description', 'dato no encontrado')
            
            # Formatear duración
            duration = course_data.get('total_duration', 'dato no encontrado')
            if duration != 'dato no encontrado' and duration:
                # Si viene en formato timedelta o string, mantenerlo como está
                duration_str = str(duration)
            else:
                duration_str = 'dato no encontrado'
            
            # Formatear nivel
            level = course_data.get('level', 'dato no encontrado')
            
            # Formatear precio con moneda
            price_usd = course_data.get('price_usd', 'dato no encontrado')
            if price_usd != 'dato no encontrado' and price_usd is not None:
                price_str = f"${price_usd} USD"
            else:
                price_str = 'dato no encontrado'
            
            # Construir mensaje con la estructura original
            course_info_text = f"""🎓 {course_name}

{course_description}

⏱️ Duración: {duration_str}
📊 Nivel: {level}
💰 Inversión: {price_str}


¿Qué te gustaría saber más sobre este curso?"""
            
            return course_info_text
            
        except Exception as e:
            logger.error(f"Error construyendo mensaje del curso: {e}")
            # Mensaje de error genérico si falla todo
            return """🎓 dato no encontrado

dato no encontrado

⏱️ Duración: dato no encontrado
📊 Nivel: dato no encontrado
💰 Inversión: dato no encontrado


¿Qué te gustaría saber más sobre este curso?"""

def main_telegram_bot():
    """Función principal del bot de Telegram con manejo mejorado de errores."""
    logger.info("Iniciando bot de Telegram...")
    
    try:
        # Verificar token
        if not settings.TELEGRAM_API_TOKEN:
            raise ValueError("TELEGRAM_API_TOKEN no encontrado en variables de entorno")

        # Crear bot y aplicación
        bot = VentasBot()
        application = Application.builder().token(settings.TELEGRAM_API_TOKEN).build()

        # Actualizar agente con API de Telegram (ignorar tipo para compatibilidad)
        # El bot se inicializa en el primer mensaje recibido
        application.bot_data['global_mem'] = bot.global_memory
        
        # Configurar handlers
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
        application.add_handler(CallbackQueryHandler(bot.handle_callback_query))

        logger.info("Bot de Telegram configurado. Iniciando polling...")
        
        # Iniciar polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error fatal en main_telegram_bot: {e}", exc_info=True)
        raise
    finally:
        logger.info("Bot de Telegram finalizado")

if __name__ == "__main__":
    # Configurar asyncio para Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        main_telegram_bot()
        logger.info("Bot finalizado normalmente")
    except KeyboardInterrupt:
        logger.info("Bot interrumpido por el usuario (Ctrl+C)")
    except Exception as e:
        logger.error(f"Error fatal en la aplicación principal: {e}", exc_info=True)
        import sys
        sys.exit(1)