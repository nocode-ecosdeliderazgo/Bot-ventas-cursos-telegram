"""
Servicio para interactuar con la base de datos PostgreSQL.
"""

from typing import Dict, List, Optional, Any
import asyncpg
from datetime import datetime

class DatabaseService:
    def __init__(self, connection_string: str):
        self.conn_string = connection_string
        self.pool = None

    async def connect(self) -> None:
        """
        Establece el pool de conexiones a la base de datos.
        """
        self.pool = await asyncpg.create_pool(
            self.conn_string,
            min_size=2,
            max_size=10
        )

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """
        Ejecuta una query y retorna un solo resultado como diccionario.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """
        Ejecuta una query y retorna todos los resultados como lista de diccionarios.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def execute(self, query: str, *args) -> str:
        """
        Ejecuta una query que no retorna resultados (INSERT, UPDATE, DELETE).
        Retorna el ID del registro afectado si está disponible.
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, *args)
            return result

    async def get_course_details(self, course_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene todos los detalles relevantes de un curso, incluyendo bonos activos.
        """
        query = """
        SELECT 
            c.*,
            json_agg(DISTINCT cm.*) as modules,
            json_agg(DISTINCT ltb.*) FILTER (WHERE ltb.active = true AND ltb.expires_at > NOW()) as active_bonuses
        FROM courses c
        LEFT JOIN course_modules cm ON cm.course_id = c.id
        LEFT JOIN limited_time_bonuses ltb ON ltb.course_id = c.id
        WHERE c.id = $1
        GROUP BY c.id;
        """
        return await self.fetch_one(query, course_id)

    async def get_lead_profile(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el perfil completo de un lead, incluyendo sus interacciones.
        """
        query = """
        SELECT 
            l.*,
            json_agg(DISTINCT ci.*) as course_interactions,
            json_agg(DISTINCT c.*) FILTER (WHERE c.created_at > NOW() - INTERVAL '24 hours') as recent_conversations
        FROM user_leads l
        LEFT JOIN course_interactions ci ON ci.lead_id = l.id
        LEFT JOIN conversations c ON c.lead_id = l.id
        WHERE l.id = $1
        GROUP BY l.id;
        """
        return await self.fetch_one(query, lead_id)

    async def register_interaction(
        self,
        lead_id: str,
        course_id: str,
        interaction_type: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Registra una nueva interacción de un lead con un curso.
        """
        query = """
        INSERT INTO course_interactions (
            lead_id, course_id, interaction_type, metadata
        ) VALUES ($1, $2, $3, $4)
        RETURNING id;
        """
        return await self.execute(query, lead_id, course_id, interaction_type, metadata)

    async def update_lead_score(self, lead_id: str, new_score: int) -> None:
        """
        Actualiza el score de interés de un lead.
        """
        query = """
        UPDATE user_leads 
        SET 
            interest_score = $2,
            updated_at = NOW()
        WHERE id = $1;
        """
        await self.execute(query, lead_id, new_score)

    async def close(self) -> None:
        """
        Cierra el pool de conexiones.
        """
        if self.pool:
            await self.pool.close() 