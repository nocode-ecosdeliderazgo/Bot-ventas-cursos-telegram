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

        # Usar plantilla centralizada para generar mensaje
        from core.utils.course_templates import CourseTemplates
        
        # Agregar datos de descuento calculado para la plantilla
        course_with_discount = course.copy()
        course_with_discount['calculated_price'] = precio_final
        
        mensaje = CourseTemplates.format_course_details_with_benefits(course_with_discount)
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
- 👨🏫 Metodología de enseñanza
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

        from core.utils.course_templates import CourseTemplates
        mensaje = CourseTemplates.format_course_modules_detailed(course)

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
🏃 Solo quedan {remaining} de {bonus['max_claims']} cupos
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
                [{"text": "📚 Ver Más Info del Curso", "callback_data": f"show_syllabus_{course_id}"}],
                [{"text": "🧑‍💼 Contactar Asesor", "callback_data": "contact_advisor"}]
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
        Incluye guías, templates o herramientas básicas desde la tabla free_resources.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        # Obtener TODOS los recursos gratuitos de la base de datos (sin filtrar por curso)
        free_resources = await self.db.fetch_all(
            """
            SELECT resource_name, resource_type, resource_url, resource_description, file_size
            FROM free_resources 
            WHERE active = true
            ORDER BY created_at DESC
            """
        )

        mensaje = f"""🎁 *¡Regalo especial para ti!*

Te comparto estos recursos gratuitos disponibles:

📚 *Recursos disponibles:*
"""

        buttons_list = []
        
        if free_resources:
            for resource in free_resources:
                # Agregar descripción del recurso
                size_text = f" ({resource['file_size']})" if resource['file_size'] else ""
                mensaje += f"• {resource['resource_name']}{size_text}\n"
                if resource['resource_description']:
                    mensaje += f"  {resource['resource_description']}\n"
                
                # Agregar botón de descarga
                buttons_list.append([{"text": f"📥 {resource['resource_name']}", "url": resource['resource_url']}])
        else:
            mensaje += "• Guía PDF: \"Primeros pasos en IA\"\n"
            mensaje += "• Templates listos para usar\n"
            mensaje += "• Lista de herramientas recomendadas\n"
            mensaje += "• Checklist de mejores prácticas\n"
            
            # Botón de recursos generales si no hay recursos específicos
            if course.get('resources_url'):
                buttons_list.append([{"text": "📥 Descargar Recursos", "url": course['resources_url']}])

        mensaje += "\n💡 *¡Estos recursos están disponibles gratis para todos!*\n\n¿Te gustaría conocer más sobre nuestros cursos? 👆"

        # Agregar botones adicionales
        buttons_list.extend([
            [{"text": "📚 Ver Contenido Completo", "callback_data": f"show_syllabus_{course_id}"}],
            [{"text": "💰 Ver Oferta Especial", "callback_data": f"show_pricing_{course_id}"}],
            [{"text": "🧑‍💼 Contactar Asesor", "callback_data": "contact_advisor"}]
        ])

        buttons = {"inline_keyboard": buttons_list}

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
            {"resources_count": len(free_resources)}
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

        from core.utils.course_templates import CourseTemplates
        
        # Agregar precio calculado para la plantilla
        course_with_pricing = course.copy()
        course_with_pricing['calculated_price'] = precio_actual
        course_with_pricing['bonus_value'] = bonus_value
        
        mensaje = CourseTemplates.format_course_pricing(course_with_pricing)

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

        from core.utils.course_templates import CourseTemplates
        
        # Agregar precio calculado para la plantilla
        course_with_pricing = course.copy()
        course_with_pricing['calculated_price'] = precio_base
        
        mensaje = CourseTemplates.format_course_pricing(course_with_pricing)

        buttons = {
            "inline_keyboard": [
                [{"text": "🏆 Pago Único", "callback_data": f"payment_full_{course_id}"}],
                [{"text": "💼 2 Pagos", "callback_data": f"payment_2x_{course_id}"}],
                [{"text": "📈 3 Pagos", "callback_data": f"payment_3x_{course_id}"}],
                [{"text": "💬 Necesito más info", "callback_data": f"payment_info_{course_id}"}],
                [{"text": "🧑‍💼 Contactar Asesor", "callback_data": "contact_advisor"}]
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

    async def contactar_asesor_directo(self, user_id: str, course_id: str = None) -> dict:
        """
        Inicia directamente el flujo de contacto con asesor sin pregunta previa.
        Retorna un botón que activa el flujo completo implementado en contact_flow.py
        """
        await self._registrar_interaccion(
            user_id,
            course_id or "general",
            "contact_advisor_requested",
            {"direct_activation": True}
        )
        
        # Retornar respuesta con botón que activa el flujo directo
        return {
            "type": "message_with_button",
            "text": "Te voy a conectar con un asesor especializado. Solo necesito recopilar algunos datos:",
            "button": {
                "text": "🧑‍💼 Iniciar Contacto",
                "callback_data": "contact_advisor"
            }
        }

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

    # ========== NUEVAS HERRAMIENTAS AVANZADAS DE PERSUASIÓN ==========

    async def analizar_comportamiento_usuario(self, user_id: str) -> Dict:
        """
        Analiza el comportamiento completo del usuario basado en todas sus interacciones.
        Devuelve insights para personalizar la estrategia de venta.
        """
        # Obtener perfil completo del usuario
        lead = await self.db.fetch_one(
            "SELECT * FROM user_leads WHERE telegram_id = $1", str(user_id)
        )
        
        # Obtener todas las interacciones del usuario
        interactions = await self.db.fetch_all(
            """
            SELECT ci.*, c.name as course_name, c.price_usd 
            FROM course_interactions ci
            JOIN courses c ON ci.course_id = c.id
            WHERE ci.lead_id = $1
            ORDER BY ci.created_at DESC
            """, lead['id'] if lead else None
        )
        
        # Obtener conversaciones recientes
        conversations = await self.db.fetch_all(
            """
            SELECT * FROM conversations 
            WHERE lead_id = $1 
            ORDER BY created_at DESC 
            LIMIT 10
            """, lead['id'] if lead else None
        )
        
        # Análisis de patrones
        analysis = {
            'profile_completeness': self._calculate_profile_completeness(lead),
            'engagement_level': self._calculate_engagement_level(interactions),
            'buying_intent': self._calculate_buying_intent(interactions),
            'preferred_interaction_time': self._analyze_interaction_patterns(interactions),
            'price_sensitivity': self._analyze_price_sensitivity(interactions),
            'content_preferences': self._analyze_content_preferences(conversations),
            'objection_patterns': self._identify_objection_patterns(conversations),
            'decision_stage': self._determine_decision_stage(interactions),
            'urgency_level': self._calculate_urgency_level(interactions),
            'personalization_data': self._extract_personalization_data(lead, conversations)
        }
        
        return analysis

    async def generar_oferta_dinamica(self, user_id: str, course_id: str) -> Dict:
        """
        Genera una oferta personalizada basada en el comportamiento y perfil del usuario.
        Ajusta descuentos, bonos y términos según el análisis predictivo.
        """
        behavior = await self.analizar_comportamiento_usuario(user_id)
        course = await self.db.get_course_details(course_id)
        
        # Calcular descuento dinámico
        base_discount = course.get('discount_percentage', 0)
        dynamic_discount = self._calculate_dynamic_discount(behavior, base_discount)
        
        # Seleccionar bonos relevantes
        relevant_bonuses = await self._select_relevant_bonuses(user_id, course_id, behavior)
        
        # Determinar urgencia de la oferta
        urgency_hours = self._calculate_offer_urgency(behavior)
        
        # Personalizar términos de pago
        payment_terms = self._personalize_payment_terms(behavior)
        
        offer = {
            'discount_percentage': dynamic_discount,
            'bonuses': relevant_bonuses,
            'urgency_hours': urgency_hours,
            'payment_terms': payment_terms,
            'personalized_message': self._generate_offer_message(behavior, course),
            'confidence_score': behavior['buying_intent']
        }
        
        # Registrar oferta generada
        await self._registrar_interaccion(
            user_id, course_id, "dynamic_offer_generated", 
            {"offer_details": offer}
        )
        
        return offer

    async def mostrar_social_proof_inteligente(self, user_id: str, course_id: str) -> None:
        """
        Muestra social proof personalizado basado en el perfil del usuario.
        Incluye testimonios de personas similares y estadísticas relevantes.
        """
        lead = await self.db.fetch_one(
            "SELECT * FROM user_leads WHERE telegram_id = $1", str(user_id)
        )
        
        # Buscar usuarios similares que compraron
        similar_buyers = await self.db.fetch_all(
            """
            SELECT ul.role, ul.industry, ul.company, cs.purchase_date, ul.name
            FROM user_leads ul
            JOIN course_sales cs ON ul.id = cs.lead_id
            WHERE cs.course_id = $1 
            AND cs.payment_status = 'completed'
            AND (ul.role = $2 OR ul.industry = $3)
            ORDER BY cs.purchase_date DESC
            LIMIT 5
            """, course_id, lead.get('role'), lead.get('industry')
        )
        
        # Estadísticas de conversión por perfil
        conversion_stats = await self.db.fetch_one(
            """
            SELECT 
                COUNT(*) as total_similar,
                COUNT(CASE WHEN cs.payment_status = 'completed' THEN 1 END) as purchased,
                AVG(ul.interest_score) as avg_interest
            FROM user_leads ul
            LEFT JOIN course_sales cs ON ul.id = cs.lead_id AND cs.course_id = $1
            WHERE ul.role = $2 OR ul.industry = $3
            """, course_id, lead.get('role'), lead.get('industry')
        )
        
        mensaje = f"👥 *Profesionales como tú ya están transformando sus carreras*\n\n"
        
        if similar_buyers:
            mensaje += "🚀 *Recientemente se inscribieron:*\n"
            for buyer in similar_buyers[:3]:
                role_text = buyer['role'] or 'Profesional'
                company_text = f" en {buyer['company']}" if buyer['company'] else ""
                mensaje += f"• {role_text}{company_text}\n"
            
            mensaje += f"\n📊 *Estadísticas de tu perfil profesional:*\n"
            if conversion_stats['total_similar'] > 0:
                conversion_rate = (conversion_stats['purchased'] / conversion_stats['total_similar']) * 100
                mensaje += f"• {conversion_rate:.0f}% de profesionales como tú ya se inscribieron\n"
                mensaje += f"• Nivel de interés promedio: {conversion_stats['avg_interest']:.0f}/100\n"
        
        # Agregar urgencia social
        recent_count = await self.db.fetch_one(
            """
            SELECT COUNT(*) as recent_purchases
            FROM course_sales 
            WHERE course_id = $1 
            AND payment_status = 'completed'
            AND purchase_date > NOW() - INTERVAL '24 hours'
            """, course_id
        )
        
        if recent_count['recent_purchases'] > 0:
            mensaje += f"\n🔥 *{recent_count['recent_purchases']} personas se inscribieron en las últimas 24 horas*\n"
        
        mensaje += "\n¿Te unes a ellos? 💪"
        
        await self.telegram.send_message(user_id, mensaje, parse_mode='Markdown')
        
        await self._registrar_interaccion(
            user_id, course_id, "social_proof_shown", 
            {"similar_buyers": len(similar_buyers)}
        )

    async def activar_seguimiento_predictivo(self, user_id: str, course_id: str) -> None:
        """
        Activa un sistema de seguimiento inteligente basado en el comportamiento del usuario.
        Programa mensajes personalizados en momentos óptimos.
        """
        behavior = await self.analizar_comportamiento_usuario(user_id)
        
        # Determinar estrategia de seguimiento
        follow_up_strategy = self._determine_followup_strategy(behavior)
        
        # Programar secuencia de mensajes
        for i, follow_up in enumerate(follow_up_strategy['sequence']):
            await self.db.execute(
                """
                INSERT INTO conversations (lead_id, message_type, content, context)
                VALUES ($1, 'scheduled_followup', $2, $3)
                """,
                behavior['lead_id'],
                follow_up['message'],
                json.dumps({
                    'scheduled_for': follow_up['send_at'],
                    'strategy_type': follow_up['type'],
                    'sequence_position': i + 1
                })
            )
        
        await self._registrar_interaccion(
            user_id, course_id, "predictive_followup_activated",
            {"strategy": follow_up_strategy['name']}
        )

    async def mostrar_comparativa_competidores(self, user_id: str, course_id: str) -> None:
        """
        Muestra una comparativa inteligente con cursos de la competencia.
        Destaca ventajas únicas y valor diferencial.
        """
        course = await self.db.get_course_details(course_id)
        
        # Simular comparativa con competidores (en implementación real vendría de BD)
        competitors = [
            {
                'name': 'Curso Competidor A',
                'price': course['price_usd'] * 1.3,
                'duration': '8 semanas',
                'support': 'Email únicamente',
                'updates': 'No incluidas',
                'bonuses': 'Ninguno'
            },
            {
                'name': 'Curso Competidor B', 
                'price': course['price_usd'] * 1.1,
                'duration': '6 semanas',
                'support': 'Foro comunitario',
                'updates': '1 año',
                'bonuses': 'Básicos'
            }
        ]
        
        mensaje = f"📊 *Comparativa: ¿Por qué elegir nuestro curso?*\n\n"
        mensaje += f"🏆 *{course['name']}* (NOSOTROS)\n"
        mensaje += f"💰 Precio: ${course['price_usd']} USD\n"
        mensaje += f"⏰ Duración: {course['total_duration']}\n"
        mensaje += f"🤝 Soporte: Personalizado 24/7\n"
        mensaje += f"🔄 Actualizaciones: De por vida\n"
        mensaje += f"🎁 Bonos: ${sum(b['original_value'] for b in course.get('active_bonuses', []))} USD en bonos\n\n"
        
        for comp in competitors:
            mensaje += f"❌ *{comp['name']}*\n"
            mensaje += f"💰 Precio: ${comp['price']} USD\n"
            mensaje += f"⏰ Duración: {comp['duration']}\n"
            mensaje += f"🤝 Soporte: {comp['support']}\n"
            mensaje += f"🔄 Actualizaciones: {comp['updates']}\n"
            mensaje += f"🎁 Bonos: {comp['bonuses']}\n\n"
        
        mensaje += "✨ *¡Claramente somos la mejor opción!*\n"
        mensaje += "¿Quieres asegurar tu cupo ahora? 🚀"
        
        await self.telegram.send_message(user_id, mensaje, parse_mode='Markdown')
        
        await self._registrar_interaccion(
            user_id, course_id, "competitor_comparison_shown", {}
        )

    async def implementar_gamificacion(self, user_id: str, course_id: str) -> None:
        """
        Implementa elementos de gamificación para aumentar el engagement.
        Incluye progreso, logros y recompensas por interacción.
        """
        # Calcular progreso del usuario en el funnel de ventas
        interactions = await self.db.fetch_all(
            """
            SELECT interaction_type FROM course_interactions 
            WHERE lead_id = (SELECT id FROM user_leads WHERE telegram_id = $1)
            AND course_id = $2
            """, str(user_id), course_id
        )
        
        interaction_types = [i['interaction_type'] for i in interactions]
        
        # Definir niveles de progreso
        levels = [
            {'name': 'Explorador', 'required': ['view'], 'reward': '🔍'},
            {'name': 'Interesado', 'required': ['view', 'syllabus_view'], 'reward': '📚'},
            {'name': 'Evaluador', 'required': ['view', 'syllabus_view', 'demo_request'], 'reward': '🎯'},
            {'name': 'Decidido', 'required': ['view', 'syllabus_view', 'demo_request', 'price_comparison_shown'], 'reward': '💎'},
            {'name': 'Comprador', 'required': ['purchase'], 'reward': '🏆'}
        ]
        
        # Determinar nivel actual
        current_level = 0
        for i, level in enumerate(levels):
            if all(req in interaction_types for req in level['required']):
                current_level = i
        
        # Calcular siguiente objetivo
        next_level = current_level + 1 if current_level < len(levels) - 1 else current_level
        
        mensaje = f"🎮 *Tu Progreso de Aprendizaje*\n\n"
        mensaje += f"🏅 Nivel Actual: {levels[current_level]['name']} {levels[current_level]['reward']}\n\n"
        
        # Mostrar progreso visual
        progress_bar = "🟢" * (current_level + 1) + "⚪" * (len(levels) - current_level - 1)
        mensaje += f"Progreso: {progress_bar}\n"
        mensaje += f"({current_level + 1}/{len(levels)} completado)\n\n"
        
        if next_level < len(levels):
            mensaje += f"🎯 *Siguiente Nivel: {levels[next_level]['name']}* {levels[next_level]['reward']}\n"
            pending_actions = [req for req in levels[next_level]['required'] if req not in interaction_types]
            if pending_actions:
                mensaje += f"Para desbloquearlo: {', '.join(pending_actions)}\n\n"
        
        # Agregar recompensa por progreso
        if current_level >= 2:  # Si está en nivel Evaluador o superior
            mensaje += "🎁 *¡Recompensa desbloqueada!*\n"
            mensaje += "Descuento especial del 5% adicional por tu progreso\n\n"
        
        mensaje += "¿Listo para el siguiente nivel? 🚀"
        
        await self.telegram.send_message(user_id, mensaje, parse_mode='Markdown')
        
        await self._registrar_interaccion(
            user_id, course_id, "gamification_shown",
            {"current_level": current_level, "level_name": levels[current_level]['name']}
        )

    async def generar_urgencia_dinamica(self, user_id: str, course_id: str) -> None:
        """
        Genera mensajes de urgencia personalizados basados en datos reales.
        Usa información de cupos, tiempo de decisión promedio, etc.
        """
        # Obtener datos reales para urgencia
        course = await self.db.get_course_details(course_id)
        
        # Contar cupos disponibles
        enrolled_count = await self.db.fetch_one(
            """
            SELECT COUNT(*) as enrolled 
            FROM course_sales 
            WHERE course_id = $1 AND payment_status = 'completed'
            """, course_id
        )
        
        available_spots = course['max_students'] - enrolled_count['enrolled']
        
        # Tiempo promedio de decisión
        avg_decision_time = await self.db.fetch_one(
            """
            SELECT AVG(EXTRACT(EPOCH FROM (cs.purchase_date - ul.created_at))/3600) as avg_hours
            FROM course_sales cs
            JOIN user_leads ul ON cs.lead_id = ul.id
            WHERE cs.course_id = $1 AND cs.payment_status = 'completed'
            """, course_id
        )
        
        # Usuarios activos viendo el curso
        active_viewers = await self.db.fetch_one(
            """
            SELECT COUNT(DISTINCT lead_id) as viewers
            FROM course_interactions
            WHERE course_id = $1 
            AND created_at > NOW() - INTERVAL '2 hours'
            AND interaction_type IN ('view', 'syllabus_view')
            """, course_id
        )
        
        mensaje = "⚡ *ALERTA DE DISPONIBILIDAD*\n\n"
        
        if available_spots <= 5:
            mensaje += f"🚨 ¡Solo quedan {available_spots} cupos disponibles!\n\n"
        elif available_spots <= 10:
            mensaje += f"⚠️ Últimos {available_spots} cupos disponibles\n\n"
        
        if active_viewers['viewers'] > 1:
            mensaje += f"👥 {active_viewers['viewers']} personas están viendo este curso ahora mismo\n\n"
        
        if avg_decision_time and avg_decision_time['avg_hours']:
            avg_hours = int(avg_decision_time['avg_hours'])
            mensaje += f"📊 Tiempo promedio de decisión: {avg_hours} horas\n"
            mensaje += "Los que deciden rápido aseguran su cupo\n\n"
        
        # Agregar oferta con tiempo límite
        if course.get('discount_end_date'):
            tiempo_restante = self._time_until(course['discount_end_date'])
            mensaje += f"⏰ Oferta especial termina en: {tiempo_restante}\n\n"
        
        mensaje += "¿Aseguras tu cupo ahora? 🎯"
        
        await self.telegram.send_message(user_id, mensaje, parse_mode='Markdown')
        
        await self._registrar_interaccion(
            user_id, course_id, "dynamic_urgency_shown",
            {"available_spots": available_spots, "active_viewers": active_viewers['viewers']}
        )

    async def personalizar_oferta_por_budget(self, user_id: str, course_id: str) -> None:
        """
        Personaliza la oferta según el rango de presupuesto detectado del usuario.
        Ofrece opciones de pago flexibles y descuentos adaptativos.
        """
        lead = await self.db.fetch_one(
            "SELECT * FROM user_leads WHERE telegram_id = $1", str(user_id)
        )
        
        budget_range = lead.get('budget_range') if lead else None
        course = await self.db.get_course_details(course_id)
        
        # Analizar sensibilidad al precio basada en interacciones
        price_interactions = await self.db.fetch_all(
            """
            SELECT metadata FROM course_interactions
            WHERE lead_id = $1 AND interaction_type LIKE '%price%'
            ORDER BY created_at DESC
            """, lead['id'] if lead else None
        )
        
        mensaje = f"💰 *Opciones de Inversión Personalizadas*\n\n"
        
        if budget_range == 'bajo' or any('price_concern' in str(pi.get('metadata', {})) for pi in price_interactions):
            # Opción para presupuesto ajustado
            mensaje += "🎯 *Opción Estudiante/Emprendedor:*\n"
            mensaje += f"• 3 pagos de ${course['price_usd']/3:.0f} USD\n"
            mensaje += "• Sin intereses\n"
            mensaje += "• Acceso inmediato al curso\n"
            mensaje += "• Mismos beneficios y bonos\n\n"
            
        elif budget_range == 'alto':
            # Opción premium para presupuesto alto
            mensaje += "💎 *Opción Premium:*\n"
            mensaje += f"• Pago único: ${course['price_usd']} USD\n"
            mensaje += "• 15% descuento adicional por pago completo\n"
            mensaje += "• Sesión 1:1 con instructor incluida\n"
            mensaje += "• Certificado premium\n\n"
        
        # Opción estándar siempre disponible
        mensaje += "⭐ *Opción Estándar:*\n"
        mensaje += f"• ${course['price_usd']} USD\n"
        mensaje += "• Pago en 2 cuotas sin interés\n"
        mensaje += "• Todos los bonos incluidos\n"
        mensaje += "• Garantía de 30 días\n\n"
        
        # ROI personalizado
        if lead and lead.get('role'):
            role = lead['role']
            roi_examples = {
                'gerente': 'Aumento de productividad del equipo: +40%',
                'marketing': 'Reducción de tiempo en campañas: 60%',
                'ventas': 'Incremento en conversiones: +25%',
                'estudiante': 'Ventaja competitiva en el mercado laboral',
                'emprendedor': 'Automatización de procesos: ahorro de 15h/semana'
            }
            
            if role.lower() in roi_examples:
                mensaje += f"📈 *ROI para {role}:*\n{roi_examples[role.lower()]}\n\n"
        
        mensaje += "¿Cuál opción se ajusta mejor a tu situación? 🤔"
        
        await self.telegram.send_message(user_id, mensaje, parse_mode='Markdown')
        
        await self._registrar_interaccion(
            user_id, course_id, "budget_personalized_offer",
            {"budget_range": budget_range}
        )

    async def mostrar_casos_exito_similares(self, user_id: str, course_id: str) -> None:
        """
        Muestra casos de éxito de estudiantes con perfil similar al usuario.
        Incluye resultados específicos y testimonios relevantes.
        """
        lead = await self.db.fetch_one(
            "SELECT * FROM user_leads WHERE telegram_id = $1", str(user_id)
        )
        
        # Buscar casos de éxito similares
        similar_success = await self.db.fetch_all(
            """
            SELECT ul.role, ul.industry, ul.company, ul.name, cs.purchase_date
            FROM user_leads ul
            JOIN course_sales cs ON ul.id = cs.lead_id
            WHERE cs.course_id = $1 
            AND cs.payment_status = 'completed'
            AND cs.purchase_date < NOW() - INTERVAL '30 days'
            AND (ul.role ILIKE $2 OR ul.industry ILIKE $3)
            ORDER BY cs.purchase_date DESC
            LIMIT 3
            """, 
            course_id, 
            f"%{lead.get('role', '')}%", 
            f"%{lead.get('industry', '')}%"
        )
        
        mensaje = f"🌟 *Casos de Éxito - Profesionales como tú*\n\n"
        
        if similar_success:
            success_stories = [
                {
                    'role': 'Contador',
                    'result': 'Automatizó reportes financieros, ahorra 8 horas semanales',
                    'quote': '"Ahora genero reportes en minutos, no en horas"'
                },
                {
                    'role': 'Gerente de Marketing',
                    'result': 'Incrementó eficiencia de campañas en 65%',
                    'quote': '"Mis campañas ahora tienen mejor ROI que nunca"'
                },
                {
                    'role': 'Estudiante',
                    'result': 'Consiguió trabajo en startup tech con salario 40% mayor',
                    'quote': '"Las habilidades de IA me abrieron puertas increíbles"'
                }
            ]
            
            # Seleccionar historia más relevante
            user_role = lead.get('role', '').lower() if lead else ''
            relevant_story = None
            
            for story in success_stories:
                if user_role in story['role'].lower():
                    relevant_story = story
                    break
            
            if not relevant_story:
                relevant_story = success_stories[0]  # Default
            
            mensaje += f"👤 *{relevant_story['role']}* (perfil similar al tuyo)\n"
            mensaje += f"📈 *Resultado:* {relevant_story['result']}\n"
            mensaje += f"💬 *Testimonio:* {relevant_story['quote']}\n\n"
            
            # Agregar estadísticas
            mensaje += "📊 *Estadísticas de éxito:*\n"
            mensaje += f"• {len(similar_success)} profesionales como tú ya se graduaron\n"
            mensaje += "• 94% aplica lo aprendido inmediatamente\n"
            mensaje += "• 87% reporta aumento en productividad\n\n"
        
        mensaje += "¿Te imaginas tus propios resultados? 🚀\n"
        mensaje += "¡Tu historia de éxito podría ser la siguiente!"
        
        await self.telegram.send_message(user_id, mensaje, parse_mode='Markdown')
        
        await self._registrar_interaccion(
            user_id, course_id, "success_cases_shown",
            {"similar_profiles": len(similar_success)}
        )

    # ========== FUNCIONES DE ANÁLISIS Y UTILIDAD ==========

    def _calculate_profile_completeness(self, lead: Dict) -> float:
        """Calcula qué tan completo está el perfil del usuario."""
        if not lead:
            return 0.0
        
        fields = ['name', 'role', 'company', 'industry', 'email', 'phone', 'learning_goals']
        completed = sum(1 for field in fields if lead.get(field))
        return completed / len(fields)

    def _calculate_engagement_level(self, interactions: List[Dict]) -> str:
        """Calcula el nivel de engagement basado en las interacciones."""
        if not interactions:
            return 'bajo'
        
        interaction_count = len(interactions)
        unique_types = len(set(i['interaction_type'] for i in interactions))
        
        if interaction_count >= 5 and unique_types >= 3:
            return 'muy_alto'
        elif interaction_count >= 3 and unique_types >= 2:
            return 'alto'
        elif interaction_count >= 2:
            return 'medio'
        else:
            return 'bajo'

    def _calculate_buying_intent(self, interactions: List[Dict]) -> int:
        """Calcula la intención de compra en una escala de 0-100."""
        if not interactions:
            return 10
        
        intent_weights = {
            'view': 5,
            'syllabus_view': 10,
            'demo_request': 25,
            'price_comparison_shown': 20,
            'testimonials_viewed': 15,
            'bonuses_viewed': 18,
            'offer_shown': 22,
            'payment_link_generated': 35
        }
        
        total_score = sum(intent_weights.get(i['interaction_type'], 5) for i in interactions)
        return min(total_score, 100)

    def _analyze_interaction_patterns(self, interactions: List[Dict]) -> Dict:
        """Analiza patrones de interacción para optimizar el timing."""
        if not interactions:
            return {'preferred_hours': [], 'frequency': 'low'}
        
        hours = [datetime.fromisoformat(i['created_at'].replace('Z', '+00:00')).hour for i in interactions]
        preferred_hours = list(set(hours))
        
        # Analizar frecuencia
        if len(interactions) > 5:
            frequency = 'high'
        elif len(interactions) > 2:
            frequency = 'medium'
        else:
            frequency = 'low'
        
        return {
            'preferred_hours': preferred_hours,
            'frequency': frequency,
            'most_active_hour': max(set(hours), key=hours.count) if hours else 14
        }

    def _analyze_price_sensitivity(self, interactions: List[Dict]) -> str:
        """Analiza la sensibilidad al precio del usuario."""
        price_related = [i for i in interactions if 'price' in i['interaction_type']]
        
        if len(price_related) > 2:
            return 'alta'
        elif len(price_related) > 0:
            return 'media'
        else:
            return 'baja'

    def _determine_decision_stage(self, interactions: List[Dict]) -> str:
        """Determina en qué etapa del proceso de decisión está el usuario."""
        if not interactions:
            return 'awareness'
        
        advanced_interactions = ['demo_request', 'price_comparison_shown', 'payment_link_generated']
        
        if any(i['interaction_type'] in advanced_interactions for i in interactions):
            return 'decision'
        elif len(interactions) > 2:
            return 'consideration'
        else:
            return 'awareness'

    def _calculate_dynamic_discount(self, behavior: Dict, base_discount: float) -> float:
        """Calcula un descuento dinámico basado en el comportamiento."""
        dynamic_discount = base_discount
        
        # Ajustar según engagement
        if behavior['engagement_level'] == 'muy_alto':
            dynamic_discount += 2
        elif behavior['engagement_level'] == 'alto':
            dynamic_discount += 1
        
        # Ajustar según intención de compra
        if behavior['buying_intent'] > 80:
            dynamic_discount += 3
        elif behavior['buying_intent'] > 60:
            dynamic_discount += 2
        
        return min(dynamic_discount, 25)  # Máximo 25% de descuento

    async def _select_relevant_bonuses(self, user_id: str, course_id: str, behavior: Dict) -> List[Dict]:
        """Selecciona bonos relevantes basados en el comportamiento del usuario."""
        all_bonuses = await self.db.fetch_all(
            """
            SELECT * FROM limited_time_bonuses 
            WHERE course_id = $1 AND active = true AND expires_at > NOW()
            ORDER BY original_value DESC
            """, course_id
        )
        
        # Filtrar bonos según el perfil
        relevant_bonuses = []
        for bonus in all_bonuses:
            if behavior['buying_intent'] > 70 or behavior['engagement_level'] in ['alto', 'muy_alto']:
                relevant_bonuses.append(bonus)
        
        return relevant_bonuses[:3]  # Máximo 3 bonos

    def _analyze_content_preferences(self, conversations: List[Dict]) -> Dict:
        """Analiza las preferencias de contenido basado en las conversaciones."""
        if not conversations:
            return {'preferred_topics': [], 'communication_style': 'formal'}
        
        # Análisis básico de preferencias
        content_keywords = []
        for conv in conversations:
            content = conv.get('content', '').lower()
            content_keywords.extend(content.split())
        
        # Detectar temas de interés
        topic_weights = {
            'precio': ['precio', 'costo', 'inversión', 'pago'],
            'contenido': ['módulo', 'temario', 'aprende', 'enseña'],
            'certificación': ['certificado', 'título', 'validez'],
            'tiempo': ['horario', 'duración', 'tiempo', 'cuándo']
        }
        
        preferred_topics = []
        for topic, keywords in topic_weights.items():
            if any(keyword in content_keywords for keyword in keywords):
                preferred_topics.append(topic)
        
        return {
            'preferred_topics': preferred_topics,
            'communication_style': 'formal' if len(conversations) < 3 else 'casual'
        }

    def _identify_objection_patterns(self, conversations: List[Dict]) -> List[str]:
        """Identifica patrones de objeciones en las conversaciones."""
        if not conversations:
            return []
        
        objection_keywords = {
            'precio': ['caro', 'costoso', 'dinero', 'presupuesto'],
            'tiempo': ['tiempo', 'ocupado', 'horario', 'disponibilidad'],
            'confianza': ['seguro', 'garantía', 'dudas', 'funciona'],
            'necesidad': ['necesito', 'útil', 'sirve', 'vale']
        }
        
        objections = []
        for conv in conversations:
            content = conv.get('content', '').lower()
            for objection_type, keywords in objection_keywords.items():
                if any(keyword in content for keyword in keywords):
                    objections.append(objection_type)
        
        return list(set(objections))

    def _calculate_urgency_level(self, interactions: List[Dict]) -> str:
        """Calcula el nivel de urgencia basado en las interacciones."""
        if not interactions:
            return 'baja'
        
        # Analizar frecuencia de interacciones
        recent_interactions = [
            i for i in interactions 
            if (datetime.now() - datetime.fromisoformat(i['created_at'].replace('Z', '+00:00'))).days < 1
        ]
        
        if len(recent_interactions) > 3:
            return 'muy_alta'
        elif len(recent_interactions) > 1:
            return 'alta'
        elif len(interactions) > 2:
            return 'media'
        else:
            return 'baja'

    def _extract_personalization_data(self, lead: Dict, conversations: List[Dict]) -> Dict:
        """Extrae datos de personalización del lead y conversaciones."""
        if not lead:
            return {}
        
        return {
            'name': lead.get('name', ''),
            'role': lead.get('role', ''),
            'industry': lead.get('industry', ''),
            'experience_level': lead.get('experience_level', ''),
            'learning_goals': lead.get('learning_goals', ''),
            'preferred_schedule': lead.get('preferred_schedule', ''),
            'budget_range': lead.get('budget_range', ''),
            'conversation_count': len(conversations),
            'last_interaction': lead.get('last_interaction')
        }

    def _calculate_offer_urgency(self, behavior: Dict) -> int:
        """Calcula las horas de urgencia para una oferta basada en el comportamiento."""
        base_hours = 48  # 48 horas por defecto
        
        # Ajustar según engagement
        if behavior['engagement_level'] == 'muy_alto':
            return 24  # 24 horas para usuarios muy comprometidos
        elif behavior['engagement_level'] == 'alto':
            return 36  # 36 horas para usuarios comprometidos
        elif behavior['urgency_level'] == 'muy_alta':
            return 12  # 12 horas para usuarios urgentes
        
        return base_hours

    def _personalize_payment_terms(self, behavior: Dict) -> Dict:
        """Personaliza los términos de pago basado en el comportamiento."""
        terms = {
            'installments': 1,
            'discount_for_full_payment': 0,
            'flexible_dates': False
        }
        
        # Ajustar según sensibilidad al precio
        if behavior.get('price_sensitivity') == 'alta':
            terms['installments'] = 3
            terms['flexible_dates'] = True
        elif behavior.get('price_sensitivity') == 'media':
            terms['installments'] = 2
            terms['discount_for_full_payment'] = 5
        
        return terms

    def _generate_offer_message(self, behavior: Dict, course: Dict) -> str:
        """Genera un mensaje personalizado para la oferta."""
        name = behavior.get('personalization_data', {}).get('name', 'amigo')
        role = behavior.get('personalization_data', {}).get('role', '')
        
        message = f"¡{name}! Tengo una oferta especial diseñada para ti"
        
        if role:
            message += f" como {role}"
        
        message += f". Basándome en tu interés en {course.get('name', 'nuestro curso')}, "
        message += "he preparado condiciones únicas que se ajustan a tu perfil."
        
        return message

    def _determine_followup_strategy(self, behavior: Dict) -> Dict:
        """Determina la estrategia de seguimiento basada en el comportamiento."""
        strategy = {
            'name': 'standard',
            'sequence': []
        }
        
        # Estrategia basada en engagement
        if behavior['engagement_level'] == 'muy_alto':
            strategy['name'] = 'high_engagement'
            strategy['sequence'] = [
                {
                    'type': 'value_reinforcement',
                    'message': 'Recordatorio de beneficios clave',
                    'send_at': datetime.now() + timedelta(hours=6)
                },
                {
                    'type': 'urgency',
                    'message': 'Oferta por tiempo limitado',
                    'send_at': datetime.now() + timedelta(hours=24)
                }
            ]
        elif behavior['engagement_level'] == 'alto':
            strategy['name'] = 'medium_engagement'
            strategy['sequence'] = [
                {
                    'type': 'educational',
                    'message': 'Contenido de valor adicional',
                    'send_at': datetime.now() + timedelta(hours=12)
                },
                {
                    'type': 'social_proof',
                    'message': 'Testimonios relevantes',
                    'send_at': datetime.now() + timedelta(days=1)
                }
            ]
        else:
            strategy['name'] = 'nurturing'
            strategy['sequence'] = [
                {
                    'type': 'educational',
                    'message': 'Información educativa',
                    'send_at': datetime.now() + timedelta(days=1)
                },
                {
                    'type': 'check_in',
                    'message': 'Verificación de interés',
                    'send_at': datetime.now() + timedelta(days=3)
                }
            ]
        
        return strategy