"""
Herramientas del agente de ventas para interactuar con usuarios y gestionar recursos.
VERSIÓN MIGRADA - Compatible con nueva estructura de base de datos.
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
        MIGRADO: Usa ai_courses con campos actualizados.
        """
        # Obtener detalles del curso desde nueva estructura
        course = await self.db.get_course_details(course_id)
        if not course:
            return
        
        # Calcular descuento si existe (funcionalidad removida en nueva estructura)
        precio_final = course['price']  # Cambio: price_usd → price
        
        # Usar plantilla centralizada para generar mensaje
        from core.utils.course_templates import CourseTemplates
        
        # Agregar datos de descuento calculado para la plantilla
        course_with_discount = course.copy()
        course_with_discount['calculated_price'] = precio_final
        
        mensaje = CourseTemplates.format_course_details_with_benefits(course_with_discount)
        
        # Enviar mensaje (thumbnail_url eliminado en nueva estructura)
        await self.telegram.send_message(
            user_id,
            mensaje,
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
        MIGRADO: Usa ai_courses, preview_url eliminado de nueva estructura.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        # preview_url eliminado en nueva estructura, usar course_url
        preview_url = course.get('course_url')
        
        mensaje = f"""🎥 *Preview del curso: {course['name']}*

Te comparto este video donde podrás ver:
- 👨🏫 Metodología de enseñanza
- 📚 Ejemplos de contenido
- 💡 Proyectos prácticos
- 🎯 Resultados esperados

¡Mira el video y pregúntame cualquier duda! 😊"""

        if preview_url:
            await self.telegram.send_video(
                user_id,
                preview_url,
                caption=mensaje,
                parse_mode='Markdown'
            )
        else:
            await self.telegram.send_message(
                user_id,
                mensaje + "\n\n❌ Video no disponible temporalmente",
                parse_mode='Markdown'
            )

        await self._registrar_interaccion(
            user_id,
            course_id,
            "preview_watch",
            {"video_url": preview_url}
        )

    async def mostrar_syllabus_interactivo(self, user_id: str, course_id: str) -> None:
        """
        Presenta el syllabus de manera interactiva con botones para expandir módulos.
        MIGRADO: Usa ai_course_sessions en lugar de course_modules.
        """
        course = await self.db.get_course_details(course_id)
        if not course or not course.get('sessions'):
            return

        from core.utils.course_templates import CourseTemplates
        mensaje = CourseTemplates.format_course_modules_detailed(course)

        # Crear botones para sesiones interactivas
        buttons = []
        sessions = course['sessions']
        
        for session in sessions[:5]:  # Mostrar máximo 5 sesiones
            buttons.append([{
                "text": f"📖 {session['title']}",
                "callback_data": f"show_session_{session['id']}"
            }])
        
        # Agregar botón de prácticas
        buttons.append([{
            "text": "🛠️ Ver Prácticas",
            "callback_data": f"show_practices_{course_id}"
        }])
        
        # Agregar botón de entregables
        buttons.append([{
            "text": "📁 Ver Entregables",
            "callback_data": f"show_deliverables_{course_id}"
        }])

        buttons.append([{
            "text": "💰 Ver Precio",
            "callback_data": f"show_pricing_{course_id}"
        }])

        keyboard = {"inline_keyboard": buttons}

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown',
            reply_markup=keyboard
        )

        await self._registrar_interaccion(
            user_id,
            course_id,
            "syllabus_view",
            {"sessions_count": len(sessions)}
        )

    async def mostrar_ofertas_limitadas(self, user_id: str, course_id: str) -> None:
        """
        Muestra ofertas por tiempo limitado para el curso.
        MANTENIDO: Usa limited_time_bonuses sin cambios.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        # Obtener bonos activos (tabla se mantiene igual)
        bonos = await self.db.fetch_all(
            """
            SELECT * FROM limited_time_bonuses
            WHERE course_id = $1 AND active = true AND expires_at > NOW()
            ORDER BY expires_at ASC
            """,
            course_id
        )

        if not bonos:
            return

        mensaje = f"""🎯 *¡Ofertas Especiales Disponibles!*

Para el curso *{course['name']}*:

"""

        for bono in bonos:
            tiempo_restante = bono['expires_at'] - datetime.now(timezone.utc)
            horas_restantes = tiempo_restante.total_seconds() / 3600
            
            mensaje += f"""🎁 *{bono['bonus_name']}*
💰 Valor: ${bono['bonus_value']} USD
⏰ Expira en: {int(horas_restantes)} horas
📦 Incluye: {bono['bonus_description']}

