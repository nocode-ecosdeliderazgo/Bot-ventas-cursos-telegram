"""
Wrapper del agente de ventas que utiliza las herramientas de agent_tools.py
"""

from typing import Dict, List, Optional, Union
from datetime import datetime, timezone
from decimal import Decimal
import json
from ..services.database import DatabaseService
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from .agent_tools import AgentTools

class AgenteSalesTools(AgentTools):
    """
    Clase principal del agente de ventas que hereda todas las herramientas de AgentTools.
    """
    
    def __init__(self, db: DatabaseService, telegram_api):
        """
        Inicializa el agente de ventas con el servicio de base de datos y API de Telegram.
        """
        super().__init__(db, telegram_api)
        self.db = db
        self.telegram = telegram_api 