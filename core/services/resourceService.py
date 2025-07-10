"""
Servicio para gestionar recursos del bot desde la base de datos.
Integrado con la nueva estructura de base de datos.
"""

import logging
from typing import Dict, List, Optional, Any
from core.services.database import DatabaseService

logger = logging.getLogger(__name__)

class ResourceService:
    """Servicio para gestionar recursos del bot"""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
    
    async def get_resource_by_key(self, resource_key: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un recurso específico por su clave.
        
        Args:
            resource_key: Clave única del recurso
            
        Returns:
            Diccionario con los datos del recurso o None si no existe
        """
        try:
            async with self.db.pool.acquire() as connection:
                result = await connection.fetchrow(
                    """
                    SELECT 
                        id,
                        resource_type,
                        resource_key,
                        resource_url,
                        resource_title,
                        resource_description,
                        is_active
                    FROM bot_resources
                    WHERE resource_key = $1 AND is_active = true
                    """,
                    resource_key
                )
                
                if result:
                    return dict(result)
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo recurso por clave {resource_key}: {e}")
            return None
    
    async def get_course_resources(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los recursos asociados a un curso.
        
        Args:
            course_id: ID del curso
            
        Returns:
            Lista de recursos del curso
        """
        try:
            async with self.db.pool.acquire() as connection:
                results = await connection.fetch(
                    """
                    SELECT 
                        br.resource_key,
                        br.resource_title,
                        br.resource_type,
                        br.resource_url,
                        br.resource_description,
                        bcr.context_description,
                        bcr.priority
                    FROM bot_course_resources bcr
                    JOIN bot_resources br ON bcr.resource_id = br.id
                    WHERE bcr.course_id = $1 AND br.is_active = true
                    ORDER BY bcr.priority, br.resource_type
                    """,
                    course_id
                )
                
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error obteniendo recursos del curso {course_id}: {e}")
            return []
    
    async def get_session_resources(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los recursos asociados a una sesión.
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Lista de recursos de la sesión
        """
        try:
            async with self.db.pool.acquire() as connection:
                results = await connection.fetch(
                    """
                    SELECT 
                        br.resource_key,
                        br.resource_title,
                        br.resource_type,
                        br.resource_url,
                        br.resource_description,
                        bsr.context_description,
                        bsr.priority
                    FROM bot_session_resources bsr
                    JOIN bot_resources br ON bsr.resource_id = br.id
                    WHERE bsr.session_id = $1 AND br.is_active = true
                    ORDER BY bsr.priority, br.resource_type
                    """,
                    session_id
                )
                
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error obteniendo recursos de la sesión {session_id}: {e}")
            return []
    
    async def get_resources_by_type(self, resource_type: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los recursos de un tipo específico.
        
        Args:
            resource_type: Tipo de recurso (demo, pdf, video, etc.)
            
        Returns:
            Lista de recursos del tipo especificado
        """
        try:
            async with self.db.pool.acquire() as connection:
                results = await connection.fetch(
                    """
                    SELECT 
                        resource_key,
                        resource_title,
                        resource_type,
                        resource_url,
                        resource_description
                    FROM bot_resources
                    WHERE resource_type = $1 AND is_active = true
                    ORDER BY resource_title
                    """,
                    resource_type
                )
                
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error obteniendo recursos del tipo {resource_type}: {e}")
            return []
    
    async def get_resource_url(self, resource_key: str, fallback_url: str = None) -> str:
        """
        Obtiene la URL de un recurso específico con fallback.
        
        Args:
            resource_key: Clave del recurso
            fallback_url: URL de fallback si el recurso no existe
            
        Returns:
            URL del recurso o URL de fallback
        """
        try:
            resource = await self.get_resource_by_key(resource_key)
            if resource:
                return resource['resource_url']
            
            # Si no existe, devolver fallback o URL genérica
            if fallback_url:
                return fallback_url
            
            return f"https://aprenda-ia.com/{resource_key}"
            
        except Exception as e:
            logger.error(f"Error obteniendo URL del recurso {resource_key}: {e}")
            return fallback_url or f"https://aprenda-ia.com/{resource_key}"
    
    async def add_resource(self, resource_data: Dict[str, Any]) -> Optional[str]:
        """
        Agrega un nuevo recurso a la base de datos.
        
        Args:
            resource_data: Datos del recurso a agregar
            
        Returns:
            ID del recurso creado o None si falló
        """
        try:
            async with self.db.pool.acquire() as connection:
                result = await connection.fetchrow(
                    """
                    INSERT INTO bot_resources (
                        resource_type, resource_key, resource_url, 
                        resource_title, resource_description, is_active
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                    """,
                    resource_data.get('resource_type'),
                    resource_data.get('resource_key'),
                    resource_data.get('resource_url'),
                    resource_data.get('resource_title'),
                    resource_data.get('resource_description'),
                    resource_data.get('is_active', True)
                )
                
                if result:
                    logger.info(f"Recurso creado: {resource_data['resource_key']}")
                    return str(result['id'])
                
                return None
                
        except Exception as e:
            logger.error(f"Error agregando recurso: {e}")
            return None
    
    async def update_resource(self, resource_key: str, update_data: Dict[str, Any]) -> bool:
        """
        Actualiza un recurso existente.
        
        Args:
            resource_key: Clave del recurso a actualizar
            update_data: Datos a actualizar
            
        Returns:
            True si se actualizó correctamente, False si falló
        """
        try:
            async with self.db.pool.acquire() as connection:
                # Construir query dinámicamente basado en los campos a actualizar
                set_clauses = []
                values = []
                counter = 1
                
                for field, value in update_data.items():
                    if field in ['resource_type', 'resource_url', 'resource_title', 'resource_description', 'is_active']:
                        set_clauses.append(f"{field} = ${counter}")
                        values.append(value)
                        counter += 1
                
                if not set_clauses:
                    return False
                
                values.append(resource_key)
                
                query = f"""
                    UPDATE bot_resources 
                    SET {', '.join(set_clauses)}, updated_at = NOW()
                    WHERE resource_key = ${counter}
                """
                
                await connection.execute(query, *values)
                logger.info(f"Recurso actualizado: {resource_key}")
                return True
                
        except Exception as e:
            logger.error(f"Error actualizando recurso {resource_key}: {e}")
            return False
    
    async def link_resource_to_course(self, course_id: str, resource_key: str, context: str = None, priority: int = 1) -> bool:
        """
        Vincula un recurso a un curso específico.
        
        Args:
            course_id: ID del curso
            resource_key: Clave del recurso
            context: Descripción del contexto
            priority: Prioridad del recurso
            
        Returns:
            True si se vinculó correctamente, False si falló
        """
        try:
            async with self.db.pool.acquire() as connection:
                # Obtener el ID del recurso
                resource = await self.get_resource_by_key(resource_key)
                if not resource:
                    logger.error(f"Recurso no encontrado: {resource_key}")
                    return False
                
                # Insertar la relación
                await connection.execute(
                    """
                    INSERT INTO bot_course_resources (course_id, resource_id, context_description, priority)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (course_id, resource_id) DO UPDATE SET
                        context_description = EXCLUDED.context_description,
                        priority = EXCLUDED.priority
                    """,
                    course_id,
                    resource['id'],
                    context,
                    priority
                )
                
                logger.info(f"Recurso {resource_key} vinculado al curso {course_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error vinculando recurso {resource_key} al curso {course_id}: {e}")
            return False