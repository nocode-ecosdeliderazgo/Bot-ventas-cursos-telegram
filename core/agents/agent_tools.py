"""
Herramientas del agente de ventas para interactuar con usuarios y gestionar recursos.
Consolidación de todas las funciones necesarias para maximizar conversiones.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Union
from decimal import Decimal
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

class AgentTools:
    def __init__(self, db_service, telegram_api):
        self.db = db_service
        self.telegram = telegram_api
        
    # ========== Funciones de Presentación de Cursos ==========
    
    async def mostrar_curso_destacado(self, user_id: str, course_id: str) -> None:
        """
        Muestra una presentación completa y atractiva de un curso específico.
        Incluye thumbnail, descripción corta, precio con descuento y valor total de bonos.
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
        await self._registrar_interaccion(
            user_id, 
            course_id,
            "view",
            {"shown_price": precio_final}
        )

    async def enviar_preview_curso(self, user_id: str, course_id: str) -> None:
        """
        Envía un video preview del curso al usuario.
        Incluye CTA (Call to Action) personalizado basado en el perfil del usuario.
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

        await self._registrar_interaccion(
            user_id,
            course_id,
            "preview_watch",
            {"video_url": course['preview_url']}
        )

    async def mostrar_syllabus_interactivo(self, user_id: str, course_id: str) -> None:
        """
        Presenta el syllabus de manera interactiva con botones para expandir módulos.
        Incluye duración, herramientas a aprender y resultados esperados.
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

        await self._registrar_interaccion(
            user_id,
            course_id,
            "syllabus_view",
            {}
        )

    # ========== Funciones de Persuasión y Urgencia ==========

    async def presentar_oferta_limitada(self, user_id: str, course_id: str) -> None:
        """
        Muestra una oferta especial con contador de tiempo y beneficios exclusivos.
        Enfatiza el ahorro total (descuento + valor de bonos).
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

        await self._registrar_interaccion(
            user_id,
            course_id,
            "offer_shown",
            {"discount": course['discount_percentage']}
        )

    async def mostrar_bonos_exclusivos(self, user_id: str, course_id: str) -> None:
        """
        Presenta los bonos disponibles para el curso con su valor monetario.
        Incluye contador de cupos disponibles para crear urgencia.
        """
        bonuses = await self.db.fetch_all(
            """
            SELECT * FROM limited_time_bonuses 
            WHERE course_id = $1 AND active = true AND expires_at > NOW()
            ORDER BY original_value DESC
            """,
            course_id
        )

        if not bonuses:
            await self.telegram.send_message(
                user_id,
                "🎁 *Bonos especiales próximamente disponibles*\n\n¡Mantente atento para no perderte ofertas exclusivas!"
            )
            return

        mensaje = "🎁 *¡BONOS EXCLUSIVOS DISPONIBLES!*\n\n"
        total_value = 0

        for bonus in bonuses:
            remaining = bonus['max_claims'] - bonus['current_claims']
            total_value += bonus['original_value']
            
            mensaje += f"""✨ *{bonus['name']}*
📝 {bonus['description']}
💰 Valor: ${bonus['original_value']} USD
🏃‍♂️ Solo quedan {remaining} de {bonus['max_claims']} cupos
⏰ Expira: {self._time_until(bonus['expires_at'])}

"""

        mensaje += f"""💎 *Valor total de bonos: ${total_value} USD*

