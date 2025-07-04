"""Bot de ventas inteligente con Telegram."""
import logging
import asyncio
import sys
from typing import Optional, Tuple
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
import nest_asyncio
import os

from config.settings import settings
from core.utils.memory import GlobalMemory
from core.utils.navigation import show_main_menu
from core.handlers.menu_handlers import handle_callback_query
from core.services.database import DatabaseService
from core.agents.sales_agent import AgenteSalesTools
from core.agents.smart_sales_agent import SmartSalesAgent

# Aplicar nest_asyncio para manejar event loops anidados
nest_asyncio.apply()

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotApplication:
    def __init__(self):
        self.bot = None
        self.application: Optional[Application] = None
        self.db = DatabaseService(settings.DATABASE_URL)
        self.agent_tools = AgenteSalesTools(self.db, None)
        self.ventas_bot = SmartSalesAgent(self.db, self.agent_tools)
        self.global_memory = GlobalMemory()

    async def handle_message(self, update: Update, context) -> None:
        """Manejador principal de mensajes."""
        try:
            # Asegurarse de que global_mem esté disponible
            if 'global_mem' not in context.bot_data:
                context.bot_data['global_mem'] = self.global_memory

            # Procesar el mensaje
            if update.message and update.message.text and update.message.from_user:
                message_data = {
                    'text': update.message.text,
                    'chat_id': update.message.chat_id,
                    'message_id': update.message.message_id
                }
                user = update.message.from_user
                user_data = {
                    'id': user.id,
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                    'username': user.username or ''
                }
                
                # Obtener respuesta del agente
                response, keyboard = await self.ventas_bot.handle_conversation(message_data, user_data)
                
                # Si la respuesta es un diccionario, significa que debemos enviar una secuencia de mensajes
                if isinstance(response, dict):
                    # 1. Enviar mensaje de confirmación
                    await update.message.reply_text(response['confirmation'])
                    
                    # 2. Enviar imagen si se solicita
                    if response.get('send_image'):
                        image_path = "data/imagen_prueba.jpg"
                        if os.path.exists(image_path):
                            try:
                                with open(image_path, 'rb') as photo:
                                    await update.message.reply_photo(photo=photo)
                            except Exception as e:
                                logger.warning(f"No se pudo enviar imagen: {e}")
                    
                    # 3. Enviar PDF si se solicita
                    if response.get('send_pdf'):
                        pdf_path = "data/pdf_prueba.pdf"
                        if os.path.exists(pdf_path):
                            try:
                                with open(pdf_path, 'rb') as document:
                                    await update.message.reply_document(document=document)
                            except Exception as e:
                                logger.warning(f"No se pudo enviar PDF: {e}")
                    
                    # 4. Enviar mensaje final con resumen si existe
                    if final_message := response.get('final_message'):
                        mensaje_completo = final_message['text']
                        if resumen := final_message.get('resumen'):
                            mensaje_completo += "\n\n" + resumen
                        await update.message.reply_text(mensaje_completo, parse_mode='Markdown')
                
                # Si es una respuesta normal, enviarla como siempre
                elif response:
                    await update.message.reply_text(response, reply_markup=keyboard, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error en handle_message: {e}", exc_info=True)
            if update.message:
                try:
                    await update.message.reply_text(
                        "Lo siento, ha ocurrido un error. Por favor, intenta de nuevo."
                    )
                except Exception:
                    pass

    async def _send_course_files(self, update: Update, user_memory) -> None:
        """
        Envía los archivos del curso (imagen y PDF) al usuario.
        """
        try:
            if not update.message:
                return
                
            # Obtener información del curso
            from core.services.supabase_service import get_course_detail
            curso_info = await get_course_detail(user_memory.selected_course)
            if not curso_info:
                logger.warning("No se encontró información del curso para envío de archivos")
                return
            
            # Enviar imagen
            image_path = "data/imagen_prueba.jpg"
            if os.path.exists(image_path):
                try:
                    with open(image_path, 'rb') as photo:
                        await update.message.reply_photo(
                            photo=photo,
                            caption="🎯 ¡Este es el curso que transformará tu carrera profesional!"
                        )
                    logger.info("Imagen enviada correctamente")
                except Exception as e:
                    logger.warning(f"No se pudo enviar imagen: {e}")
            else:
                logger.warning("Archivo de imagen no encontrado")
            
            # Enviar PDF
            pdf_path = "data/pdf_prueba.pdf"
            if os.path.exists(pdf_path):
                try:
                    with open(pdf_path, 'rb') as document:
                        caption = (
                            "📚 Aquí tienes toda la información detallada del curso.\n\n"
                            f"*Modalidad:* {curso_info.get('modality', 'No especificado')}\n"
                            f"*Duración:* {curso_info.get('total_duration', 'No especificado')} horas\n"
                            f"*Horario:* {curso_info.get('schedule', 'No especificado')}\n"
                            f"*Precio:* ${curso_info.get('price_usd', 'No especificado')} USD\n"
                            "*Incluye:* Material, acceso a grabaciones, soporte"
                        )
                        await update.message.reply_document(
                            document=document,
                            caption=caption,
                            parse_mode='Markdown'
                        )
                    logger.info("PDF enviado correctamente")
                except Exception as e:
                    logger.warning(f"No se pudo enviar PDF: {e}")
            else:
                logger.warning("Archivo PDF no encontrado")
                
        except Exception as e:
            logger.error(f"Error enviando archivos del curso: {e}", exc_info=True)

    async def setup(self) -> None:
        """Configurar el bot y sus handlers."""
        try:
            if not settings.TELEGRAM_API_TOKEN:
                raise ValueError("TELEGRAM_API_TOKEN no encontrado en variables de entorno")

            # Crear aplicación
            self.application = Application.builder().token(settings.TELEGRAM_API_TOKEN).build()
            
            # Actualizar referencias
            self.bot = self.application.bot
            self.agent_tools.telegram = self.bot
            
            # Inicializar memoria global
            self.application.bot_data['global_mem'] = self.global_memory
            
            # Configurar handlers
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            )
            self.application.add_handler(
                CallbackQueryHandler(handle_callback_query)
            )

            logger.info("Bot configurado exitosamente")
            
        except Exception as e:
            logger.error(f"Error en setup: {e}", exc_info=True)
            raise

    async def start(self) -> None:
        """Iniciar el bot."""
        try:
            await self.setup()
            logger.info("Iniciando bot...")
            
            if self.application:
                # Usar async with para manejo automático del ciclo de vida
                async with self.application:
                    await self.application.start()
                    logger.info("Bot iniciado correctamente")
                    
                    # Verificar que updater esté disponible
                    if self.application.updater:
                        await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
                    else:
                        logger.error("Updater no disponible")
                        return
                    
                    # Mantener ejecutándose indefinidamente
                    try:
                        while True:
                            await asyncio.sleep(1)
                    except KeyboardInterrupt:
                        logger.info("Bot interrumpido por el usuario")
                        return
                    finally:
                        logger.info("Deteniendo bot...")
                        if self.application.updater:
                            await self.application.updater.stop()
                        
        except Exception as e:
            logger.error(f"Error en start: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Detener el bot de manera limpia."""
        # El async with maneja automáticamente la limpieza
        logger.info("Bot detenido correctamente")

async def main():
    """Función principal asíncrona."""
    bot_app = None
    try:
        logger.info("Iniciando aplicación...")
        bot_app = BotApplication()
        await bot_app.start()
    except KeyboardInterrupt:
        logger.info("Bot interrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error en la ejecución del bot: {e}", exc_info=True)
    finally:
        if bot_app:
            await bot_app.stop()
        logger.info("Bot finalizado")

def run_bot():
    """Ejecutar el bot."""
    try:
        logger.info("Creando nuevo event loop")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ejecutar el bot
        loop.run_until_complete(main())
        
    except KeyboardInterrupt:
        logger.info("Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"Error ejecutando el bot: {e}", exc_info=True)
    finally:
        # Cerrar el event loop
        try:
            loop = asyncio.get_event_loop()
            tasks = asyncio.all_tasks(loop)
            for task in tasks:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            loop.close()
        except Exception as e:
            logger.error(f"Error cerrando el event loop: {e}", exc_info=True)

if __name__ == "__main__":
    run_bot()
 