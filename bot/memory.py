# ==============================
# MEMORIA DE USUARIO Y PERSISTENCIA
# ==============================
# Este módulo define la estructura de memoria por usuario y helpers de persistencia.

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
logger = logging.getLogger(__name__)

# ==============================
# LEAD MEMORY (per user)
# ==============================
class LeadMemory:
    """Almacena los datos principales del lead/usuario."""
    def __init__(self):
        self.user_id: str = ""
        self.name: str = ""
        self.email: str = ""
        self.phone: str = ""
        self.selected_course: Optional[str] = None
        self.interests: List[str] = []
        self.stage: str = "inicio"
        self.privacy_accepted: bool = False  # Indica si aceptó privacidad
        self.courses_seen: set = set()
        self.escalation_pending: bool = False
        self.role: Optional[str] = None
        self.lead_score: int = 0
        self.awaiting_ack: bool = False
        self.last_ack_time: Optional[float] = None
        self.source: Optional[str] = None  # Para tracking de origen (ej: anuncios)

class Memory:
    """Memoria completa de usuario, historial y helpers de persistencia."""
    def __init__(self):
        self.lead_data: LeadMemory = LeadMemory()
        self.history: List[Dict[str, Any]] = []  # Historial de interacciones
        self.last_presented_courses: List[Dict[str, Any]] = [] # Últimos cursos presentados
        self.last_activity: float = time.time()

    def load(self, user_id: str) -> bool:
        """Carga la memoria específica de un usuario desde disco."""
        try:
            # Crear archivo específico por usuario
            user_memory_file = os.path.join("memorias", f"memory_{user_id}.json")
            
            with open(user_memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Verificar si los datos no son muy antiguos (más de 30 días)
            last_activity = data.get("last_activity", 0)
            if time.time() - last_activity > 30 * 24 * 3600:  # 30 días
                logger.info(f"Memoria de usuario {user_id} muy antigua, inicializando nueva")
                self.lead_data.user_id = user_id
                self.lead_data.stage = "inicio"
                return False
                
            if data.get("lead_data"):
                self.lead_data.user_id = data["lead_data"].get("user_id")
                self.lead_data.email = data["lead_data"].get("email")
                self.lead_data.phone = data["lead_data"].get("phone")
                self.lead_data.stage = data["lead_data"].get("stage", "inicio")
                self.lead_data.courses_seen = set(data["lead_data"].get("courses_seen", []))
                self.lead_data.selected_course = data["lead_data"].get("selected_course")
                self.lead_data.escalation_pending = data["lead_data"].get("escalation_pending", False)
                self.lead_data.name = data["lead_data"].get("name")
                self.lead_data.role = data["lead_data"].get("role")
                self.lead_data.interests = data["lead_data"].get("interests", [])
                self.lead_data.lead_score = data["lead_data"].get("lead_score", 0)
                self.lead_data.awaiting_ack = data["lead_data"].get("awaiting_ack", False)
                self.lead_data.last_ack_time = data["lead_data"].get("last_ack_time")
                self.lead_data.privacy_accepted = data["lead_data"].get("privacy_accepted", False)
                self.lead_data.source = data["lead_data"].get("source")
                
            self.history = data.get("history", [])
            self.last_presented_courses = data.get("last_presented_courses", [])
            self.last_activity = data.get("last_activity", time.time())
            
            logger.info(f"Memoria cargada para usuario {user_id}")
            return True
            
        except FileNotFoundError:
            logger.info(f"Archivo de memoria no encontrado para usuario {user_id}, inicializando nueva")
            self.lead_data.user_id = user_id
            self.lead_data.stage = "inicio"
            return False
        except Exception as e:
            logger.error(f"Error cargando memoria para usuario {user_id}: {e}")
            self.lead_data.user_id = user_id
            self.lead_data.stage = "inicio"
            return False

    def save(self):
        """Guarda memoria específica para el usuario actual"""
        try:
            user_memory_file = os.path.join("memorias", f"memory_{self.lead_data.user_id}.json")
            self.last_activity = time.time()
            
            data = {
                "lead_data": {
                    "user_id": self.lead_data.user_id,
                    "email": self.lead_data.email,
                    "phone": self.lead_data.phone,
                    "stage": self.lead_data.stage,
                    "courses_seen": list(self.lead_data.courses_seen),
                    "selected_course": self.lead_data.selected_course,
                    "escalation_pending": self.lead_data.escalation_pending,
                    "name": self.lead_data.name,
                    "role": self.lead_data.role,
                    "interests": ", ".join(self.lead_data.interests),
                    "lead_score": self.lead_data.lead_score,
                    "awaiting_ack": self.lead_data.awaiting_ack,
                    "last_ack_time": self.lead_data.last_ack_time,
                    "privacy_accepted": self.lead_data.privacy_accepted,
                    "source": self.lead_data.source
                },
                "history": self.history[-50:],  # Mantener solo los últimos 50 mensajes
                "last_presented_courses": self.last_presented_courses,
                "last_activity": self.last_activity
            }
            
            with open(user_memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
                
            logger.debug(f"Memoria guardada para usuario {self.lead_data.user_id}")
            
        except Exception as e:
            logger.error(f"Error guardando memoria para usuario {self.lead_data.user_id}: {e}")

    @staticmethod
    def cleanup_old_memories():
        """Limpia archivos de memoria antiguos"""
        try:
            current_time = time.time()
            memory_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memorias")
            
            for filename in os.listdir(memory_dir):
                if filename.startswith("memory_") and filename.endswith(".json"):
                    filepath = os.path.join(memory_dir, filename)
                    file_time = os.path.getmtime(filepath)
                    
                    # Eliminar archivos más antiguos de 30 días
                    if current_time - file_time > 30 * 24 * 3600:
                        os.remove(filepath)
                        logger.info(f"Archivo de memoria eliminado: {filename}")
                        
        except Exception as e:
            logger.error(f"Error limpiando memorias antiguas: {e}")