¡Estos bonos están incluidos GRATIS con tu inscripción!
¡No esperes más, los cupos se agotan rápido! 🔥"""

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown'
        )

        await self._registrar_interaccion(
            user_id,
            course_id,
            "bonuses_viewed",
            {"total_bonus_value": total_value}
        )

    async def mostrar_testimonios_relevantes(self, user_id: str, course_id: str) -> None:
        """
        Muestra testimonios filtrados según el perfil del usuario.
        Incluye rating del curso y número de estudiantes satisfechos.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        # Testimonios predefinidos por curso (en una implementación real vendrían de la BD)
        testimonios = {
            'principiante': [
                "\"¡Increíble! Nunca pensé que podría aprender IA tan rápido. El instructor explica todo súper claro.\" - María González, Marketing",
                "\"De cero a crear mis propios asistentes virtuales en 4 semanas. ¡Recomendadísimo!\" - Carlos Ruiz, Emprendedor"
            ],
            'intermedio': [
                "\"Me ayudó a automatizar procesos en mi empresa que nos ahorran 20 horas semanales.\" - Ana Martínez, Gerente de Operaciones",
                "\"La metodología práctica es excelente. Aplicé todo inmediatamente en mi trabajo.\" - Diego Torres, Analista"
            ],
            'avanzado': [
                "\"Llevó mis conocimientos al siguiente nivel. Ahora lidero proyectos de IA en mi empresa.\" - Roberto Silva, CTO",
                "\"La calidad del contenido supera cualquier curso que haya tomado antes.\" - Laura Vega, Data Scientist"
            ]
        }

        # Seleccionar testimonios basados en el nivel del curso
        nivel = course['level'].lower()
        testimonios_curso = testimonios.get('intermedio', testimonios['principiante'])  # Default

        mensaje = f"""⭐ *Testimonios del curso: {course['name']}*

🌟 *Calificación: {course['rating']}/5 estrellas*
👥 *Basado en {course['reviews_count']} reseñas verificadas*

💬 *Lo que dicen nuestros estudiantes:*

{testimonios_curso[0]}

{testimonios_curso[1]}

📊 *Estadísticas de satisfacción:*
• 98% recomendaría este curso
• 95% consiguió aplicar lo aprendido inmediatamente
• 92% reportó aumento en productividad

¡Únete a nuestros estudiantes exitosos! 🚀"""

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown'
        )

        await self._registrar_interaccion(
            user_id,
            course_id,
            "testimonials_viewed",
            {}
        )

    # ========== Funciones de Seguimiento y Engagement ==========

    async def agendar_demo_personalizada(self, user_id: str, course_id: str) -> None:
        """
        Permite al usuario agendar una demo/sesión informativa personalizada.
        Registra el interés y programa seguimiento.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        mensaje = f"""📞 *¡Excelente elección!*

Me encanta que quieras conocer más sobre "{course['name']}" a través de una sesión personalizada.

🗓️ *¿Cómo funciona?*
• Sesión de 30 minutos vía Zoom
• Revisamos el contenido específico que te interesa
• Resolvemos todas tus dudas
• Te mostramos ejemplos prácticos en vivo

⏰ *Horarios disponibles:*
• Lunes a Viernes: 9:00 AM - 6:00 PM
• Sábados: 9:00 AM - 2:00 PM

