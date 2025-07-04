"""
Maneja la memoria global del bot y los datos de los usuarios.
"""

from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class LeadData:
    """Datos del lead/usuario"""
    user_id: str
    name: str = ""
    username: Optional[str] = None
    selected_course: Optional[str] = None
    last_interaction: Optional[float] = None

class GlobalMemory:
    """Maneja la memoria global del bot"""
    def __init__(self):
        self._leads: Dict[str, LeadData] = {}
        
    @property
    def lead_data(self) -> Optional[LeadData]:
        """Obtiene los datos del lead actual"""
        return self._current_lead
        
    def set_current_lead(self, user_id: str, name: str = "", username: Optional[str] = None) -> None:
        """Establece el lead actual"""
        if user_id not in self._leads:
            self._leads[user_id] = LeadData(user_id=user_id, name=name, username=username)
        self._current_lead = self._leads[user_id]
        
    def get_lead(self, user_id: str) -> Optional[LeadData]:
        """Obtiene los datos de un lead específico"""
        return self._leads.get(user_id) 