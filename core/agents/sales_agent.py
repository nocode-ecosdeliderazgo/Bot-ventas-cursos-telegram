"""
Implementación de las funciones del agente de ventas.
"""

from typing import Dict, List, Optional, Union
from datetime import datetime, timezone
from decimal import Decimal
import json
from .services.database import DatabaseService

class AgenteSalesTools:
    def __init__(self, db: DatabaseService, telegram_api):
        self.db = db
        self.telegram = telegram_api

    async def mostrar_curso_destacado(self, user_id: str, course_id: str) -> None:
        """
        Muestra una presentación completa y atractiva de un curso específico.
        """
        # Obtener detalles del curso
        course = await self.db.get_course_details(course_id)
        if not course:
            return
        
        # Calcular descuento si existe
        precio_final = course['price_usd']
        if course['discount_percentage'] and course['discount_end_date'] > datetime.now(timezone.utc):
            precio_final = precio_final * (1 - course['discount_percentage'] / 100)

        # Preparar mensaje con formato atractivo
        mensaje = f"""🎓 *{course['name']}*

{course['short_description']}

📚 *Nivel:* {course['level']}
⏰ *Duración:* {course['total_duration']}
🗓️ *Horarios:* {course['schedule']}

💡 *Herramientas que aprenderás:*
{self._format_tools_list(course['tools_used'])}

💰 *Inversión:*
{'~~$' + str(course['original_price_usd']) + ' USD~~' if course['discount_percentage'] else ''}
*${precio_final} USD*
{f'🔥 {course["discount_percentage"]}% OFF - ¡Oferta termina en {self._time_until(course["discount_end_date"])}!' if course['discount_percentage'] else ''}

✨ *Bonos Exclusivos:*
{self._format_bonuses(course['active_bonuses'])}

👥 *¡Últimos cupos disponibles!*
Grupos reducidos: máximo {course['max_students']} estudiantes
"""
        # Enviar mensaje y thumbnail
        await self.telegram.send_photo(
            user_id,
            course['thumbnail_url'],
            caption=mensaje,
            parse_mode='Markdown'
        )

        # Registrar interacción
        await self.db.register_interaction(
            user_id, 
            course_id,
            "view",
            {"shown_price": precio_final}
        )

    async def enviar_preview_curso(self, user_id: str, course_id: str) -> None:
        """
        Envía un video preview del curso al usuario.
        """
        course = await self.db.get_course_details(course_id)
        if not course or not course['preview_url']:
            return

        mensaje = f"""🎥 *Preview del curso: {course['name']}*

Te comparto este video donde podrás ver:
- 👨‍🏫 Metodología de enseñanza
- 📚 Ejemplos de contenido
- 💡 Proyectos prácticos
- 🎯 Resultados esperados

¡Mira el video y pregúntame cualquier duda! 😊"""

        await self.telegram.send_video(
            user_id,
            course['preview_url'],
            caption=mensaje,
            parse_mode='Markdown'
        )

        await self.db.register_interaction(
            user_id,
            course_id,
            "preview_watch",
            {"video_url": course['preview_url']}
        )

    async def mostrar_syllabus_interactivo(self, user_id: str, course_id: str) -> None:
        """
        Presenta el syllabus de manera interactiva.
        """
        course = await self.db.get_course_details(course_id)
        if not course or not course['modules']:
            return

        mensaje = f"""📚 *Contenido del curso: {course['name']}*

{course['long_description']}

*Módulos del curso:*
"""
        for module in course['modules']:
            mensaje += f"""
📌 *Módulo {module['module_index']}: {module['name']}*
{module['description']}
⏱️ Duración: {module['duration']}
"""

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown',
            reply_markup=self._get_syllabus_buttons(course)
        )

        await self.db.register_interaction(
            user_id,
            course_id,
            "syllabus_view",
            {}
        )

    async def presentar_oferta_limitada(self, user_id: str, course_id: str) -> None:
        """
        Muestra una oferta especial con contador de tiempo.
        """
        course = await self.db.get_course_details(course_id)
        if not course or not course['discount_end_date']:
            return

        tiempo_restante = self._time_until(course['discount_end_date'])
        ahorro = course['original_price_usd'] - (course['price_usd'] * (1 - course['discount_percentage'] / 100))
        
        mensaje = f"""🔥 *¡OFERTA ESPECIAL!*

Por tiempo limitado, obtén el curso "{course['name']}" con un *{course['discount_percentage']}% DE DESCUENTO*

💰 Precio normal: ~~${course['original_price_usd']} USD~~
💎 Precio con descuento: *${course['price_usd'] * (1 - course['discount_percentage'] / 100)} USD*
✨ ¡Ahorras ${ahorro} USD!

⏰ Esta oferta termina en: *{tiempo_restante}*

🎁 *Además, incluye estos bonos GRATIS:*
{self._format_bonuses(course['active_bonuses'])}

¡No pierdas esta oportunidad única! 🚀"""

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown',
            reply_markup=self._get_purchase_buttons(course)
        )

        await self.db.register_interaction(
            user_id,
            course_id,
            "offer_shown",
            {"discount": course['discount_percentage']}
        )

    # ... Más implementaciones de funciones ...

    def _format_tools_list(self, tools: List[str]) -> str:
        """Formatea la lista de herramientas para mostrar."""
        return '\n'.join(f'• {tool}' for tool in tools)

    def _format_bonuses(self, bonuses: List[Dict]) -> str:
        """Formatea la lista de bonos activos."""
        if not bonuses:
            return "Sin bonos activos"
        
        bonus_text = ""
        for bonus in bonuses:
            remaining = bonus['max_claims'] - bonus['current_claims']
            bonus_text += f"""
🎁 *{bonus['name']}*
   • {bonus['value_proposition']}
   • Valor: ${bonus['original_value']} USD
   • ¡Solo quedan {remaining} cupos!"""
        return bonus_text

    def _time_until(self, end_date: datetime) -> str:
        """Calcula el tiempo restante hasta una fecha."""
        now = datetime.now(timezone.utc)
        diff = end_date - now
        
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def _get_syllabus_buttons(self, course: Dict) -> Dict:
        """Genera botones para el syllabus."""
        return {
            "inline_keyboard": [
                [{"text": "📥 Descargar Syllabus Completo", "url": course['syllabus_url']}],
                [{"text": "🎥 Ver Video Preview", "callback_data": f"preview_{course['id']}"}],
                [{"text": "💰 Ver Precios y Descuentos", "callback_data": f"pricing_{course['id']}"}]
            ]
        }

    def _get_purchase_buttons(self, course: Dict) -> Dict:
        """Genera botones para la compra."""
        return {
            "inline_keyboard": [
                [{"text": "💳 Comprar Ahora", "url": course['purchase_link']}],
                [{"text": "🗣️ Hablar con un Asesor", "url": course['demo_request_link']}],
                [{"text": "📚 Ver Contenido Completo", "callback_data": f"syllabus_{course['id']}"}]
            ]
        } 