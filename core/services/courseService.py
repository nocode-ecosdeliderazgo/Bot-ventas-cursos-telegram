"""
Servicio para consultas específicas de cursos - VERSIÓN HÍBRIDA
Funciona con estructura actual (courses, course_modules) y nueva (ai_courses, ai_course_sessions)
Detecta automáticamente qué estructura usar según disponibilidad.
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
    Servicio para consultas específicas de cursos - VERSIÓN HÍBRIDA.
    Funciona con estructura actual y nueva automáticamente.
    """
    
    def __init__(self, db_service: "DatabaseService"):
        """Inicializa el servicio con una conexión a la base de datos."""
        self.db = db_service
        self._structure_checked = False
        self._use_new_structure = False
    
    async def _check_structure(self) -> bool:
        """Detecta automáticamente qué estructura de BD usar"""
        if self._structure_checked:
            return self._use_new_structure
            
        try:
            # Intentar consultar la nueva estructura - FORZAR para debug
            query = "SELECT COUNT(*) FROM ai_courses LIMIT 1;"
            result = await self.db.fetch_one(query)
            if result is not None:
                self._use_new_structure = True
                logger.info("✅ NUEVA ESTRUCTURA DETECTADA - ai_courses existe y tiene datos")
                
                # Verificar también ai_course_sessions
                sessions_query = "SELECT COUNT(*) FROM ai_course_sessions LIMIT 1;"
                sessions_result = await self.db.fetch_one(sessions_query)
                logger.info(f"✅ ai_course_sessions también existe - conteo: {sessions_result}")
            else:
                logger.warning("⚠️ ai_courses existe pero está vacía")
                self._use_new_structure = False
        except Exception as e:
            # Si falla, usar estructura actual
            logger.error(f"❌ Error consultando nueva estructura: {e}")
            self._use_new_structure = False
            logger.info("✅ Usando estructura actual de BD (courses)")
            
        self._structure_checked = True
        logger.info(f"📊 Resultado detección estructura: use_new_structure = {self._use_new_structure}")
        return self._use_new_structure
    
    async def getCourseBasicInfo(self, courseId: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información básica específica del curso para mostrar en mensajes.
        HÍBRIDO: Usa estructura actual o nueva según disponibilidad
        """
        try:
            use_new = await self._check_structure()
            logger.info(f"🔍 getCourseBasicInfo para curso {courseId} - usando nueva estructura: {use_new}")
            
            if use_new:
                # Nueva estructura
                query = """
                SELECT 
                    id,
                    name,
                    short_description,
                    total_duration_min as total_duration,
                    level,
                    price as price_usd,
                    status,
                    currency,
                    session_count,
                    audience_category
                FROM ai_courses 
                WHERE id = $1 AND status = 'publicado';
                """
                logger.info(f"📋 Ejecutando query NUEVA estructura básica para curso {courseId}")
            else:
                # Estructura actual
                query = """
                SELECT 
                    id,
                    name,
                    short_description,
                    total_duration,
                    level,
                    price_usd,
                    'activo' as status,
                    currency,
                    0 as session_count,
                    category as audience_category
                FROM courses 
                WHERE id = $1 AND published = true;
                """
                logger.info(f"📋 Ejecutando query ANTIGUA estructura básica para curso {courseId}")
            
            result = await self.db.fetch_one(query, courseId)
            
            if result:
                logger.info(f"✅ Información básica encontrada para curso {courseId}: {result.get('name', 'Sin nombre')}")
            else:
                logger.warning(f"❌ NO se encontró información básica para curso {courseId}")
                
            return result
        except Exception as e:
            logger.error(f"❌ Error obteniendo información básica del curso {courseId}: {e}")
            return None

    async def getCourseDetails(self, courseId: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene todos los detalles de un curso específico, incluyendo sus sesiones/módulos.
        HÍBRIDO: Usa estructura actual o nueva según disponibilidad
        """
        try:
            use_new = await self._check_structure()
            
            if use_new:
                # Nueva estructura
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
            else:
                # Estructura actual
                query = """
                SELECT 
                    c.*,
                    json_agg(
                        DISTINCT jsonb_build_object(
                            'id', m.id,
                            'module_index', m.module_index,
                            'name', m.name,
                            'description', m.description,
                            'duration', m.duration
                        )
                    ) as modules
                FROM courses c
                LEFT JOIN course_modules m ON m.course_id = c.id
                WHERE c.id = $1
                GROUP BY c.id;
                """
            
            result = await self.db.fetch_one(query, courseId)
            return result
        except Exception as e:
            logger.error(f"Error obteniendo detalles del curso {courseId}: {e}")
            return None
    
    async def getCourseModules(self, courseId: str) -> List[Dict[str, Any]]:
        """
        Obtiene todas las sesiones/módulos de un curso específico.
        HÍBRIDO: Usa estructura actual o nueva según disponibilidad
        """
        try:
            use_new = await self._check_structure()
            logger.info(f"🔍 getCourseModules para curso {courseId} - usando nueva estructura: {use_new}")
            
            if use_new:
                # Nueva estructura
                query = """
                SELECT 
                    id, 
                    title as name,
                    objective as description,
                    duration_minutes as duration,
                    session_index as module_index
                FROM ai_course_sessions
                WHERE course_id = $1
                ORDER BY session_index;
                """
                logger.info(f"📋 Ejecutando query NUEVA estructura para curso {courseId}")
            else:
                # Estructura actual
                query = """
                SELECT 
                    id, 
                    name,
                    description,
                    duration,
                    module_index
                FROM course_modules
                WHERE course_id = $1
                ORDER BY module_index;
                """
                logger.info(f"📋 Ejecutando query ANTIGUA estructura para curso {courseId}")
            
            results = await self.db.fetch_all(query, courseId)
            
            if results:
                logger.info(f"✅ Encontradas {len(results)} sesiones/módulos para curso {courseId}")
                # Log del primer resultado para debug
                logger.info(f"📄 Primer resultado: {results[0] if results else 'N/A'}")
            else:
                logger.warning(f"❌ NO se encontraron sesiones/módulos para curso {courseId}")
                
            return results or []
        except Exception as e:
            logger.error(f"❌ Error obteniendo módulos/sesiones del curso {courseId}: {e}")
            return []

    async def searchCourses(self, search_query: str) -> List[Dict[str, Any]]:
        """
        Busca cursos por nombre, descripción, categoría o audiencia.
        HÍBRIDO: Usa estructura actual o nueva según disponibilidad
        """
        try:
            use_new = await self._check_structure()
            
            if use_new:
                # Nueva estructura
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
            else:
                # Estructura actual
                query = """
                SELECT 
                    *
                FROM courses
                WHERE 
                    published = true AND
                    (
                        name ILIKE $1 OR
                        short_description ILIKE $1 OR
                        long_description ILIKE $1 OR
                        category ILIKE $1
                    )
                ORDER BY created_at DESC;
                """
            
            search_pattern = f"%{search_query}%"
            results = await self.db.fetch_all(query, search_pattern)
            return results or []
        except Exception as e:
            logger.error(f"Error buscando cursos con query '{search_query}': {e}")
            return []

    async def getModuleExercises(self, moduleId: str) -> List[Dict[str, Any]]:
        """
        Obtiene todas las prácticas/ejercicios de una sesión/módulo específico.
        HÍBRIDO: Usa estructura actual o nueva según disponibilidad
        """
        try:
            use_new = await self._check_structure()
            
            if use_new:
                # Nueva estructura
                query = """
                SELECT 
                    id, 
                    description, 
                    practice_index as order_idx,
                    title,
                    notes,
                    estimated_duration_min,
                    resource_type,
                    is_mandatory
                FROM ai_session_practices
                WHERE session_id = $1
                ORDER BY practice_index;
                """
            else:
                # Estructura actual
                query = """
                SELECT 
                    id,
                    description,
                    order_idx,
                    'Ejercicio' as title,
                    '' as notes,
                    0 as estimated_duration_min,
                    'exercise' as resource_type,
                    true as is_mandatory
                FROM module_exercises
                WHERE module_id = $1
                ORDER BY order_idx;
                """
            
            results = await self.db.fetch_all(query, moduleId)
            return results or []
        except Exception as e:
            logger.error(f"Error obteniendo ejercicios/prácticas del módulo/sesión {moduleId}: {e}")
            return []

    async def getAvailableBonuses(self, courseId: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los bonos por tiempo limitado disponibles para un curso.
        MANTENIDO: Esta tabla no cambia en la migración
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

    async def getSessionDeliverables(self, sessionId: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los entregables de una sesión específica.
        HÍBRIDO: Solo disponible en nueva estructura
        """
        try:
            use_new = await self._check_structure()
            
            if use_new:
                # Nueva estructura
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
            else:
                # Estructura actual no tiene entregables por sesión
                return []
        except Exception as e:
            logger.error(f"Error obteniendo entregables de la sesión {sessionId}: {e}")
            return []

    async def getCourseSubtheme(self, courseId: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información del subtema asociado a un curso.
        HÍBRIDO: Solo disponible en nueva estructura
        """
        try:
            use_new = await self._check_structure()
            
            if use_new:
                # Nueva estructura
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
            else:
                # Estructura actual no tiene subtemas
                return None
        except Exception as e:
            logger.error(f"Error obteniendo subtema del curso {courseId}: {e}")
            return None

    async def getFreeResources(self, courseId: str) -> List[Dict[str, Any]]:
        """
        Obtiene recursos gratuitos para un curso específico.
        HÍBRIDO: Usa estructura actual o nueva según disponibilidad
        """
        try:
            use_new = await self._check_structure()
            
            if use_new:
                # Nueva estructura
                query = """
                SELECT 
                    d.id,
                    d.name as resource_name,
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
            else:
                # Estructura actual
                query = """
                SELECT 
                    id,
                    resource_name,
                    resource_type,
                    resource_url,
                    0 as estimated_duration_min,
                    false as is_mandatory,
                    '' as session_title
                FROM free_resources
                WHERE course_id = $1
                ORDER BY resource_name;
                """
            
            results = await self.db.fetch_all(query, courseId)
            return results or []
        except Exception as e:
            logger.error(f"Error obteniendo recursos gratuitos del curso {courseId}: {e}")
            return []

    # Métodos que no cambian en la migración
    async def getCoursePrompts(self, courseId: str) -> List[Dict[str, Any]]:
        """
        ELIMINADO: Esta función ya no está disponible en la nueva estructura.
        En estructura actual, aún puede funcionar.
        """
        try:
            use_new = await self._check_structure()
            
            if use_new:
                logger.warning(f"getCoursePrompts() eliminado en migración - no hay equivalente para curso {courseId}")
                return []
            else:
                # Intentar obtener de estructura actual si existe
                query = """
                SELECT *
                FROM course_prompts
                WHERE course_id = $1
                ORDER BY created_at;
                """
                
                results = await self.db.fetch_all(query, courseId)
                return results or []
        except Exception as e:
            logger.error(f"Error obteniendo prompts del curso {courseId}: {e}")
            return []
    
    async def getCourseSales(self, courseId: str) -> int:
        """
        Obtiene el número de ventas de un curso específico.
        MANTENIDO: Esta tabla no cambia en la migración
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
        MANTENIDO: Esta tabla no cambia en la migración
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

# Protección para evitar ejecución directa del módulo
if __name__ == "__main__":
    print("❌ Este archivo es un módulo y no debe ejecutarse directamente.")
    print("💡 Úsalo importándolo desde el bot principal: agente_ventas_telegram.py")
    print("✅ Las importaciones están correctas para uso como módulo.")
    import sys
    sys.exit(0)