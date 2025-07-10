"""
ResourceService - Servicio para obtener recursos desde la base de datos.
Funciona con las tablas bot_resources, bot_course_resources, etc.
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ResourceService:
    def __init__(self, db_service):
        self.db = db_service

    async def get_resource_url(self, resource_key: str, fallback_url: str = None) -> Optional[str]:
        """
        Obtiene URL de recurso por su key desde la tabla bot_resources.
        """
        try:
            if not self.db:
                return fallback_url
                
            result = await self.db.fetch_one(
                """
                SELECT resource_url FROM bot_resources 
                WHERE resource_key = $1 AND is_active = true
                LIMIT 1
                """,
                resource_key
            )
            
            if result:
                return result['resource_url']
            
            return fallback_url
            
        except Exception as e:
            logger.error(f"Error obteniendo recurso {resource_key}: {e}")
            return fallback_url

    async def get_course_resources(self, course_id: str) -> List[Dict]:
        """
        Obtiene recursos específicos de un curso desde bot_course_resources.
        """
        try:
            if not self.db:
                return []
                
            results = await self.db.fetch_all(
                """
                SELECT br.resource_type, br.resource_key, br.resource_url, 
                       br.resource_title, br.resource_description
                FROM bot_course_resources bcr
                JOIN bot_resources br ON bcr.resource_id = br.id
                WHERE bcr.course_id = $1 AND br.is_active = true
                ORDER BY bcr.priority ASC
                """,
                course_id
            )
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error obteniendo recursos del curso {course_id}: {e}")
            return []

    async def get_resources_by_type(self, resource_type: str) -> List[Dict]:
        """
        Obtiene recursos por tipo desde bot_resources.
        """
        try:
            if not self.db:
                return []
                
            results = await self.db.fetch_all(
                """
                SELECT resource_type, resource_key, resource_url, 
                       resource_title, resource_description
                FROM bot_resources 
                WHERE resource_type = $1 AND is_active = true
                ORDER BY created_at DESC
                """,
                resource_type
            )
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error obteniendo recursos tipo {resource_type}: {e}")
            return []

    async def get_free_resources(self, course_id: str = None) -> List[Dict]:
        """
        Obtiene recursos gratuitos desde free_resources.
        """
        try:
            if not self.db:
                return []
                
            if course_id:
                # Recursos específicos del curso
                results = await self.db.fetch_all(
                    """
                    SELECT resource_name, resource_type, resource_url, 
                           resource_description, tags
                    FROM free_resources 
                    WHERE course_id = $1 AND active = true
                    ORDER BY created_at DESC
                    """,
                    course_id
                )
            else:
                # Todos los recursos gratuitos
                results = await self.db.fetch_all(
                    """
                    SELECT resource_name, resource_type, resource_url, 
                           resource_description, tags
                    FROM free_resources 
                    WHERE active = true
                    ORDER BY created_at DESC
                    """,
                )
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error obteniendo recursos gratuitos: {e}")
            return []

    async def get_session_resources(self, session_id: str) -> List[Dict]:
        """
        Obtiene recursos específicos de una sesión desde bot_session_resources.
        """
        try:
            if not self.db:
                return []
                
            results = await self.db.fetch_all(
                """
                SELECT br.resource_type, br.resource_key, br.resource_url, 
                       br.resource_title, br.resource_description
                FROM bot_session_resources bsr
                JOIN bot_resources br ON bsr.resource_id = br.id
                WHERE bsr.session_id = $1 AND br.is_active = true
                ORDER BY bsr.priority ASC
                """,
                session_id
            )
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error obteniendo recursos de sesión {session_id}: {e}")
            return []