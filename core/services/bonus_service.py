"""
Servicio para manejar bonos exclusivos y ofertas especiales.
"""

import logging
from typing import Dict, List, Optional
from core.services.database import DatabaseService

logger = logging.getLogger(__name__)

class BonusService:
    def __init__(self, db: DatabaseService):
        self.db = db

    async def get_course_bonuses(self, course_id: str) -> List[Dict]:
        """
        Obtiene todos los bonos activos para un curso específico.
        
        Args:
            course_id: ID del curso
            
        Returns:
            Lista de bonos del curso
        """
        try:
            query = """
            SELECT 
                id,
                bonus_name,
                bonus_description,
                bonus_type,
                resource_url,
                value_usd,
                condition_type,
                condition_detail
            FROM course_bonuses 
            WHERE course_id = $1 AND is_active = true
            ORDER BY value_usd DESC
            """
            
            results = await self.db.fetch_all(query, course_id)
            
            if results:
                bonuses = [dict(result) for result in results]
                logger.info(f"✅ Encontrados {len(bonuses)} bonos para curso {course_id}")
                return bonuses
            else:
                logger.info(f"📋 No se encontraron bonos para curso {course_id}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo bonos del curso {course_id}: {e}")
            return []

    def format_bonuses_for_persuasion(self, bonuses: List[Dict]) -> str:
        """
        Formatea los bonos para mencionar en conversación de ventas (NO para enviar).
        
        Args:
            bonuses: Lista de bonos del curso
            
        Returns:
            Mensaje formateado mencionando los bonos disponibles
        """
        if not bonuses:
            return ""

        try:
            total_value = sum(float(bonus.get('value_usd', 0)) for bonus in bonuses)
            
            message = f"""🎁 **BONOS EXCLUSIVOS INCLUIDOS**

*¡Además del curso, recibes estos recursos de regalo!*

"""
            
            for bonus in bonuses:
                bonus_name = bonus.get('bonus_name', 'Bono especial')
                bonus_type = bonus.get('bonus_type', '').upper()
                value = float(bonus.get('value_usd', 0))
                condition = bonus.get('condition_detail', '')
                
                # Emoji según tipo de bono
                emoji = {
                    'TEMPLATE': '📋',
                    'MASTERCLASS': '🎓',
                    'GUIDE': '📖',
                    'VIDEO': '🎥',
                    'TOOL': '🛠️'
                }.get(bonus_type, '🎁')
                
                message += f"{emoji} **{bonus_name}** (Valor: ${value} USD)\n"
            
            message += f"""
💰 **Valor total de bonos:** ${total_value} USD

⏰ *Bonos disponibles solo para inscripciones en las {bonuses[0].get('condition_detail', 'próximas 24 horas')}*

🚀 **¡No dejes pasar esta oportunidad única!**"""

            logger.info(f"✅ Mensaje de bonos formateado: {len(bonuses)} bonos, valor total ${total_value}")
            return message
            
        except Exception as e:
            logger.error(f"❌ Error formateando bonos para persuasión: {e}")
            return "🎁 **Bonos exclusivos disponibles** - Contacta a un asesor para más detalles."

    def format_single_bonus_detail(self, bonus: Dict) -> str:
        """
        Formatea los detalles de un bono específico.
        
        Args:
            bonus: Diccionario con datos del bono
            
        Returns:
            Descripción detallada del bono
        """
        try:
            bonus_name = bonus.get('bonus_name', 'Bono especial')
            description = bonus.get('bonus_description', 'Recurso exclusivo')
            value = float(bonus.get('value_usd', 0))
            condition = bonus.get('condition_detail', 'tiempo limitado')
            
            message = f"""🎁 **{bonus_name}**

📄 **Qué incluye:** {description}

💰 **Valor:** ${value} USD
⏰ **Disponible:** Solo durante las {condition}

*Este bono se entrega automáticamente después de confirmar tu inscripción.*"""

            return message
            
        except Exception as e:
            logger.error(f"❌ Error formateando detalle de bono: {e}")
            return "🎁 Bono exclusivo disponible."

    async def get_formatted_bonuses_for_course(self, course_id: str) -> str:
        """
        Método de conveniencia que obtiene y formatea bonos de un curso.
        
        Args:
            course_id: ID del curso
            
        Returns:
            Mensaje formateado listo para enviar
        """
        bonuses = await self.get_course_bonuses(course_id)
        return self.format_bonuses_for_persuasion(bonuses)

    async def get_total_bonus_value(self, course_id: str) -> float:
        """
        Calcula el valor total de todos los bonos de un curso.
        
        Args:
            course_id: ID del curso
            
        Returns:
            Valor total en USD
        """
        try:
            bonuses = await self.get_course_bonuses(course_id)
            total = sum(float(bonus.get('value_usd', 0)) for bonus in bonuses)
            logger.info(f"💰 Valor total de bonos para curso {course_id}: ${total} USD")
            return total
        except Exception as e:
            logger.error(f"❌ Error calculando valor total de bonos: {e}")
            return 0.0 