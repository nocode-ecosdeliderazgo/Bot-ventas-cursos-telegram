"""
Sistema de memoria global para manejar leads y usuarios del bot.
Incluye persistencia, scoring y gestión de estados.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class LeadMemory:
    """
    Clase para almacenar información de un lead/usuario.
    """
    user_id: str = ""
    name: str = ""
    first_name: str = ""
    username: str = ""
    email: str = ""
    phone: str = ""
    
    # Estado del flujo
    has_accepted_privacy: bool = False
    privacy_accepted: bool = False  # Alias para compatibilidad
    brenda_introduced: bool = False
    stage: str = "initial"  # initial, privacy_accepted, name_collected, course_presented, etc.
    
    # Información del curso
    selected_course: str = ""
    course_presented: bool = False
    media_sent: bool = False
    
    # Información profesional
    profile_type: str = ""  # professional, student, entrepreneur, curious
    role: str = ""
    interests: Optional[List[str]] = None
    
    # Scoring y comportamiento
    lead_score: int = 50
    score_history: Optional[List[Dict]] = None
    message_history: Optional[List[Dict]] = None
    
    # Nuevos atributos para el agente inteligente
    interaction_count: int = 0
    conversation_history: Optional[List[Dict]] = None
    pain_points: Optional[List[str]] = None
    buying_signals: Optional[List[str]] = None
    interest_level: str = "low"
    
    # Necesidades de automatización
    automation_needs: Optional[Dict[str, Any]] = None
    
    # Seguimiento
    last_interaction: Optional[datetime] = None
    ad_source: str = ""
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.interests is None:
            self.interests = []
        if self.score_history is None:
            self.score_history = []
        if self.message_history is None:
            self.message_history = []
        if self.conversation_history is None:
            self.conversation_history = []
        if self.pain_points is None:
            self.pain_points = []
        if self.buying_signals is None:
            self.buying_signals = []
        if self.automation_needs is None:
            self.automation_needs = {
                "report_types": [],
                "frequency": "",
                "time_investment": "",
                "current_tools": [],
                "specific_frustrations": []
            }
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convierte la instancia a diccionario para serialización."""
        data = asdict(self)
        # Convertir datetime a string para JSON
        if data['last_interaction']:
            data['last_interaction'] = data['last_interaction'].isoformat()
        if data['created_at']:
            data['created_at'] = data['created_at'].isoformat()
        if data['updated_at']:
            data['updated_at'] = data['updated_at'].isoformat()
        
        # Convertir cualquier UUID a string para JSON
        def convert_uuids(obj):
            if hasattr(obj, '__dict__'):
                for key, value in obj.__dict__.items():
                    if hasattr(value, 'hex'):  # Es un UUID
                        setattr(obj, key, str(value))
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    if hasattr(value, 'hex'):  # Es un UUID
                        obj[key] = str(value)
                    elif isinstance(value, (dict, list)):
                        convert_uuids(value)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if hasattr(item, 'hex'):  # Es un UUID
                        obj[i] = str(item)
                    elif isinstance(item, (dict, list)):
                        convert_uuids(item)
        
        # Aplicar conversión recursiva a todos los campos
        for key, value in data.items():
            if hasattr(value, 'hex'):  # Es un UUID
                data[key] = str(value)
            elif isinstance(value, (dict, list)):
                convert_uuids(value)
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LeadMemory':
        """Crea una instancia desde un diccionario."""
        # Convertir strings de datetime de vuelta a datetime
        if data.get('last_interaction'):
            data['last_interaction'] = datetime.fromisoformat(data['last_interaction'])
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        return cls(**data)

    @classmethod
    def from_lead_data(cls, lead_data: Dict) -> 'LeadMemory':
        """
        Crea una instancia desde datos de lead.
        
        Args:
            lead_data: Diccionario con datos del lead
            
        Returns:
            Nueva instancia de LeadMemory
        """
        # Mapear campos del lead_data a los campos de LeadMemory
        mapped_data = {
            'user_id': str(lead_data.get('id', '')),
            'name': lead_data.get('name', ''),
            'first_name': lead_data.get('first_name', ''),
            'username': lead_data.get('username', ''),
            'email': lead_data.get('email', ''),
            'phone': lead_data.get('phone', ''),
            'role': lead_data.get('role', ''),
            'selected_course': lead_data.get('selected_course', ''),
            'stage': lead_data.get('stage', 'initial'),
            'has_accepted_privacy': lead_data.get('has_accepted_privacy', False),
            'profile_type': lead_data.get('profile_type', ''),
            'interests': lead_data.get('interests', []) if isinstance(lead_data.get('interests'), list) else [],
            'lead_score': lead_data.get('lead_score', 50),
            'ad_source': lead_data.get('ad_source', ''),
            'score_history': [],
            'message_history': data.get('history', []),
            'course_presented': bool(data.get('last_presented_courses')),
            'media_sent': False,
            'last_interaction': datetime.fromtimestamp(data['last_activity']) if data.get('last_activity') else None,
            'created_at': datetime.fromtimestamp(data['last_activity']) if data.get('last_activity') else None,
            'updated_at': datetime.fromtimestamp(data['last_activity']) if data.get('last_activity') else None
        }
        return cls(**mapped_data)

