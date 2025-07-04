"""
Manejador de flujo para usuarios provenientes de anuncios.
Detecta hashtags y procesa la información inicial del lead.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import re
from ..services import DatabaseService
from ..utils.message_parser import extract_hashtags, get_course_from_hashtag
from ..utils.lead_scorer import calculate_initial_score
from ..sales_agent import AgenteSalesTools

class AdsFlowHandler:
    def __init__(self, db_service: DatabaseService, agent_tools: AgenteSalesTools):
        self.db = db_service
        self.agent = agent_tools

    async def handle_ad_message(self, message: Dict, user_data: Dict) -> Tuple[str, List[Dict]]:
        """
        Maneja el mensaje inicial de un usuario proveniente de un anuncio.
        Retorna la respuesta y los botones/acciones siguientes.
        """
        # Extraer hashtags del mensaje
        hashtags = extract_hashtags(message['text'])
        course_id = await get_course_from_hashtag(hashtags, self.db)
        ad_source = self._get_ad_source(hashtags)

        # Crear o actualizar lead
        lead_data = {
            'telegram_id': str(user_data['id']),
            'name': user_data.get('first_name', '') + ' ' + user_data.get('last_name', ''),
            'source': ad_source,
            'selected_course': course_id,
            'stage': 'nuevo',
            'last_interaction': datetime.now(timezone.utc),
            'interest_score': await calculate_initial_score(message, hashtags)
        }
        
        lead_id = await self._create_or_update_lead(lead_data)
        
        # Registrar la interacción inicial
        await self.agent._registrar_interaccion(
            lead_id,
            course_id,
            "inquiry",
            {"source": ad_source, "initial_message": message['text']}
        )

        # Preparar respuesta personalizada
        response = await self._generate_initial_response(lead_id, course_id)
        next_actions = await self._prepare_next_actions(course_id)

        return response, next_actions

    async def _create_or_update_lead(self, lead_data: Dict) -> str:
        """
        Crea o actualiza un lead en la base de datos.
        Retorna el ID del lead.
        """
        query = """
        INSERT INTO public.user_leads (
            telegram_id, name, source, selected_course, 
            stage, last_interaction, interest_score
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7
        )
        ON CONFLICT (telegram_id) 
        DO UPDATE SET
            source = EXCLUDED.source,
            selected_course = EXCLUDED.selected_course,
            last_interaction = EXCLUDED.last_interaction,
            interest_score = EXCLUDED.interest_score
        RETURNING id;
        """
        
        result = await self.db.fetch_one(
            query,
            lead_data['telegram_id'],
            lead_data['name'],
            lead_data['source'],
            lead_data['selected_course'],
            lead_data['stage'],
            lead_data['last_interaction'],
            lead_data['interest_score']
        )
        
        return result['id']

    def _get_ad_source(self, hashtags: List[str]) -> str:
        """
        Extrae la fuente del anuncio de los hashtags.
        Ejemplo: #ADSIM_01 -> "instagram_marketing_01"
        """
        for tag in hashtags:
            if tag.startswith('ADS'):
                parts = tag.split('_')
                if len(parts) >= 2:
                    platform = {
                        'IM': 'instagram_marketing',
                        'FB': 'facebook_ads',
                        'GO': 'google_ads',
                        'TW': 'twitter_ads'
                    }.get(parts[0][3:], 'other')
                    campaign = parts[1]
                    return f"{platform}_{campaign}"
        return "organic"

    async def _generate_initial_response(self, lead_id: str, course_id: str) -> str:
        """
        Genera la respuesta inicial personalizada basada en el curso seleccionado.
        """
        course = await self.db.fetch_one(
            "SELECT name, short_description FROM courses WHERE id = $1",
            course_id
        )
        
        return f"""¡Hola! 👋 Me alegro que te interese nuestro curso "{course['name']}"

{course['short_description']}

¿Te gustaría conocer más detalles sobre:
- 📚 Contenido del curso
- ⏰ Duración y horarios
- 💰 Inversión y métodos de pago
- 🎁 Bonos especiales disponibles

¡Puedes preguntarme lo que necesites! 😊"""

    async def _prepare_next_actions(self, course_id: str) -> List[Dict]:
        """
        Prepara los botones/acciones siguientes para el usuario.
        """
        return [
            {
                "text": "📚 Ver contenido del curso",
                "callback_data": f"show_syllabus_{course_id}"
            },
            {
                "text": "🎥 Ver video preview",
                "callback_data": f"show_preview_{course_id}"
            },
            {
                "text": "💰 Ver precios y descuentos",
                "callback_data": f"show_pricing_{course_id}"
            },
            {
                "text": "🗣️ Agendar llamada informativa",
                "callback_data": f"schedule_call_{course_id}"
            }
        ] 