Para agendar tu sesión, haz clic en el botón de abajo o escríbeme tu horario preferido."""

        buttons = {
            "inline_keyboard": [
                [{"text": "📅 Agendar Ahora", "url": course['demo_request_link']}],
                [{"text": "💬 Escribir Horario Preferido", "callback_data": f"schedule_manual_{course_id}"}],
                [{"text": "📚 Ver Más Info del Curso", "callback_data": f"show_syllabus_{course_id}"}]
            ]
        }

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown',
            reply_markup=buttons
        )

        await self._registrar_interaccion(
            user_id,
            course_id,
            "demo_request",
            {}
        )

        # Actualizar lead como altamente interesado
        await self.db.execute(
            "UPDATE user_leads SET stage = 'demo_solicitada', interest_score = LEAST(interest_score + 20, 100) WHERE telegram_id = $1",
            str(user_id)
        )

    async def enviar_recursos_gratuitos(self, user_id: str, course_id: str) -> None:
        """
        Envía recursos de valor relacionados al curso para demostrar calidad.
        Incluye guías, templates o herramientas básicas.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        mensaje = f"""🎁 *¡Regalo especial para ti!*

Como muestra de la calidad de nuestro curso "{course['name']}", te comparto estos recursos gratuitos:

📚 *Recursos incluidos:*
• Guía PDF: "Primeros pasos en IA"
• Templates listos para usar
• Lista de herramientas recomendadas
• Checklist de mejores prácticas

💡 *Esto es solo una pequeña muestra* de todo el contenido premium que incluye el curso completo.

¿Te gustaría ver qué más incluye el curso? 👆"""

        buttons = {
            "inline_keyboard": [
                [{"text": "📥 Descargar Recursos", "url": course['resources_url']}],
                [{"text": "📚 Ver Contenido Completo", "callback_data": f"show_syllabus_{course_id}"}],
                [{"text": "💰 Ver Oferta Especial", "callback_data": f"show_pricing_{course_id}"}]
            ]
        }

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown',
            reply_markup=buttons
        )

        await self._registrar_interaccion(
            user_id,
            course_id,
            "free_resources_sent",
            {}
        )

    async def mostrar_comparativa_precios(self, user_id: str, course_id: str) -> None:
        """
        Presenta una comparativa del valor total vs inversión requerida.
        Destaca el ROI esperado y beneficios a largo plazo.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        # Calcular valores
        precio_actual = course['price_usd']
        if course['discount_percentage']:
            precio_actual = precio_actual * (1 - course['discount_percentage'] / 100)

        # Valor de bonos
        bonus_value = sum(bonus['original_value'] for bonus in (course['active_bonuses'] or []))

        mensaje = f"""💰 *Análisis de Inversión: {course['name']}*

🎯 *Tu inversión:* ${precio_actual} USD

🎁 *Lo que recibes:*
• Curso completo: ${course['original_price_usd']} USD
• Bonos exclusivos: ${bonus_value} USD
• Soporte personalizado: $200 USD
• Acceso de por vida: $300 USD
• Actualizaciones futuras: $150 USD

📊 *Valor total: ${course['original_price_usd'] + bonus_value + 650} USD*

✨ *Tu ahorro: ${(course['original_price_usd'] + bonus_value + 650) - precio_actual} USD*

💼 *ROI Esperado:*
• Aumento de productividad: 40-60%
• Ahorro en tiempo: 10-15 horas/semana
• Valor de mercado de habilidades: +$5,000/año

¿Cuándo más vas a encontrar una oportunidad así? 🚀"""

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown',
            reply_markup=self._get_purchase_buttons(course)
        )

        await self._registrar_interaccion(
            user_id,
            course_id,
            "price_comparison_shown",
            {"total_value": course['original_price_usd'] + bonus_value + 650}
        )

    # ========== Funciones de Cierre de Venta ==========

    async def generar_link_pago_personalizado(self, user_id: str, course_id: str) -> str:
        """
        Crea un link de pago personalizado con descuentos y bonos aplicados.
        Incluye seguimiento de la fuente de conversión.
        """
        course = await self.db.get_course_details(course_id)
        lead = await self.db.fetch_one(
            "SELECT * FROM user_leads WHERE telegram_id = $1",
            str(user_id)
        )

        if not course or not lead:
            return course['purchase_link'] if course else ""

        # Crear parámetros de tracking
        params = {
            'lead_id': lead['id'],
            'source': lead['source'],
            'course_id': course_id,
            'discount': course['discount_percentage'] or 0,
            'timestamp': int(datetime.now().timestamp())
        }

        # En una implementación real, esto generaría un link único
        tracking_params = "&".join([f"{k}={v}" for k, v in params.items()])
        personalized_link = f"{course['purchase_link']}?{tracking_params}"

        await self._registrar_interaccion(
            user_id,
            course_id,
            "payment_link_generated",
            {"link": personalized_link}
        )

        return personalized_link

    async def mostrar_garantia_satisfaccion(self, user_id: str) -> None:
        """
        Presenta la política de garantía y testimonios de satisfacción.
        Reduce la fricción para la decisión de compra.
        """
        mensaje = """🛡️ *GARANTÍA DE SATISFACCIÓN TOTAL*

