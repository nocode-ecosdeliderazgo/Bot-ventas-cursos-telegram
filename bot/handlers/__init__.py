"""
Handlers module for the Telegram bot.
This module contains all the handlers for different flows in the bot.
"""

# Importaciones de los módulos
from .auth_flow import ensure_privacy, send_privacy_notice, start_command
from .menu_handlers import handle_callback_query, mostrar_menu_principal
from .course_flow import (
    mostrar_lista_cursos, mostrar_menu_curso_exploracion
)
from .contact_flow import (
    contact_advisor_flow
)
from .faq_flow import mostrar_faq, responder_faq, mostrar_cursos_para_faq
from .promo_flow import mostrar_promociones
from .utils import (
    send_agent_telegram,
    handle_telegram_errors
)

# Exportar las funciones principales que usa agente_ventas_telegram.py
__all__ = [
    'start_command',
    'handle_callback_query',
    'mostrar_menu_principal',
    'ensure_privacy',
    'send_privacy_notice'
] 