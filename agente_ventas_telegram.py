"""Bot de ventas para Telegram que utiliza un agente inteligente para convertir leads."""

import os
import logging
import asyncio
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
from telegram import Update
from core.services.database import DatabaseService
from core.agents.agent_tools import AgentTools
from core.agents.smart_sales_agent import SmartSalesAgent
from core.utils.memory import GlobalMemory
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
        self.global_memory = GlobalMemory()

    async def setup(self):
        # Inicializar el pool de conexiones
        await self.db.connect()
        # Ahora sí, inicializar los servicios que usan la base de datos
        self.agent_tools = AgentTools(self.db, None)  # Se actualizará con la API de Telegram
        self.ventas_bot = SmartSalesAgent(self.db, self.agent_tools)

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
            
            # Procesar mensaje con el agente inteligente
            response, keyboard = await self.ventas_bot.handle_conversation(message_data, user_data)
            
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
                        with open(item['path'], 'rb') as img_file:
                            await message.reply_photo(img_file)
                    elif item.get('type') == 'document':
                        with open(item['path'], 'rb') as doc_file:
                            await message.reply_document(doc_file)

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            if message:
                await message.reply_text(
                    "Lo siento, hubo un error procesando tu mensaje. Por favor, intenta nuevamente."
                )

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
                
                # Preparar datos del mensaje
                message_data = {
                    'text': query.data,
                    'chat_id': query.message.chat.id if query.message else 0,
                    'message_id': query.message.message_id if query.message else 0,
                    'from': user_data
                }
                
                # Procesar la consulta con el agente
                response, keyboard = await self.ventas_bot.handle_conversation(message_data, user_data)
                
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
 