class GlobalMemory:
    """
    Manejo de memoria global para todos los usuarios del bot.
    Incluye persistencia en archivos JSON y gestión de estados.
    """
    
    def __init__(self, memory_dir: str = "memorias"):
        self.memory_dir = memory_dir
        self.leads_cache: Dict[str, LeadMemory] = {}
        self.current_lead_id: Optional[str] = None
        
        # Crear directorio si no existe
        os.makedirs(memory_dir, exist_ok=True)
        
        # Cargar leads existentes
        self._load_all_leads()
    
    def set_current_lead(self, user_id: str, name: str = "", username: str = "") -> None:
        """
        Establece el lead actual y actualiza información básica.
        """
        self.current_lead_id = user_id
        
        # Crear o actualizar lead
        if user_id not in self.leads_cache:
            self.leads_cache[user_id] = LeadMemory(
                user_id=user_id,
                first_name=name,
                username=username
            )
        else:
            # Actualizar información básica si es nueva
            lead = self.leads_cache[user_id]
            if name and not lead.first_name:
                lead.first_name = name
            if username and not lead.username:
                lead.username = username
            lead.updated_at = datetime.now()
    
    def get_lead_memory(self, user_id: str) -> LeadMemory:
        """
        Obtiene la memoria de un lead específico.
        """
        if user_id not in self.leads_cache:
            self.leads_cache[user_id] = LeadMemory(user_id=user_id)
        
        return self.leads_cache[user_id]
    
    def create_lead_memory(self, user_id: str) -> LeadMemory:
        """
        Crea una nueva memoria de lead.
        """
        lead = LeadMemory(user_id=user_id)
        self.leads_cache[user_id] = lead
        return lead
    
    def save_lead_memory(self, user_id: str, lead_memory: LeadMemory) -> bool:
        """
        Guarda la memoria de un lead específico.
        """
        try:
            # Actualizar cache
            lead_memory.updated_at = datetime.now()
            self.leads_cache[user_id] = lead_memory
            
            # Guardar en archivo
            filename = f"memory_{user_id}.json"
            filepath = os.path.join(self.memory_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(lead_memory.to_dict(), f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Lead memory saved for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving lead memory for {user_id}: {e}")
            return False
    
    def load_lead_memory(self, user_id: str) -> Optional[LeadMemory]:
        """
        Carga la memoria de un lead desde archivo.
        
        Args:
            user_id: ID del usuario a cargar
            
        Returns:
            Instancia de LeadMemory o None si hay error
        """
        try:
            filename = f"memory_{user_id}.json"
            filepath = os.path.join(self.memory_dir, filename)
            
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Manejar diferentes formatos de archivos de memoria
            if 'lead_data' in data:
                # Formato antiguo con lead_data anidado
                lead_data = data['lead_data']
                # Mapear campos del formato antiguo al nuevo
                mapped_data = {
                    'user_id': str(lead_data.get('user_id', '')),
                    'name': lead_data.get('name', ''),
                    'first_name': lead_data.get('name', ''),  # usar name como first_name si no existe
                    'username': '',
                    'email': lead_data.get('email', ''),
                    'phone': lead_data.get('phone', ''),
                    'role': lead_data.get('role', ''),
                    'selected_course': lead_data.get('selected_course', ''),
                    'stage': lead_data.get('stage', 'initial'),
                    'has_accepted_privacy': lead_data.get('privacy_accepted', False),
                    'profile_type': '',
                    'interests': lead_data.get('interests', []) if isinstance(lead_data.get('interests'), list) else [],
                    'lead_score': lead_data.get('lead_score', 50),
                    'ad_source': lead_data.get('source', ''),
                    'score_history': [],
                    'message_history': data.get('history', []),
                    'course_presented': bool(data.get('last_presented_courses')),
                    'media_sent': False,
                    'last_interaction': datetime.fromtimestamp(data['last_activity']) if data.get('last_activity') else None,
                    'created_at': datetime.fromtimestamp(data['last_activity']) if data.get('last_activity') else None,
                    'updated_at': datetime.fromtimestamp(data['last_activity']) if data.get('last_activity') else None
                }
                lead = LeadMemory(**mapped_data)
            elif 'id' in data:
                # Formato con ID directo
                lead = LeadMemory.from_lead_data(data)
            else:
                # Formato directo de LeadMemory
                lead = LeadMemory.from_dict(data)
            
            self.leads_cache[user_id] = lead
            return lead
            
        except Exception as e:
            logger.error(f"Error loading lead memory for {user_id}: {e}")
            return None
    
    def _load_all_leads(self) -> None:
        """
        Carga todas las memorias de leads existentes.
        """
        try:
            for filename in os.listdir(self.memory_dir):
                if filename.startswith('memory_') and filename.endswith('.json'):
                    user_id = filename[7:-5]  # Extraer user_id del nombre del archivo
                    self.load_lead_memory(user_id)
            
            logger.info(f"Loaded {len(self.leads_cache)} lead memories")
            
        except Exception as e:
            logger.error(f"Error loading all leads: {e}")
    
    def get_all_leads(self) -> Dict[str, LeadMemory]:
        """
        Obtiene todas las memorias de leads.
        """
        return self.leads_cache.copy()
    
    def get_leads_by_stage(self, stage: str) -> List[LeadMemory]:
        """
        Obtiene leads filtrados por etapa.
        """
        return [lead for lead in self.leads_cache.values() if lead.stage == stage]
    
    def get_leads_by_score_range(self, min_score: int, max_score: int) -> List[LeadMemory]:
        """
        Obtiene leads filtrados por rango de puntuación.
        """
        return [
            lead for lead in self.leads_cache.values() 
            if min_score <= lead.lead_score <= max_score
        ]
    
    def get_inactive_leads(self, days: int = 7) -> List[LeadMemory]:
        """
        Obtiene leads que no han interactuado en X días.
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        inactive_leads = []
        
        for lead in self.leads_cache.values():
            last_interaction = lead.last_interaction or lead.created_at
            if last_interaction and last_interaction < cutoff_date:
                inactive_leads.append(lead)
        
        return inactive_leads
    
    def get_hot_leads(self, min_score: int = 80) -> List[LeadMemory]:
        """
        Obtiene leads con alta puntuación (calientes).
        """
        return [
            lead for lead in self.leads_cache.values() 
            if lead.lead_score >= min_score
        ]
    
    def update_lead_score(self, user_id: str, new_score: int, reason: str = "") -> bool:
        """
        Actualiza la puntuación de un lead.
        """
        try:
            if user_id in self.leads_cache:
                lead = self.leads_cache[user_id]
                old_score = lead.lead_score
                lead.lead_score = max(0, min(100, new_score))  # Mantener entre 0-100
                
                # Agregar al historial
                lead.score_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'old_score': old_score,
                    'new_score': lead.lead_score,
                    'reason': reason
                })
                
                # Mantener solo los últimos 20 registros
                lead.score_history = lead.score_history[-20:]
                
                # Guardar cambios
                return self.save_lead_memory(user_id, lead)
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating lead score for {user_id}: {e}")
            return False
    
    def add_message_to_history(self, user_id: str, message: str, response: str = "", metadata: Optional[Dict] = None) -> bool:
        """
        Agrega un mensaje al historial del lead.
        """
        try:
            if user_id in self.leads_cache:
                lead = self.leads_cache[user_id]
                
                message_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'message': message,
                    'response': response,
                    'metadata': metadata or {}
                }
                
                lead.message_history.append(message_entry)
                
                # Mantener solo los últimos 50 mensajes
                lead.message_history = lead.message_history[-50:]
                
                # Actualizar última interacción
                lead.last_interaction = datetime.now()
                
                return self.save_lead_memory(user_id, lead)
            
            return False
            
        except Exception as e:
            logger.error(f"Error adding message to history for {user_id}: {e}")
            return False
    
    def cleanup_old_memories(self, days: int = 90) -> int:
        """
        Limpia memorias antiguas que no han sido actualizadas en X días.
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cleaned_count = 0
            
            user_ids_to_remove = []
            
            for user_id, lead in self.leads_cache.items():
                last_update = lead.updated_at or lead.created_at
                if last_update and last_update < cutoff_date:
                    user_ids_to_remove.append(user_id)
            
            # Remover de cache y archivos
            for user_id in user_ids_to_remove:
                # Remover archivo
                filename = f"memory_{user_id}.json"
                filepath = os.path.join(self.memory_dir, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                # Remover de cache
                del self.leads_cache[user_id]
                cleaned_count += 1
            
            logger.info(f"Cleaned {cleaned_count} old lead memories")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning old memories: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de los leads.
        """
        try:
            total_leads = len(self.leads_cache)
            
            if total_leads == 0:
                return {
                    'total_leads': 0,
                    'average_score': 0,
                    'leads_by_stage': {},
                    'leads_by_score_range': {},
                    'hot_leads': 0,
                    'inactive_leads': 0
                }
            
            # Calcular estadísticas
            scores = [lead.lead_score for lead in self.leads_cache.values()]
            average_score = sum(scores) / len(scores)
            
            # Leads por etapa
            stages = {}
            for lead in self.leads_cache.values():
                stage = lead.stage
                stages[stage] = stages.get(stage, 0) + 1
            
            # Leads por rango de puntuación
            score_ranges = {
                'cold (0-30)': len([s for s in scores if 0 <= s <= 30]),
                'lukewarm (31-50)': len([s for s in scores if 31 <= s <= 50]),
                'warm (51-70)': len([s for s in scores if 51 <= s <= 70]),
                'hot (71-100)': len([s for s in scores if 71 <= s <= 100])
            }
            
            hot_leads = len(self.get_hot_leads())
            inactive_leads = len(self.get_inactive_leads())
            
            return {
                'total_leads': total_leads,
                'average_score': round(average_score, 2),
                'leads_by_stage': stages,
                'leads_by_score_range': score_ranges,
                'hot_leads': hot_leads,
                'inactive_leads': inactive_leads
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {} 