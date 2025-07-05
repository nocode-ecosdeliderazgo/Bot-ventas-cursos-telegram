"""
Manejo del flujo de anuncios.
"""

import logging
from typing import Dict, Optional, Tuple

from telegram import InlineKeyboardMarkup
from core.services.database import DatabaseService
from core.agents.agent_tools import AgentTools

logger = logging.getLogger(__name__)

class AdsFlowHandler:
    """
    Maneja el flujo completo de usuarios que llegan desde anuncios.
    """
    
    def __init__(self, db: DatabaseService, agent: AgentTools) -> None:
        """
        Inicializa el manejador de flujo de anuncios.
        """
        self.db = db
        self.agent = agent