"""

        mensaje += "⚡ *¡No pierdas esta oportunidad única!*"

        buttons = {
            "inline_keyboard": [
                [{"text": "🛒 Aprovechar Oferta", "callback_data": f"claim_bonus_{course_id}"}],
                [{"text": "📋 Ver Detalles", "callback_data": f"show_bonus_details_{course_id}"}],
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
            "limited_offers_shown",
            {"bonuses_count": len(bonos)}
        )

    async def agendar_demo_personalizada(self, user_id: str, course_id: str) -> None:
        """
        Permite agendar una demo personalizada 1:1 con instructor.
        MIGRADO: Usa ai_courses con campos actualizados.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        mensaje = f"""🎯 *Demo Personalizada 1:1*

Para el curso: *{course['name']}*

En esta sesión personal de 30 minutos:
- 👨🏫 Conocerás al instructor
- 📚 Verás el contenido en vivo
- 💡 Resolverás tus dudas específicas
- 🎯 Diseñaremos tu plan de aprendizaje

*¡Completamente gratis y sin compromiso!*

📅 Horarios disponibles:
• Lunes a Viernes: 9:00 AM - 6:00 PM
• Sábados: 10:00 AM - 2:00 PM
• Domingos: Cerrado

¿Cuándo te gustaría agendar?"""

        # demo_request_link eliminado en nueva estructura, usar purchase_url
        demo_link = course.get('purchase_url', '#')
        
        buttons = {
            "inline_keyboard": [
                [{"text": "📅 Agendar Ahora", "url": demo_link}],
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
        MIGRADO: Usa ai_session_deliverables en lugar de free_resources.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        # Obtener entregables gratuitos desde nueva estructura
        free_resources = await self.db.fetch_all(
            """
            SELECT 
                d.name as resource_name,
                d.type as resource_type,
                d.resource_url,
                d.estimated_duration_min,
                s.title as session_title
            FROM ai_session_deliverables d
            JOIN ai_course_sessions s ON d.session_id = s.id
            WHERE s.course_id = $1 AND d.is_mandatory = false
            ORDER BY s.session_index, d.name
            """,
            course_id
        )

        mensaje = f"""🎁 *¡Regalo especial para ti!*

Te comparto estos recursos gratuitos del curso *{course['name']}*:

📚 *Recursos disponibles:*
"""

        buttons_list = []
        
        if free_resources:
            for resource in free_resources:
                # Agregar descripción del recurso
                duration_text = f" ({resource['estimated_duration_min']} min)" if resource['estimated_duration_min'] else ""
                mensaje += f"• {resource['resource_name']}{duration_text}\n"
                mensaje += f"  📖 Sesión: {resource['session_title']}\n"
                
                # Agregar botón de descarga
                if resource['resource_url']:
                    buttons_list.append([{"text": f"📥 {resource['resource_name']}", "url": resource['resource_url']}])
        else:
            mensaje += "• Guía PDF: \"Primeros pasos en IA\"\n"
            mensaje += "• Templates listos para usar\n"
            mensaje += "• Lista de herramientas recomendadas\n"
            mensaje += "• Checklist de mejores prácticas\n"
            
            # Botón de recursos generales si no hay recursos específicos
            if course.get('course_url'):
                buttons_list.append([{"text": "📥 Descargar Recursos", "url": course['course_url']}])

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
        Muestra comparativa de precios y valor total del curso.
        MIGRADO: Usa ai_courses con campos simplificados.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        # Campos simplificados en nueva estructura
        precio_curso = course['price']
        currency = course.get('currency', 'USD')
        
        mensaje = f"""💰 *Análisis de Inversión*

Para el curso: *{course['name']}*

💳 **Precio del curso:** ${precio_curso} {currency}

📊 **Valor que recibes:**
• 📚 {course.get('session_count', 0)} sesiones completas
• ⏱️ {course.get('total_duration_min', 0)} minutos de contenido
• 📖 Material de estudio incluido
• 🎓 Certificado al completar
• 💬 Soporte directo con instructores
• 🔄 Acceso de por vida
• 📱 Acceso desde cualquier dispositivo

**Valor total estimado:** ${precio_curso * 3} {currency}
**Tu precio:** ${precio_curso} {currency}
**Ahorro:** ${precio_curso * 2} {currency}

💡 **Comparativa con alternativas:**
• Curso universitario: ${precio_curso * 5} {currency}
• Consultoría 1:1: ${precio_curso * 8} {currency}
• Bootcamp presencial: ${precio_curso * 10} {currency}

¡Estás ahorrando más del 80% comparado con otras opciones!"""

        buttons = {
            "inline_keyboard": [
                [{"text": "💳 Inscribirme Ahora", "callback_data": f"enroll_{course_id}"}],
                [{"text": "💰 Ver Opciones de Pago", "callback_data": f"payment_options_{course_id}"}],
                [{"text": "📊 Garantía de Satisfacción", "callback_data": f"show_guarantee_{course_id}"}],
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
            "pricing_comparison_shown",
            {"shown_price": precio_curso}
        )

    async def mostrar_session_practices(self, user_id: str, session_id: str) -> None:
        """
        Muestra las prácticas de una sesión específica.
        NUEVO: Funcionalidad agregada para nueva estructura.
        """
        # Obtener prácticas desde nueva estructura
        practices = await self.db.fetch_all(
            """
            SELECT 
                p.title,
                p.description,
                p.estimated_duration_min,
                p.resource_type,
                p.is_mandatory,
                s.title as session_title
            FROM ai_session_practices p
            JOIN ai_course_sessions s ON p.session_id = s.id
            WHERE p.session_id = $1
            ORDER BY p.practice_index
            """,
            session_id
        )

        if not practices:
            return

        session_title = practices[0]['session_title']
        
        mensaje = f"""🛠️ *Prácticas de la Sesión*

*{session_title}*

📝 **Ejercicios prácticos:**
"""

        for i, practice in enumerate(practices, 1):
            mandatory_icon = "🔴" if practice['is_mandatory'] else "🟡"
            duration_text = f" ({practice['estimated_duration_min']} min)" if practice['estimated_duration_min'] else ""
            
            mensaje += f"\n{mandatory_icon} **{i}. {practice['title']}**{duration_text}\n"
            mensaje += f"   {practice['description']}\n"
            if practice['resource_type']:
                mensaje += f"   📁 Tipo: {practice['resource_type']}\n"

        mensaje += "\n🔴 Obligatorio | 🟡 Opcional"

        buttons = {
            "inline_keyboard": [
                [{"text": "📖 Volver a Sesiones", "callback_data": f"show_syllabus_{session_id}"}],
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
            session_id,
            "session_practices_shown",
            {"practices_count": len(practices)}
        )

    async def mostrar_session_deliverables(self, user_id: str, session_id: str) -> None:
        """
        Muestra los entregables de una sesión específica.
        NUEVO: Funcionalidad agregada para nueva estructura.
        """
        # Obtener entregables desde nueva estructura
        deliverables = await self.db.fetch_all(
            """
            SELECT 
                d.name,
                d.type,
                d.resource_url,
                d.estimated_duration_min,
                d.is_mandatory,
                s.title as session_title
            FROM ai_session_deliverables d
            JOIN ai_course_sessions s ON d.session_id = s.id
            WHERE d.session_id = $1
            ORDER BY d.name
            """,
            session_id
        )

        if not deliverables:
            return

        session_title = deliverables[0]['session_title']
        
        mensaje = f"""📁 *Entregables de la Sesión*

*{session_title}*

📦 **Recursos incluidos:**
"""

        buttons_list = []
        
        for i, deliverable in enumerate(deliverables, 1):
            mandatory_icon = "🔴" if deliverable['is_mandatory'] else "🟡"
            duration_text = f" ({deliverable['estimated_duration_min']} min)" if deliverable['estimated_duration_min'] else ""
            
            mensaje += f"\n{mandatory_icon} **{i}. {deliverable['name']}**{duration_text}\n"
            mensaje += f"   📄 Tipo: {deliverable['type']}\n"
            
            # Agregar botón de descarga si hay URL
            if deliverable['resource_url']:
                buttons_list.append([{"text": f"📥 {deliverable['name']}", "url": deliverable['resource_url']}])

        mensaje += "\n🔴 Obligatorio | 🟡 Opcional"

        # Agregar botones adicionales
        buttons_list.extend([
            [{"text": "📖 Volver a Sesiones", "callback_data": f"show_syllabus_{session_id}"}],
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
            session_id,
            "session_deliverables_shown",
            {"deliverables_count": len(deliverables)}
        )

    async def contactar_asesor_directo(self, user_id: str, course_id: str = None) -> None:
        """
        Inicia flujo directo de contacto con asesor.
        MANTENIDO: Funcionalidad sin cambios.
        """
        # Importar y activar el flujo de contacto
        from core.handlers.contact_flow import ContactFlowHandler
        
        # Esta función activará el flujo de contacto que recogerá datos del usuario
        contact_handler = ContactFlowHandler(self.db, self.telegram)
        await contact_handler.start_contact_flow(user_id, course_id)

    async def _registrar_interaccion(self, user_id: str, course_id: str, action: str, metadata: dict) -> None:
        """
        Registra interacciones del usuario para análisis.
        MANTENIDO: Tabla course_interactions sin cambios.
        """
        try:
            await self.db.execute(
                """
                INSERT INTO course_interactions 
                (lead_id, course_id, interaction_type, metadata, created_at)
                VALUES (
                    (SELECT id FROM user_leads WHERE telegram_id = $1),
                    $2, $3, $4, NOW()
                )
                """,
                str(user_id), course_id, action, json.dumps(metadata)
            )
        except Exception as e:
            print(f"Error registrando interacción: {e}")

    # Métodos adicionales para compatibilidad con herramientas existentes...
    # [Resto de métodos se mantienen similares con adaptaciones de campos]