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
            
            # Rutear según tipo de mensaje
            if has_course_hashtag and has_ad_hashtag:
                # Flujo de anuncios - usuario viene desde publicidad
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
                            await message.reply_document(
                                document=item['url'],
                                caption=item.get('caption', '')
                            )
                        elif item.get('path'):
                            try:
                                with open(item['path'], 'rb') as doc_file:
                                    await message.reply_document(
                                        document=doc_file,
                                        caption=item.get('caption', '')
                                    )
                            except FileNotFoundError:
                                logger.warning(f"Archivo PDF no encontrado: {item['path']}")

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            if message:
                await message.reply_text(
                    "Lo siento, hubo un error procesando tu mensaje. Por favor, intenta nuevamente."
                )

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
            # Marcar privacidad como aceptada
            if user_memory:
                user_memory.privacy_accepted = True
                self.global_memory.save_lead_memory(user_id, user_memory)
            
            # Iniciar secuencia post-aceptación completa según las imágenes de referencia
            if self.ads_flow_handler and user_memory:
                # Obtener course_id de la memoria o usar el curso por defecto
                course_hashtag = user_memory.ad_source or "#CURSO_IA_CHATGPT"
                course_id = "a392bf83-4908-4807-89a9-95d0acc807c9"  # ID del curso IA ChatGPT
                
                try:
                    # Marcar que Brenda ya se presentó y privacidad aceptada
                    user_memory.brenda_introduced = True
                    user_memory.selected_course = course_id
                    self.global_memory.save_lead_memory(str(user_data['id']), user_memory)
                    
                    # Crear secuencia completa: Bienvenida + Presentación del curso
                    user_name = user_data.get('first_name', 'Usuario')
                    brenda_message = f"""¡Gracias por aceptar! 😊

¡Hola {user_name}! 👋

Soy Brenda, parte del equipo automatizado de Aprenda y Aplique IA y te voy a ayudar.

A continuación te comparto toda la información del curso:"""
                    
                    # Preparar la respuesta como lista que incluye bienvenida + materiales del curso
                    complete_response = [{"type": "text", "content": brenda_message}]
                    
                    # Obtener presentación del curso (PDF, imagen, datos)
                    course_presentation, course_keyboard = await self.ads_flow_handler._present_course(user_data, course_id)
                    if isinstance(course_presentation, list):
                        complete_response.extend(course_presentation)
                    
                    return complete_response, course_keyboard
                    
                except Exception as e:
                    logger.error(f"Error en secuencia post-aceptación: {e}")
            
            # Fallback si hay error
            message = "¡Gracias por aceptar! 😊\n\nSoy Brenda, parte del equipo automatizado de Aprenda y Aplique IA y te voy a ayudar.\n\n¿Cómo te gustaría que te llame?"
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