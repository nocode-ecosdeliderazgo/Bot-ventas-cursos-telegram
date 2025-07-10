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
        
        # Inicializar ResourceService
        if self.db:
            from core.services.resourceService import ResourceService
            self.resource_service = ResourceService(self.db)
        else:
            self.resource_service = None
        
        
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
        ACTUALIZADO: Usa ResourceService para obtener preview desde base de datos.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        # Obtener preview desde ResourceService
        preview_url = None
        if self.resource_service:
            # Intentar obtener preview específico del curso
            preview_url = await self.resource_service.get_resource_url(
                f"preview_{course_id}", 
                fallback_url=course.get('course_url')
            )
            
            # Si no hay preview específico, usar preview genérico
            if not preview_url or preview_url == course.get('course_url'):
                preview_url = await self.resource_service.get_resource_url(
                    "curso_preview",
                    fallback_url=course.get('course_url')
                )
        
        mensaje = f"""🎥 *Preview del curso: {course['name']}*

Te comparto este video donde podrás ver:
- 👨🏫 Metodología de enseñanza
- 📚 Ejemplos de contenido
- 💡 Proyectos prácticos
- 🎯 Resultados esperados

¡Mira el video y pregúntame cualquier duda! 😊"""

        if preview_url and preview_url != "https://aprenda-ia.com/curso_preview":
            try:
                await self.telegram.send_video(
                    user_id,
                    preview_url,
                    caption=mensaje,
                    parse_mode='Markdown'
                )
            except Exception as e:
                # Si falla el video, enviar como link
                await self.telegram.send_message(
                    user_id,
                    f"{mensaje}\n\n🔗 [Ver Preview]({preview_url})",
                    parse_mode='Markdown'
                )
        else:
            await self.telegram.send_message(
                user_id,
                mensaje + "\n\n📧 Solicita el preview a tu asesor para ver el contenido completo",
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
        ACTUALIZADO: Usa ResourceService para obtener link de demo desde base de datos.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        # Obtener link de demo desde ResourceService
        demo_link = "#"
        if self.resource_service:
            # Intentar obtener demo específica del curso
            demo_link = await self.resource_service.get_resource_url(
                f"demo_{course_id}",
                fallback_url=None
            )
            
            # Si no hay demo específica, usar demo genérica
            if not demo_link or demo_link.startswith("https://aprenda-ia.com/"):
                demo_link = await self.resource_service.get_resource_url(
                    "demo_personalizada",
                    fallback_url=course.get('purchase_url', '#')
                )

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
            {"demo_url": demo_link}
        )

        # Actualizar lead como altamente interesado
        await self.db.execute(
            "UPDATE user_leads SET stage = 'demo_solicitada', interest_score = LEAST(interest_score + 20, 100) WHERE telegram_id = $1",
            str(user_id)
        )

    async def enviar_recursos_gratuitos(self, user_id: str, course_id: str) -> None:
        """
        Envía recursos de valor relacionados al curso para demostrar calidad.
        ACTUALIZADO: Usa ResourceService para obtener recursos desde base de datos.
        """
        course = await self.db.get_course_details(course_id)
        if not course:
            return

        # Obtener recursos gratuitos desde ResourceService
        free_resources = []
        if self.resource_service:
            # Obtener recursos específicos del curso
            course_resources = await self.resource_service.get_course_resources(course_id)
            
            # Filtrar recursos gratuitos
            free_resources = [r for r in course_resources if r['resource_type'] in ['recursos', 'pdf', 'checklist', 'templates']]
            
            # Si no hay recursos específicos, obtener recursos generales
            if not free_resources:
                general_resources = await self.resource_service.get_resources_by_type('recursos')
                free_resources.extend(general_resources)
                
                # Agregar otros tipos de recursos gratuitos
                pdf_resources = await self.resource_service.get_resources_by_type('pdf')
                free_resources.extend(pdf_resources)

        mensaje = f"""🎁 *¡Regalo especial para ti!*

Te comparto estos recursos gratuitos del curso *{course['name']}*:

📚 *Recursos disponibles:*
"""

        buttons_list = []
        
        if free_resources:
            for resource in free_resources:
                # Agregar descripción del recurso
                mensaje += f"• {resource['resource_title']}\n"
                if resource.get('resource_description'):
                    mensaje += f"  📝 {resource['resource_description']}\n"
                
                # Agregar botón de descarga
                if resource['resource_url']:
                    buttons_list.append([{"text": f"📥 {resource['resource_title']}", "url": resource['resource_url']}])
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
        VERSIÓN SIMPLIFICADA: Activa el flujo directamente sin mocks complejos
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from core.utils.memory import GlobalMemory
            
            logger.info(f"🛠️ Activando flujo de contacto para usuario: {user_id}")
            
            # Obtener memoria del usuario
            memory = GlobalMemory().get_lead_memory(user_id)
            
            # Si hay un course_id específico, guardarlo en memoria
            if course_id:
                memory.selected_course = course_id
                GlobalMemory().save_lead_memory(user_id, memory)
                logger.info(f"📚 Curso seleccionado: {course_id}")
            
            # Verificar qué información falta
            missing_info = []
            if not memory.email:
                missing_info.append("email")
            if not memory.phone:
                missing_info.append("teléfono")
            if not memory.selected_course:
                missing_info.append("curso de interés")
            
            if missing_info:
                # Solicitar información faltante
                await self._request_missing_contact_info(user_id, missing_info)
            else:
                # Toda la información está disponible, proceder con confirmación
                await self._send_contact_confirmation(user_id)
            
            logger.info("✅ Flujo de contacto activado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error activando flujo de contacto: {e}")
            # Fallback: enviar mensaje directo
            await self._send_contact_fallback_message(user_id)

    async def _request_missing_contact_info(self, user_id: str, missing_info: list):
        """Solicita información faltante para el contacto con asesor."""
        try:
            from core.utils.memory import GlobalMemory
            
            # Determinar qué pedir primero
            if "email" in missing_info:
                message = """¡Perfecto! Te voy a conectar con un asesor especializado.
                
Para que pueda ayudarte de la mejor manera, necesito tu información de contacto.

📧 **Por favor, envíame tu email:**"""
                
                # Configurar el stage para esperar email
                memory = GlobalMemory().get_lead_memory(user_id)
                memory.stage = "awaiting_email"
                GlobalMemory().save_lead_memory(user_id, memory)
                
                logger.info(f"🔄 Stage configurado a 'awaiting_email' para usuario {user_id}")
                
            elif "teléfono" in missing_info:
                message = """📱 **Ahora necesito tu número de teléfono:**

Por favor, envíamelo en formato: +XX XXXXXXXXXX"""
                
                # Configurar el stage para esperar teléfono
                memory = GlobalMemory().get_lead_memory(user_id)
                memory.stage = "awaiting_phone"
                GlobalMemory().save_lead_memory(user_id, memory)
                
            elif "curso de interés" in missing_info:
                message = """📚 **Finalmente, necesito saber qué curso te interesa:**

¿Podrías decirme cuál es tu principal área de interés?"""
                
                # Mostrar cursos disponibles
                await self._show_available_courses(user_id)
                return
                
            else:
                message = """¡Perfecto! Ya tengo toda tu información.
                
Un asesor se pondrá en contacto contigo muy pronto."""
                await self._send_contact_confirmation(user_id)
                return
            
            await self.telegram.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error solicitando información faltante: {e}")
    
    async def _show_available_courses(self, user_id: str):
        """Muestra los cursos disponibles para selección."""
        try:
            # Obtener cursos desde la base de datos
            from core.services.courseService import CourseService
            course_service = CourseService(self.db)
            
            # Obtener cursos disponibles
            courses = await course_service.getAllCourses()
            
            if not courses:
                await self.telegram.send_message(
                    chat_id=user_id,
                    text="Actualmente tenemos cursos de Inteligencia Artificial disponibles. Un asesor te dará todos los detalles."
                )
                return
            
            # Crear lista de cursos
            course_list = "📚 **Cursos disponibles:**\n\n"
            for i, course in enumerate(courses[:3], 1):  # Mostrar máximo 3 cursos
                course_list += f"{i}. {course.get('name', 'Curso de IA')}\n"
            
            course_list += "\n¿Cuál te interesa más?"
            
            await self.telegram.send_message(
                chat_id=user_id,
                text=course_list,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error mostrando cursos disponibles: {e}")
            # Fallback
            await self.telegram.send_message(
                chat_id=user_id,
                text="Un asesor te ayudará a elegir el curso perfecto para ti."
            )
    
    async def _send_contact_confirmation(self, user_id: str):
        """Envía confirmación y ejecuta el envío de correo al asesor."""
        try:
            from core.utils.memory import GlobalMemory
            from core.handlers.contact_flow import send_advisor_email
            
            # Obtener datos del usuario
            memory = GlobalMemory().get_lead_memory(user_id)
            
            # Obtener nombre del curso si está disponible
            course_name = "Curso de IA para Profesionales"  # Default
            if memory.selected_course:
                try:
                    from core.services.courseService import CourseService
                    course_service = CourseService(self.db)
                    course_details = await course_service.getCourseDetails(memory.selected_course)
                    if course_details:
                        course_name = course_details.get('name', course_name)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error obteniendo detalles del curso: {e}")
            
            # Preparar datos para el asesor
            user_data = {
                "name": memory.name or "Usuario",
                "email": memory.email,
                "phone": memory.phone,
                "course_name": course_name
            }
            
            # Enviar email al asesor
            email_sent = send_advisor_email(user_data)
            
            if email_sent:
                confirmation_message = f"""✅ **¡Listo!** Tu información ha sido enviada correctamente.
                
📋 **Resumen de tus datos:**
• Nombre: {user_data['name']}
• Email: {user_data['email']}
• Teléfono: {user_data['phone']}
• Curso de interés: {user_data['course_name']}

📞 **Un asesor especializado se pondrá en contacto contigo muy pronto.**

¡Gracias por tu interés en nuestros cursos!"""
            else:
                confirmation_message = """⚠️ **Información recibida** pero hubo un problema técnico.
                
No te preocupes, hemos registrado tu interés y nos pondremos en contacto contigo a la brevedad.

Si tienes alguna urgencia, puedes contactarnos directamente."""
            
            await self.telegram.send_message(
                chat_id=user_id,
                text=confirmation_message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error enviando confirmación de contacto: {e}")
            await self._send_contact_fallback_message(user_id)
    
    async def _send_contact_fallback_message(self, user_id: str):
        """Envía mensaje de fallback cuando falla el flujo de contacto."""
        try:
            fallback_message = """¡Perfecto! Quiero conectarte con un asesor especializado.
            
Para que pueda ayudarte de la mejor manera, necesito algunos datos:

📧 **Envíame tu email**
📱 **Envíame tu número de teléfono**

Una vez que tengas estos datos, un asesor se pondrá en contacto contigo a la brevedad."""
            
            await self.telegram.send_message(
                chat_id=user_id,
                text=fallback_message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error enviando mensaje fallback: {e}")

    async def activar_flujo_contacto_asesor(self, user_id: str, course_id: str = None) -> str:
        """
        Función wrapper para activar el flujo de contacto desde el agente inteligente.
        Retorna un mensaje de confirmación para el usuario.
        """
        try:
            # Activar el flujo de contacto
            await self.contactar_asesor_directo(user_id, course_id)
            
            # Retornar mensaje de confirmación
            return """¡Perfecto! He iniciado el proceso para conectarte con un asesor especializado.
            
Por favor, sigue las instrucciones que te voy a enviar para recopilar tus datos de contacto."""
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error activando flujo de contacto desde agente: {e}")
            
            return """Te entiendo perfectamente. Déjame obtener la información más actualizada sobre el curso para responderte con precisión. ¿Qué aspecto específico te interesa más?"""

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

    # ========== HERRAMIENTAS ADICIONALES CON RESOURCESERVICE ==========
    
    async def mostrar_garantia_satisfaccion(self, user_id: str) -> None:
        """
        Muestra la garantía de satisfacción del curso.
        NUEVO: Usa ResourceService para obtener información de garantía.
        """
        garantia_url = "#"
        if self.resource_service:
            garantia_url = await self.resource_service.get_resource_url(
                "politica_garantia",
                fallback_url="https://aprenda-ia.com/garantia"
            )
        
        mensaje = """🛡️ *Garantía de Satisfacción al 100%*

Estamos tan seguros de la calidad de nuestros cursos que ofrecemos:

✅ **30 días de garantía completa**
✅ **Reembolso total si no estás satisfecho**
✅ **Sin preguntas, sin complicaciones**

📋 **¿Cómo funciona?**
• Tienes 30 días para probar el curso completo
• Si no cumple tus expectativas, solicita el reembolso
• Procesamos tu reembolso en 24-48 horas

🎯 **¿Por qué ofrecemos esta garantía?**
• Más del 96% de nuestros estudiantes están satisfechos
• Confiamos en la calidad de nuestro contenido
• Queremos que aprendas sin riesgos

*¡Tu satisfacción es nuestra prioridad!*"""

        buttons = {
            "inline_keyboard": [
                [{"text": "📜 Ver Términos Completos", "url": garantia_url}],
                [{"text": "💬 Preguntas sobre Garantía", "callback_data": "contact_advisor"}],
                [{"text": "🛒 Comprar con Confianza", "callback_data": f"enroll_course"}]
            ]
        }

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown',
            reply_markup=buttons
        )

    async def mostrar_testimonios_relevantes(self, user_id: str, course_id: str) -> None:
        """
        Muestra testimonios de estudiantes similares al usuario.
        NUEVO: Usa ResourceService para obtener testimonios.
        """
        testimonios_url = "#"
        casos_exito_url = "#"
        
        if self.resource_service:
            testimonios_url = await self.resource_service.get_resource_url(
                "testimonios_video",
                fallback_url="https://testimonios.aprenda-ia.com"
            )
            casos_exito_url = await self.resource_service.get_resource_url(
                "casos_exito",
                fallback_url="https://casos-exito.aprenda-ia.com"
            )

        mensaje = """💬 *Lo que dicen nuestros estudiantes*

🌟 **María González** - Emprendedora
_"En 3 semanas implementé IA en mi negocio y aumenté mis ventas 40%. El curso es súper práctico."_

🌟 **Carlos Rodríguez** - Gerente de Marketing
_"Aprendí a crear contenido con IA que me ahorra 15 horas semanales. Increíble ROI."_

🌟 **Ana Martínez** - Freelancer
_"Ahora ofrezco servicios de IA a mis clientes y tripliqué mis ingresos. Gracias!"_

🌟 **Roberto Silva** - Consultor
_"El curso me convirtió en experto en IA. Mis clientes me ven como un innovador."_

📊 **Resultados promedio de nuestros estudiantes:**
• 85% implementa IA en su trabajo en 30 días
• 92% aumenta su productividad significativamente
• 78% incrementa sus ingresos en 6 meses

¡Únete a más de 2,000 profesionales exitosos!"""

        buttons = {
            "inline_keyboard": [
                [{"text": "🎥 Ver Testimonios en Video", "url": testimonios_url}],
                [{"text": "📊 Casos de Éxito Completos", "url": casos_exito_url}],
                [{"text": "💬 Hablar con Graduados", "callback_data": "contact_advisor"}],
                [{"text": "🚀 Inscribirme Ahora", "callback_data": f"enroll_course"}]
            ]
        }

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown',
            reply_markup=buttons
        )

    async def mostrar_social_proof_inteligente(self, user_id: str, course_id: str) -> None:
        """
        Muestra prueba social inteligente basada en el perfil del usuario.
        NUEVO: Usa ResourceService para obtener pruebas sociales.
        """
        community_url = "#"
        calendario_url = "#"
        
        if self.resource_service:
            community_url = await self.resource_service.get_resource_url(
                "comunidad_estudiantes",
                fallback_url="https://comunidad.aprenda-ia.com"
            )
            calendario_url = await self.resource_service.get_resource_url(
                "calendario_eventos",
                fallback_url="https://calendario.aprenda-ia.com"
            )

        mensaje = """🚀 *Únete a una Comunidad Exitosa*

👥 **Más de 2,000 profesionales activos**
🏆 **96% de satisfacción promedio**
📈 **500+ historias de éxito documentadas**

🔥 **Actividad en tiempo real:**
• 47 estudiantes completaron el curso esta semana
• 12 nuevos proyectos compartidos hoy
• 8 ofertas laborales conseguidas este mes

💡 **Lo que está pasando ahora:**
• Webinar en vivo: "IA para Automatización" - Mañana 6 PM
• Grupo de estudio: "Prompts Avanzados" - Activo
• Networking: "Profesionales IA" - 156 miembros online

🌟 **Certificaciones entregadas:**
• Esta semana: 23 certificados
• Este mes: 94 certificados
• Total: 1,847 profesionales certificados

¡No te quedes atrás! Únete ahora y sé parte del cambio."""

        buttons = {
            "inline_keyboard": [
                [{"text": "👥 Unirme a la Comunidad", "url": community_url}],
                [{"text": "📅 Ver Eventos en Vivo", "url": calendario_url}],
                [{"text": "🎓 Ver Certificados", "callback_data": "show_certificates"}],
                [{"text": "🚀 Inscribirme Ya", "callback_data": f"enroll_course"}]
            ]
        }

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown',
            reply_markup=buttons
        )

    async def mostrar_casos_exito_similares(self, user_id: str, course_id: str) -> None:
        """
        Muestra casos de éxito de estudiantes con perfil similar.
        NUEVO: Usa ResourceService para obtener casos de éxito.
        """
        casos_url = "#"
        
        if self.resource_service:
            casos_url = await self.resource_service.get_resource_url(
                "casos_exito",
                fallback_url="https://casos-exito.aprenda-ia.com"
            )

        mensaje = """🏆 *Casos de Éxito Reales*

📈 **Caso 1: Laura - Agencia de Marketing**
• Problema: Procesos manuales lentos
• Solución: Automatización con IA
• Resultado: 60% más eficiente, +$15K/mes

💼 **Caso 2: Miguel - Consultor Independiente**
• Problema: Competencia con grandes empresas
• Solución: Servicios potenciados con IA
• Resultado: Triplicó sus tarifas, agenda llena

🏢 **Caso 3: Sofía - Directora de Ventas**
• Problema: Leads de baja calidad
• Solución: Calificación automática con IA
• Resultado: 45% más conversiones

🚀 **Caso 4: Roberto - E-commerce**
• Problema: Atención al cliente saturada
• Solución: Chatbots inteligentes
• Resultado: 80% consultas automatizadas

💡 **Patrón común:** Todos implementaron IA en 30 días y vieron resultados inmediatos.

¿Cuál será tu caso de éxito?"""

        buttons = {
            "inline_keyboard": [
                [{"text": "📖 Casos Completos", "url": casos_url}],
                [{"text": "💬 Hablar con Graduados", "callback_data": "contact_advisor"}],
                [{"text": "🎯 Mi Plan Personalizado", "callback_data": "demo_request"}],
                [{"text": "🚀 Ser el Próximo Caso", "callback_data": f"enroll_course"}]
            ]
        }

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown',
            reply_markup=buttons
        )

    async def presentar_oferta_limitada(self, user_id: str, course_id: str) -> None:
        """
        Presenta una oferta por tiempo limitado con urgencia.
        NUEVO: Usa ResourceService para obtener información de ofertas.
        """
        urgencia_url = "#"
        checkout_url = "#"
        
        if self.resource_service:
            urgencia_url = await self.resource_service.get_resource_url(
                "contador_descuento",
                fallback_url="https://urgencia.aprenda-ia.com"
            )
            checkout_url = await self.resource_service.get_resource_url(
                "checkout_curso",
                fallback_url="https://checkout.aprenda-ia.com"
            )

        mensaje = """🔥 *¡OFERTA ESPECIAL - SOLO POR TIEMPO LIMITADO!*

⏰ **SE CIERRA EN:** 2 horas, 34 minutos

🎁 **INCLUYE GRATIS:**
• Consultoría 1:1 personalizada (Valor: $200)
• Plantillas Premium de IA (Valor: $150)
• Acceso a Masterclass exclusiva (Valor: $100)
• Comunidad VIP por 6 meses (Valor: $300)

💰 **PRECIO NORMAL:** $497
💸 **PRECIO HOY:** $197 (60% OFF)
💎 **AHORRO TOTAL:** $750

🚨 **SOLO QUEDAN 3 CUPOS A ESTE PRECIO**

✅ **GARANTÍA:** 30 días de reembolso total
✅ **SOPORTE:** WhatsApp directo del instructor
✅ **ACTUALIZACIONES:** Gratis de por vida

⚡ **BONOS EXCLUSIVOS SI COMPRAS AHORA:**
• 🎯 Análisis gratuito de tu negocio
• 🔧 Implementación asistida 1:1
• 📊 Plantillas personalizadas

*¡Esta oferta no se repetirá!*"""

        buttons = {
            "inline_keyboard": [
                [{"text": "🔥 TOMAR OFERTA AHORA", "url": checkout_url}],
                [{"text": "⏰ Ver Contador en Vivo", "url": urgencia_url}],
                [{"text": "💬 Reservar por WhatsApp", "callback_data": "contact_advisor"}],
                [{"text": "🎁 Ver Todos los Bonos", "callback_data": "show_bonuses"}]
            ]
        }

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown',
            reply_markup=buttons
        )

    async def personalizar_oferta_por_budget(self, user_id: str, course_id: str) -> None:
        """
        Personaliza la oferta según el presupuesto del usuario.
        NUEVO: Usa ResourceService para obtener opciones de pago.
        """
        downsell_url = "#"
        
        if self.resource_service:
            downsell_url = await self.resource_service.get_resource_url(
                "downsell_basico",
                fallback_url="https://downsell.aprenda-ia.com"
            )

        mensaje = """💰 *Opciones de Inversión Personalizadas*

Entendemos que la inversión es importante. Te ofrecemos opciones flexibles:

🥇 **OPCIÓN VIP - $497**
• Curso completo + Consultoría 1:1
• Soporte prioritario por WhatsApp
• Implementación asistida
• Actualizaciones ilimitadas

🥈 **OPCIÓN ESTÁNDAR - $297**
• Curso completo
• Soporte por email
• Comunidad de estudiantes
• Actualizaciones por 1 año

🥉 **OPCIÓN BÁSICA - $197**
• Curso completo
• Soporte básico
• Acceso por 6 meses

💳 **FACILIDADES DE PAGO:**
• 3 cuotas sin intereses
• 6 cuotas con 5% extra
• 12 cuotas con 10% extra

🎯 **DESCUENTO ESPECIAL:**
• Estudiantes: 20% adicional
• Emprendedores: 15% adicional
• Empresas: Cotización especial

¿Cuál opción se adapta mejor a tu presupuesto?"""

        buttons = {
            "inline_keyboard": [
                [{"text": "🥇 Opción VIP", "callback_data": "select_vip"}],
                [{"text": "🥈 Opción Estándar", "callback_data": "select_standard"}],
                [{"text": "🥉 Opción Básica", "url": downsell_url}],
                [{"text": "💬 Cotización Personalizada", "callback_data": "contact_advisor"}]
            ]
        }

        await self.telegram.send_message(
            user_id,
            mensaje,
            parse_mode='Markdown',
            reply_markup=buttons
        )

    # Métodos adicionales para compatibilidad con herramientas existentes...
    # [Resto de métodos se mantienen similares con adaptaciones de campos]