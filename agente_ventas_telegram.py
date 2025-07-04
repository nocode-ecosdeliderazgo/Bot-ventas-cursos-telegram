"""
Bot de ventas para Telegram que utiliza un agente inteligente para convertir leads.
"""

import os
import logging
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
from telegram import Update
from core.services.database import DatabaseService
from core.agents.sales_agent import AgenteSalesTools
from core.handlers.ads_flow import AdsFlowHandler
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

class VentasBot:
    def __init__(self):
        # Inicializar servicios
        self.db = DatabaseService(os.getenv('DATABASE_URL'))
        self.agent = AgenteSalesTools(self.db, None)  # Se actualizará con la API de Telegram
        self.ads_handler = AdsFlowHandler(self.db, self.agent)

    async def start(self):
        """Inicia el bot y configura los handlers."""
        # Crear aplicación
        token = os.getenv('TELEGRAM_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_TOKEN no encontrado en variables de entorno")
            
        self.app = Application.builder().token(token).build()
        
        # Actualizar agente con API de Telegram
        self.agent.telegram = self.app.bot
        
        # Conectar a la base de datos
        await self.db.connect()
        
        # Configurar handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Iniciar bot
        await self.app.initialize()
        await self.app.start()
        await self.app.run_polling()

    async def handle_message(self, update: Update, context):
        """
        Maneja todos los mensajes entrantes.
        Detecta si el mensaje viene de un anuncio y lo procesa adecuadamente.
        """
        try:
            message = update.message
            if not message or not message.text:
                return
                
            user = message.from_user
            if not user:
                return
            
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
                # Procesar mensaje normal
                await message.reply_text(
                    "¡Hola! Soy tu asistente de cursos de IA. ¿En qué puedo ayudarte hoy?"
                )

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            await message.reply_text(
                "Lo siento, hubo un error procesando tu mensaje. Por favor, intenta nuevamente."
            )

    async def handle_callback(self, update: Update, context):
        """
        Maneja las interacciones con botones.
        """
        try:
            query = update.callback_query
            if not query or not query.data:
                return
                
            data = query.data
            user_id = query.from_user.id
            
            # Extraer acción y course_id del callback_data
            parts = data.split('_', 1)
            if len(parts) < 2:
                await query.answer("Acción no válida")
                return
                
            action, course_id = parts
            
            # Ejecutar acción correspondiente
            if action == 'show_syllabus':
                await self.agent.mostrar_syllabus_interactivo(user_id, course_id)
            elif action == 'show_preview':
                await self.agent.enviar_preview_curso(user_id, course_id)
            elif action == 'show_pricing':
                await self.agent.presentar_oferta_limitada(user_id, course_id)
            elif action == 'schedule_call':
                await self.agent.agendar_demo_personalizada(user_id, course_id)
            
            # Confirmar la acción al usuario
            await query.answer()

        except Exception as e:
            logger.error(f"Error handling callback: {str(e)}", exc_info=True)
            await query.answer("Error procesando tu solicitud. Intenta nuevamente.")

if __name__ == '__main__':
    # Iniciar el bot
    bot = VentasBot()
    import asyncio
    asyncio.run(bot.start())
 