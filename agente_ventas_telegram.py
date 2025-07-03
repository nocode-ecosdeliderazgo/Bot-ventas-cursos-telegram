# -*- coding: utf-8 -*-
import logging
import sys
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, PollAnswerHandler
from config.settings import settings
from bot.handlers import (
    start_command, handle_message, handle_callback_query, handle_poll_answer
)
from bot.memory import Memory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==============================
# CONFIGURACIÓN GLOBAL
# ==============================
CURSOS_MAP = {
    "CURSO_IA_CHATGPT": "a392bf83-4908-4807-89a9-95d0acc807c9"
}
UMBRAL_PROMO = 20

global_mem = Memory()
global_user_id = None

# ==============================
# MAIN BOT LAUNCHER
# ==============================
def main_telegram_bot():
    logger.info("Iniciando bot de Telegram...")
    try:
        application = Application.builder().token(settings.telegram_api_token).build()
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        # application.add_handler(CallbackQueryHandler(handle_callback_query))
        # application.add_handler(PollAnswerHandler(handle_poll_answer))
        # Elimino MyChatMemberHandler y handle_stop si no existen
        logger.info("Bot de Telegram configurado. Listo para iniciar polling.")
        Memory.cleanup_old_memories()
        logger.info("Limpieza de memorias antiguas completada")
        application.run_polling(allowed_updates=None)
    except Exception as e:
        logger.error(f"Error fatal en main_telegram_bot: {e}", exc_info=True)
        raise
    finally:
        logger.info("Bot de Telegram finalizado")

if __name__ == "__main__":
    logger.info("Iniciando aplicación principal")
    if sys.platform == "win32":
        logger.info("Configurando WindowsSelectorEventLoopPolicy para Windows")
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        main_telegram_bot()
        logger.info("Bot finalizado normalmente")
    except KeyboardInterrupt:
        logger.info("Bot interrumpido por el usuario (Ctrl+C)")
    except Exception as e:
        logger.error(f"Error fatal en la aplicación principal: {e}", exc_info=True)
        sys.exit(1)
 