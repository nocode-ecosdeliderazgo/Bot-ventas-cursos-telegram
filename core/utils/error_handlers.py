"""Decoradores para manejo de errores."""
import logging
import asyncio
from functools import wraps
import httpx
import requests
from telegram import Update

logger = logging.getLogger(__name__)

def handle_telegram_errors(func):
    """Decorator para manejar errores de Telegram con reintentos."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except httpx.ReadError as e:
                logger.warning(f"Error de conexión Telegram (intento {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Error fatal de conexión Telegram después de {max_retries} intentos")
                    update = args[0] if args else None
                    if update and hasattr(update, 'message') and update.message:
                        try:
                            await update.message.reply_text("⚠️ Error de conexión. Por favor, intenta de nuevo en unos momentos.")
                        except Exception:
                            pass
                    raise
                await asyncio.sleep(1 * (attempt + 1))
            except Exception as e:
                logger.error(f"Error inesperado en {func.__name__}: {e}", exc_info=True)
                update = args[0] if args else None
                if update and hasattr(update, 'message') and update.message:
                    try:
                        await update.message.reply_text("⚠️ Ocurrió un error inesperado. Por favor, intenta de nuevo más tarde.")
                    except Exception:
                        pass
                raise
    return wrapper

def handle_supabase_errors(func):
    """Decorator para manejar errores de Supabase."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión Supabase en {func.__name__}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado en {func.__name__}: {e}")
            return None
    return wrapper 