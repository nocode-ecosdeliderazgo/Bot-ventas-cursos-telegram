"""Bot de ventas inteligente con Telegram."""
import logging
import asyncio
import sys
from typing import Optional, Tuple
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
import nest_asyncio

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
                response, keyboard = await self.ventas_bot.handle_conversation(message_data, user_data)
                if response:
                    await update.message.reply_text(response, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error en handle_message: {e}", exc_info=True)
            if update.message:
                try:
                    await update.message.reply_text(
                        "Lo siento, ha ocurrido un error. Por favor, intenta de nuevo."
                    )
                except Exception:
                    pass

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
                    await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
                    
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
    """Ejecutar el bot con manejo correcto del event loop."""
    try:
        # Configurar asyncio para Windows
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        # Verificar si ya hay un event loop ejecutándose
        try:
            loop = asyncio.get_running_loop()
            logger.info("Event loop ya está ejecutándose, usando nest_asyncio")
            # Si ya hay un loop ejecutándose, usar nest_asyncio
            import nest_asyncio
            nest_asyncio.apply()
            # Crear una nueva tarea en el loop existente
            task = asyncio.create_task(main())
            # Esperar a que termine
            loop.run_until_complete(task)
        except RuntimeError:
            # No hay event loop, crear uno nuevo
            logger.info("Creando nuevo event loop")
            asyncio.run(main())
            
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_bot()
 