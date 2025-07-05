"""
Servicio para consultas específicas de cursos.
Implementa funciones que consultan directamente la base de datos
sin transformaciones ni interpretaciones, retornando datos exactos.
"""

import logging
from typing import Dict, List, Optional, Any
import asyncpg

from config.settings import settings
from core.services.database import DatabaseService

logger = logging.getLogger(__name__)

class CourseService:
    """
    Servicio para consultas específicas de cursos.
    Proporciona métodos para obtener información detallada de cursos
    directamente desde la base de datos.
    """
    
    def __init__(self, db_service: DatabaseService):
        """Inicializa el servicio con una conexión a la base de datos."""
        self.db = db_service
    
    async def getCourseDetails(self, courseId: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene todos los detalles de un curso específico, incluyendo sus módulos.
        
        Args:
            courseId: ID único del curso
            
        Returns:
            Diccionario con todos los campos del curso y sus módulos
        """
        try:
            query = """
            SELECT 
                c.*,
                json_agg(DISTINCT cm.*) as modules
            FROM courses c
            LEFT JOIN course_modules cm ON cm.course_id = c.id
            WHERE c.id = $1
            GROUP BY c.id;
            """
            
            result = await self.db.fetch_one(query, courseId)
            return result
        except Exception as e:
            logger.error(f"Error obteniendo detalles del curso {courseId}: {e}")
            return None
    
    async def searchCourses(self, search_query: str) -> List[Dict[str, Any]]:
        """
        Busca cursos por nombre, descripción, categoría o herramientas.
        
        Args:
            search_query: Texto para buscar en los campos del curso
            
        Returns:
            Lista de cursos que coinciden con la búsqueda
        """
        try:
            query = """
            SELECT * FROM courses
            WHERE 
                published = true AND
                (
                    name ILIKE $1 OR
                    short_description ILIKE $1 OR
                    long_description ILIKE $1 OR
                    category ILIKE $1 OR
                    $1 = ANY(tools_used)
                )
            ORDER BY created_at DESC;
            """
            
            search_pattern = f"%{search_query}%"
            results = await self.db.fetch_all(query, search_pattern)
            return results or []
        except Exception as e:
            logger.error(f"Error buscando cursos con query '{search_query}': {e}")
            return []
    
    async def getCourseModules(self, courseId: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los módulos de un curso específico.
        
        Args:
            courseId: ID único del curso
            
        Returns:
            Lista de módulos del curso con nombre, descripción y duración
        """
        try:
            query = """
            SELECT 
                id, name, description, duration, module_index
            FROM course_modules
            WHERE course_id = $1
            ORDER BY module_index;
            """
            
            results = await self.db.fetch_all(query, courseId)
            return results or []
        except Exception as e:
            logger.error(f"Error obteniendo módulos del curso {courseId}: {e}")
            return []
    
    async def getCoursePrompts(self, courseId: str) -> List[Dict[str, Any]]:
        """
        Obtiene ejemplos de prompts para un curso específico.
        
        Args:
            courseId: ID único del curso
            
        Returns:
            Lista de prompts de ejemplo para el curso
        """
        try:
            query = """
            SELECT 
                id, usage, prompt
            FROM course_prompts
            WHERE course_id = $1;
            """
            
            results = await self.db.fetch_all(query, courseId)
            return results or []
        except Exception as e:
            logger.error(f"Error obteniendo prompts del curso {courseId}: {e}")
            return []
    
    async def getCourseSales(self, courseId: str) -> int:
        """
        Obtiene el número de ventas de un curso específico.
        
        Args:
            courseId: ID único del curso
            
        Returns:
            Número de ventas del curso
        """
        try:
            query = """
            SELECT COUNT(*) as total_sales
            FROM course_sales
            WHERE course_id = $1 AND payment_status = 'completed';
            """
            
            result = await self.db.fetch_one(query, courseId)
            return result['total_sales'] if result else 0
        except Exception as e:
            logger.error(f"Error obteniendo ventas del curso {courseId}: {e}")
            return 0
    
    async def getCourseInteractions(self, courseId: str) -> List[Dict[str, Any]]:
        """
        Obtiene todas las interacciones con un curso específico.
        
        Args:
            courseId: ID único del curso
            
        Returns:
            Lista de interacciones con el curso
        """
        try:
            query = """
            SELECT 
                ci.*, ul.name as lead_name, ul.role as lead_role
            FROM course_interactions ci
            JOIN user_leads ul ON ci.lead_id = ul.id
            WHERE ci.course_id = $1
            ORDER BY ci.created_at DESC;
            """
            
            results = await self.db.fetch_all(query, courseId)
            return results or []
        except Exception as e:
            logger.error(f"Error obteniendo interacciones del curso {courseId}: {e}")
            return [] 