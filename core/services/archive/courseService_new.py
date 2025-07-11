"""
Servicio para consultas específicas de cursos - VERSIÓN MIGRADA
Implementa funciones que consultan la nueva estructura de base de datos
con ai_courses, ai_course_sessions, ai_session_practices, ai_session_deliverables.
"""

# Protección temprana contra ejecución directa
if __name__ == "__main__":
    print("❌ Este archivo es un módulo y no debe ejecutarse directamente.")
    print("💡 Úsalo importándolo desde el bot principal: agente_ventas_telegram.py")
    print("✅ Las importaciones están correctas para uso como módulo.")
    import sys
    sys.exit(0)

import logging
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.services.database import DatabaseService
else:
    try:
        from core.services.database import DatabaseService
    except ImportError:
        print("⚠️ DatabaseService no disponible - asegúrate de que las dependencias estén instaladas")
        DatabaseService = None

logger = logging.getLogger(__name__)

class CourseService:
    """
    Servicio para consultas específicas de cursos - VERSIÓN MIGRADA.
    Proporciona métodos para obtener información detallada de cursos
    desde la nueva estructura de base de datos.
    """
    
    def __init__(self, db_service: "DatabaseService"):
        """Inicializa el servicio con una conexión a la base de datos."""
        self.db = db_service
    
    async def getCourseDetails(self, courseId: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene todos los detalles de un curso específico, incluyendo sus sesiones.
        MIGRADO: Usa ai_courses y ai_course_sessions
        
        Args:
            courseId: ID único del curso
            
        Returns:
            Diccionario con todos los campos del curso y sus sesiones
        """
        try:
            query = """
            SELECT 
                c.*,
                st.name as subtheme_name,
                st.description as subtheme_description,
                json_agg(
                    DISTINCT jsonb_build_object(
                        'id', s.id,
                        'session_index', s.session_index,
                        'title', s.title,
                        'objective', s.objective,
                        'duration_minutes', s.duration_minutes,
                        'modality', s.modality,
                        'display_order', s.display_order
                    )
                ) as sessions
            FROM ai_courses c
            LEFT JOIN ai_subthemes st ON c.subtheme_id = st.id
            LEFT JOIN ai_course_sessions s ON s.course_id = c.id
            WHERE c.id = $1
            GROUP BY c.id, st.name, st.description;
            """
            
            result = await self.db.fetch_one(query, courseId)
            return result
        except Exception as e:
            logger.error(f"Error obteniendo detalles del curso {courseId}: {e}")
            return None
    
    async def searchCourses(self, search_query: str) -> List[Dict[str, Any]]:
        """
        Busca cursos por nombre, descripción, categoría o audiencia.
        MIGRADO: Usa ai_courses y ai_subthemes
        
        Args:
            search_query: Texto para buscar en los campos del curso
            
        Returns:
            Lista de cursos que coinciden con la búsqueda
        """
        try:
            query = """
            SELECT 
                c.*,
                st.name as subtheme_name
            FROM ai_courses c
            LEFT JOIN ai_subthemes st ON c.subtheme_id = st.id
            WHERE 
                c.status = 'publicado' AND
                (
                    c.name ILIKE $1 OR
                    c.short_description ILIKE $1 OR
                    c.long_description ILIKE $1 OR
                    c.audience_category ILIKE $1 OR
                    st.name ILIKE $1 OR
                    st.description ILIKE $1
                )
            ORDER BY c.created_at DESC;
            """
            
            search_pattern = f"%{search_query}%"
            results = await self.db.fetch_all(query, search_pattern)
            return results or []
        except Exception as e:
            logger.error(f"Error buscando cursos con query '{search_query}': {e}")
            return []
    
    async def getCourseModules(self, courseId: str) -> List[Dict[str, Any]]:
        """
        Obtiene todas las sesiones de un curso específico.
        MIGRADO: Usa ai_course_sessions (equivalente a course_modules)
        
        Args:
            courseId: ID único del curso
            
        Returns:
            Lista de sesiones del curso con título, objetivo y duración
        """
        try:
            query = """
            SELECT 
                id, 
                title as name,  -- Mapear title a name para compatibilidad
                objective as description,  -- Mapear objective a description
                duration_minutes as duration,
                session_index as module_index  -- Mapear para compatibilidad
            FROM ai_course_sessions
            WHERE course_id = $1
            ORDER BY session_index;
            """
            
            results = await self.db.fetch_all(query, courseId)
            return results or []
        except Exception as e:
            logger.error(f"Error obteniendo sesiones del curso {courseId}: {e}")
            return []
    
    async def getCoursePrompts(self, courseId: str) -> List[Dict[str, Any]]:
        """
        ELIMINADO: Esta función ya no está disponible en la nueva estructura.
        La tabla course_prompts no existe en la nueva estructura.
        
        Args:
            courseId: ID único del curso
            
        Returns:
            Lista vacía (funcionalidad eliminada)
        """
        logger.warning(f"getCoursePrompts() eliminado en migración - no hay equivalente para curso {courseId}")
        return []
    
    async def getCourseSales(self, courseId: str) -> int:
        """
        Obtiene el número de ventas de un curso específico.
        MANTENIDO: Tabla course_sales se mantiene sin cambios
        
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
        MANTENIDO: Tabla course_interactions se mantiene sin cambios
        
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

    async def getModuleExercises(self, moduleId: str) -> List[Dict[str, Any]]:
        """
        Obtiene todas las prácticas de una sesión específica.
        MIGRADO: Usa ai_session_practices (equivalente a module_exercises)
        
        Args:
            moduleId: ID único de la sesión (anteriormente módulo)
            
        Returns:
            Lista de prácticas de la sesión
        """
        try:
            query = """
            SELECT 
                id, 
                description, 
                practice_index as order_idx,  -- Mapear para compatibilidad
                title,
                notes,
                estimated_duration_min,
                resource_type,
                is_mandatory
            FROM ai_session_practices
            WHERE session_id = $1
            ORDER BY practice_index;
            """
            results = await self.db.fetch_all(query, moduleId)
            return results or []
        except Exception as e:
            logger.error(f"Error obteniendo prácticas de la sesión {moduleId}: {e}")
            return [] 

    async def getAvailableBonuses(self, courseId: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los bonos por tiempo limitado disponibles para un curso.
        MANTENIDO: Tabla limited_time_bonuses se mantiene sin cambios
        
        Args:
            courseId: ID único del curso
            
        Returns:
            Lista de bonos disponibles con su información completa
        """
        try:
            query = """
            SELECT *
            FROM limited_time_bonuses
            WHERE 
                course_id = $1 AND
                active = true AND
                expires_at > NOW() AND
                (current_claims < max_claims OR max_claims = 0)
            ORDER BY expires_at ASC;
            """
            
            results = await self.db.fetch_all(query, courseId)
            return results or []
        except Exception as e:
            logger.error(f"Error obteniendo bonos del curso {courseId}: {e}")
            return [] 

    async def getCourseBasicInfo(self, courseId: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información básica específica del curso para mostrar en mensajes.
        MIGRADO: Usa ai_courses con campos actualizados
        
        Args:
            courseId: ID único del curso
            
        Returns:
            Diccionario con campos básicos: name, short_description, total_duration_min, level, price
        """
        try:
            query = """
            SELECT 
                id,
                name,
                short_description,
                total_duration_min as total_duration,  -- Mapear para compatibilidad
                level,
                price as price_usd,  -- Mapear para compatibilidad
                status,
                currency,
                session_count,
                audience_category
            FROM ai_courses 
            WHERE id = $1 AND status = 'publicado';
            """
            
            result = await self.db.fetch_one(query, courseId)
            return result
        except Exception as e:
            logger.error(f"Error obteniendo información básica del curso {courseId}: {e}")
            return None

    async def getSessionDeliverables(self, sessionId: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los entregables de una sesión específica.
        NUEVO: Funcionalidad agregada para la nueva estructura
        
        Args:
            sessionId: ID único de la sesión
            
        Returns:
            Lista de entregables de la sesión
        """
        try:
            query = """
            SELECT 
                id,
                name,
                type,
                resource_url,
                estimated_duration_min,
                resource_type,
                is_mandatory
            FROM ai_session_deliverables
            WHERE session_id = $1
            ORDER BY name;
            """
            
            results = await self.db.fetch_all(query, sessionId)
            return results or []
        except Exception as e:
            logger.error(f"Error obteniendo entregables de la sesión {sessionId}: {e}")
            return []

    async def getCourseSubtheme(self, courseId: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información del subtema asociado a un curso.
        NUEVO: Funcionalidad agregada para la nueva estructura
        
        Args:
            courseId: ID único del curso
            
        Returns:
            Diccionario con información del subtema
        """
        try:
            query = """
            SELECT 
                st.id,
                st.name,
                st.description
            FROM ai_subthemes st
            JOIN ai_courses c ON c.subtheme_id = st.id
            WHERE c.id = $1;
            """
            
            result = await self.db.fetch_one(query, courseId)
            return result
        except Exception as e:
            logger.error(f"Error obteniendo subtema del curso {courseId}: {e}")
            return None

    async def getFreeResources(self, courseId: str) -> List[Dict[str, Any]]:
        """
        Obtiene recursos gratuitos para un curso específico.
        MIGRADO: Usa ai_session_deliverables en lugar de free_resources
        
        Args:
            courseId: ID único del curso
            
        Returns:
            Lista de recursos gratuitos disponibles
        """
        try:
            query = """
            SELECT 
                d.id,
                d.name as resource_name,  -- Mapear para compatibilidad
                d.type as resource_type,
                d.resource_url,
                d.estimated_duration_min,
                d.is_mandatory,
                s.title as session_title
            FROM ai_session_deliverables d
            JOIN ai_course_sessions s ON d.session_id = s.id
            WHERE s.course_id = $1 AND d.is_mandatory = false
            ORDER BY s.session_index, d.name;
            """
            
            results = await self.db.fetch_all(query, courseId)
            return results or []
        except Exception as e:
            logger.error(f"Error obteniendo recursos gratuitos del curso {courseId}: {e}")
            return []

# Protección para evitar ejecución directa del módulo
if __name__ == "__main__":
    print("❌ Este archivo es un módulo y no debe ejecutarse directamente.")
    print("💡 Úsalo importándolo desde el bot principal: agente_ventas_telegram.py")
    print("✅ Las importaciones están correctas para uso como módulo.")
    import sys
    sys.exit(0)  # Exit 0 para indicar que no es un error, solo prevención