✅ *30 días de garantía completa*
Si no estás 100% satisfecho con el curso, te devolvemos tu dinero completo.

🔒 *¿Por qué ofrecemos esta garantía?*
• Confiamos en la calidad de nuestro contenido
• 98% de nuestros estudiantes están satisfechos
• Queremos que tomes la decisión sin riesgo

📞 *Proceso súper simple:*
1. Envíanos un mensaje antes de los 30 días
2. Nos cuentas por qué no cumplió tus expectativas
3. Procesamos tu reembolso en 24-48 horas

💪 *¡Sin preguntas difíciles, sin letra pequeña!*

¿Qué estás esperando? ¡Tu satisfacción está garantizada! 🚀"""

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown'
        )

    async def ofrecer_plan_pagos(self, user_id: str, course_id: str) -> None:
        """
        Presenta opciones de pago flexibles según el presupuesto del usuario.
        Incluye comparativa de beneficios por opción.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        precio_base = course['price_usd']
        if course['discount_percentage']:
            precio_base = precio_base * (1 - course['discount_percentage'] / 100)

        mensaje = f"""💳 *Opciones de Pago Flexibles*

Para el curso "{course['name']}"

🏆 *OPCIÓN 1: Pago Único (Recomendado)*
• Precio: ${precio_base} USD
• ✅ Acceso inmediato completo
• ✅ Todos los bonos incluidos
• ✅ 10% descuento adicional
• ✅ Certificado premium

💼 *OPCIÓN 2: Plan 2 Pagos*
• 2 pagos de ${(precio_base * 1.1) / 2:.0f} USD
• ✅ Acceso inmediato al 70% del contenido
• ✅ Bonos incluidos
• ⚠️ Sin descuento adicional

📈 *OPCIÓN 3: Plan 3 Pagos*
• 3 pagos de ${(precio_base * 1.15) / 3:.0f} USD
• ✅ Acceso gradual al contenido
• ✅ Bonos incluidos después del 2do pago
• ⚠️ Recargo del 15%

¿Cuál opción se adapta mejor a tu presupuesto? 🤔"""

        buttons = {
            "inline_keyboard": [
                [{"text": "🏆 Pago Único", "callback_data": f"payment_full_{course_id}"}],
                [{"text": "💼 2 Pagos", "callback_data": f"payment_2x_{course_id}"}],
                [{"text": "📈 3 Pagos", "callback_data": f"payment_3x_{course_id}"}],
                [{"text": "💬 Necesito más info", "callback_data": f"payment_info_{course_id}"}]
            ]
        }

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown',
            reply_markup=buttons
        )

        await self._registrar_interaccion(
            user_id,
            course_id,
            "payment_options_shown",
            {}
        )

    # ========== Funciones de Análisis y Seguimiento ==========

    async def actualizar_perfil_lead(
        self, 
        user_id: str, 
        interaction_data: Dict
    ) -> None:
        """
        Actualiza el perfil del lead con nueva información recopilada.
        Ajusta la estrategia de venta según el perfil.
        """
        # Extraer información relevante del interaction_data
        updates = {
            'last_interaction': datetime.now(timezone.utc),
            'interaction_count': 'interaction_count + 1'
        }

        # Construir query de actualización
        set_clauses = []
        values = []
        param_count = 1

        for key, value in updates.items():
            if key == 'interaction_count':
                set_clauses.append(f"{key} = {value}")
            else:
                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1

        values.append(str(user_id))  # Para el WHERE

        query = f"""
        UPDATE user_leads 
        SET {', '.join(set_clauses)}, updated_at = NOW()
        WHERE telegram_id = ${param_count}
        """

        await self.db.execute(query, *values)

    async def calcular_interes_compra(self, user_id: str) -> int:
        """
        Calcula el nivel de interés del usuario basado en sus interacciones.
        Retorna un score de 0 a 100.
        """
        # Obtener interacciones del usuario
        interactions = await self.db.fetch_all(
            """
            SELECT ci.interaction_type, ci.metadata, ci.created_at,
                   ul.interest_score as base_score
            FROM course_interactions ci
            JOIN user_leads ul ON ul.id = ci.lead_id
            WHERE ul.telegram_id = $1
            ORDER BY ci.created_at DESC
            LIMIT 20
            """,
            str(user_id)
        )

        if not interactions:
            return 50  # Score base

        base_score = interactions[0]['base_score'] or 50
        
        # Calcular incrementos basados en interacciones
        score_increments = {
            'view': 5,
            'preview_watch': 10,
            'syllabus_view': 8,
            'demo_request': 20,
            'offer_shown': 5,
            'bonuses_viewed': 7,
            'testimonials_viewed': 6,
            'payment_link_generated': 25,
            'payment_options_shown': 15
        }

        # Sumar incrementos con peso por recencia
        total_increment = 0
        for i, interaction in enumerate(interactions):
            interaction_type = interaction['interaction_type']
            increment = score_increments.get(interaction_type, 0)
            
            # Aplicar peso por recencia (interacciones más recientes valen más)
            recency_weight = 1 - (i * 0.05)  # Máximo 95% de descuento
            total_increment += increment * max(recency_weight, 0.3)

        final_score = min(base_score + total_increment, 100)
        
        # Actualizar score en la base de datos
        await self.db.execute(
            "UPDATE user_leads SET interest_score = $1 WHERE telegram_id = $2",
            int(final_score),
            str(user_id)
        )

        return int(final_score)

    async def programar_seguimiento(
        self, 
        user_id: str, 
        interaction_type: str
    ) -> None:
        """
        Programa el siguiente contacto basado en el tipo de interacción.
        Personaliza el mensaje según el perfil y etapa del funnel.
        """
        # Definir tiempos de seguimiento basados en el tipo de interacción
        followup_schedule = {
            'view': 24,  # 24 horas
            'preview_watch': 12,  # 12 horas
            'demo_request': 2,  # 2 horas
            'offer_shown': 6,  # 6 horas
            'payment_options_shown': 1  # 1 hora
        }

        hours_delay = followup_schedule.get(interaction_type, 24)
        followup_time = datetime.now(timezone.utc) + timedelta(hours=hours_delay)

        # Actualizar el lead con el próximo seguimiento programado
        await self.db.execute(
            """
            UPDATE user_leads 
            SET next_followup = $1, updated_at = NOW()
            WHERE telegram_id = $2
            """,
            followup_time,
            str(user_id)
        )

    # ========== Funciones Auxiliares Privadas ==========

    async def _registrar_interaccion(
        self, 
        user_id: str, 
        course_id: str, 
        interaction_type: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Registra cada interacción del usuario con los cursos.
        Actualiza métricas de engagement y seguimiento.
        """
        # Obtener lead_id
        lead = await self.db.fetch_one(
            "SELECT id FROM user_leads WHERE telegram_id = $1",
            str(user_id)
        )
        
        if not lead:
            return

        await self.db.register_interaction(
            lead['id'],
            course_id,
            interaction_type,
            metadata or {}
        )

        # Actualizar perfil del lead
        await self.actualizar_perfil_lead(user_id, {
            'interaction_type': interaction_type,
            'metadata': metadata
        })

        # Programar seguimiento
        await self.programar_seguimiento(user_id, interaction_type)

    async def _verificar_elegibilidad_bono(
        self, 
        user_id: str, 
        bonus_id: str
    ) -> bool:
        """
        Verifica si el usuario es elegible para un bono específico.
        Considera límites de tiempo y cupos disponibles.
        """
        # Verificar si el bono existe y está activo
        bonus = await self.db.fetch_one(
            """
            SELECT * FROM limited_time_bonuses 
            WHERE id = $1 AND active = true AND expires_at > NOW()
            """,
            bonus_id
        )

        if not bonus:
            return False

        # Verificar si hay cupos disponibles
        if bonus['current_claims'] >= bonus['max_claims']:
            return False

        # Verificar si el usuario ya reclamó este bono
        existing_claim = await self.db.fetch_one(
            """
            SELECT id FROM bonus_claims 
            WHERE bonus_id = $1 AND user_lead_id = (
                SELECT id FROM user_leads WHERE telegram_id = $2
            )
            """,
            bonus_id,
            str(user_id)
        )

        return existing_claim is None

    async def _generar_mensaje_personalizado(
        self, 
        user_id: str, 
        template_key: str, 
        **kwargs
    ) -> str:
        """
        Genera mensajes personalizados según el contexto y perfil del usuario.
        Utiliza templates predefinidos con variables dinámicas.
        """
        # Obtener perfil del usuario
        lead = await self.db.fetch_one(
            "SELECT * FROM user_leads WHERE telegram_id = $1",
            str(user_id)
        )

        if not lead:
            return "¡Hola! ¿En qué puedo ayudarte hoy?"

        # Templates de mensajes
        templates = {
            'welcome': f"¡Hola {lead['name']}! 👋 Me alegra verte por aquí.",
            'followup': f"Hola {lead['name']}, ¿has tenido oportunidad de revisar la información que te compartí?",
            'urgent': f"{lead['name']}, no quisiera que te pierdas esta oportunidad especial...",
            'support': f"¡Hola {lead['name']}! Estoy aquí para resolver cualquier duda que tengas."
        }

        template = templates.get(template_key, templates['welcome'])
        
        # Aplicar variables adicionales
        for key, value in kwargs.items():
            template = template.replace(f"{{{key}}}", str(value))

        return template

    # ========== Funciones de Formato ==========

    def _format_tools_list(self, tools: List[str]) -> str:
        """Formatea la lista de herramientas para mostrar."""
        if not tools:
            return "• Herramientas básicas incluidas"
        return '\n'.join(f'• {tool}' for tool in tools)

    def _format_bonuses(self, bonuses: List[Dict]) -> str:
        """Formatea la lista de bonos activos."""
        if not bonuses:
            return "🎁 Bonos especiales próximamente disponibles"
        
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
        
        if diff.total_seconds() <= 0:
            return "¡Expirado!"
        
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def _get_syllabus_buttons(self, course: Dict) -> InlineKeyboardMarkup:
        """Genera botones para el syllabus."""
        buttons = []
        
        if course.get('syllabus_url'):
            buttons.append([InlineKeyboardButton("📥 Descargar Syllabus Completo", url=course['syllabus_url'])])
        
        buttons.extend([
            [InlineKeyboardButton("🎥 Ver Video Preview", callback_data=f"show_preview_{course['id']}")],
            [InlineKeyboardButton("💰 Ver Precios y Descuentos", callback_data=f"show_pricing_{course['id']}")]
        ])
        
        return InlineKeyboardMarkup(buttons)

    def _get_purchase_buttons(self, course: Dict) -> InlineKeyboardMarkup:
        """Genera botones para la compra."""
        buttons = []
        
        if course.get('purchase_link'):
            buttons.append([InlineKeyboardButton("💳 Comprar Ahora", url=course['purchase_link'])])
        
        if course.get('demo_request_link'):
            buttons.append([InlineKeyboardButton("🗣️ Hablar con un Asesor", url=course['demo_request_link'])])
        
        buttons.append([InlineKeyboardButton("📚 Ver Contenido Completo", callback_data=f"show_syllabus_{course['id']}")])
        
        return InlineKeyboardMarkup(buttons)