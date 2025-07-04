"""
Bot de ventas para Telegram que utiliza un agente inteligente para convertir leads.
"""

import os
import logging
import asyncio
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
from telegram import Update
from core.services.database import DatabaseService
from core.agents.sales_agent import AgenteSalesTools
from core.handlers.ads_flow import AdsFlowHandler
from core.utils.memory import GlobalMemory
from core.handlers.menu_handlers import mostrar_menu_principal, handle_callback_query
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
        self.agent = AgenteSalesTools(self.db, None)  # Se actualizará con la API de Telegram
        self.ads_handler = AdsFlowHandler(self.db, self.agent)
        self.global_memory = GlobalMemory()

    async def handle_message(self, update: Update, context):
        """
        Maneja todos los mensajes entrantes.
        Detecta si el mensaje viene de un anuncio y lo procesa adecuadamente.
        """
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
                username=user.username
            )
            
            # Verificar si el mensaje viene de un anuncio (tiene hashtags)
            if '#' in message.text:
                response, buttons = await self.ads_handler.handle_ad_message(
                    {
                        'text': message.text,
                        'chat_id': message.chat_id,
                        'message_id': message.message_id
                    },
                    {
                        'id': user.id,
                        'first_name': user.first_name or '',
                        'last_name': user.last_name or '',
                        'username': user.username or ''
                    }
                )
                
                # Enviar respuesta con botones
                await message.reply_text(
                    response,
                    reply_markup=buttons,
                    parse_mode='Markdown'
                )
            else:
                # Mostrar menú principal
                await mostrar_menu_principal(update, context)

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            if message:
                await message.reply_text(
                    "Lo siento, hubo un error procesando tu mensaje. Por favor, intenta nuevamente."
                )

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

        # Actualizar agente con API de Telegram
        bot.agent.telegram = application.bot
        
        # Inicializar memoria global en el contexto
        application.bot_data['global_mem'] = bot.global_memory
        
        # Configurar handlers
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
        application.add_handler(CallbackQueryHandler(handle_callback_query))

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
 