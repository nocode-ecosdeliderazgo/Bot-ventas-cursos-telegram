"""
Handlers module for the Telegram bot.
This module contains all the handlers for different flows in the bot.
"""

# Importaciones de los módulos
from .auth_flow import ensure_privacy, send_privacy_notice, start_command
from .menu_handlers import handle_message, handle_callback_query
from .course_flow import (
    mostrar_lista_cursos, mostrar_menu_curso_exploracion
)
from .contact_flow import (
    contact_advisor_flow, contactar_asesor,
    solicitar_datos_contacto, mostrar_confirmacion_datos,
    editar_datos_contacto
)
from .faq_flow import mostrar_menu_faq, generar_faq_contexto
from .promo_flow import mostrar_promociones, forzar_seleccion_curso
from .utils import (
    send_agent_telegram, send_processing_message,
    edit_message, handle_telegram_errors,
    send_grouped_messages, detect_negative_feedback
)

# Exportar las funciones principales que usa agente_ventas_telegram.py
__all__ = [
    'start_command',
    'handle_message',
    'handle_callback_query',
    'ensure_privacy',
    'send_privacy_notice'
] 