"""
Plantillas centralizadas para mostrar información de cursos - VERSIÓN MIGRADA.
Todas las plantillas construyen la información dinámicamente desde la nueva estructura de base de datos.
Compatibles con ai_courses, ai_course_sessions, ai_session_practices, ai_session_deliverables.
"""

class CourseTemplates:
    """Plantillas para mostrar información de cursos de manera consistente - VERSIÓN MIGRADA."""
    
    @staticmethod
    def format_course_info(course_details: dict) -> str:
        """
        Formatea la información completa del curso para mostrar al usuario.
        MIGRADO: Usa campos de ai_courses con conversión robusta de tipos
        """
        name = course_details.get('name', 'Dato no encontrado')
        description = course_details.get('short_description', 'Dato no encontrado')
        
        # Cambios en nueva estructura: total_duration_min en lugar de total_duration
        # CORREGIDO: Manejo robusto de tipos string/int
        duration_min_raw = course_details.get('total_duration_min', 0)
        try:
            # Convertir a int sin importar si es string o int
            duration_min = int(duration_min_raw) if duration_min_raw else 0
            if duration_min > 0:
                hours = duration_min // 60
                minutes = duration_min % 60
                duration = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            else:
                duration = "dato no encontrado"
        except (ValueError, TypeError):
            duration = "dato no encontrado"
        
        level = course_details.get('level', 'dato no encontrado')
        
        # Cambios en nueva estructura: price en lugar de price_usd
        # CORREGIDO: Manejo robusto de tipos string/int para price
        price_raw = course_details.get('price', 0)
        try:
            # Convertir a float sin importar si es string o number
            price = float(price_raw) if price_raw else 0
            currency = course_details.get('currency', 'USD')
            # Formatear precio sin decimales innecesarios
            price_formatted = f"{price:.0f}" if price == int(price) else f"{price:.2f}"
            price_str = f"{price_formatted} {currency}" if price > 0 else "dato no encontrado"
        except (ValueError, TypeError):
            price_str = "dato no encontrado"
        
        # Extraer sesiones de la nueva estructura
        sessions_text = ""
        sessions = course_details.get('sessions', [])
        if sessions and isinstance(sessions, list):
            sessions_text = "\n\n📚 **Sesiones del curso:**\n"
            for i, session in enumerate(sessions[:5], 1):  # Mostrar máximo 5 sesiones
                session_title = session.get('title', f'Sesión {i}')
                sessions_text += f"{i}. {session_title}\n"
        
        return f"""🎓 **{name}**

{description}

⏱️ **Duración:** {duration}
📊 **Nivel:** {level}
💰 **Inversión:** ${price_str}
{sessions_text}

¿Qué te gustaría saber más sobre este curso?"""

    @staticmethod
    def format_course_summary(course_details: dict) -> str:
        """
        Formatea un resumen básico del curso.
        MIGRADO: Usa campos de ai_courses con conversión robusta de tipos
        """
        name = course_details.get('name', 'Dato no encontrado')
        description = course_details.get('short_description', 'Dato no encontrado')
        
        # Cambios en nueva estructura - CORREGIDO: Manejo robusto de tipos
        price_raw = course_details.get('price', 0)
        try:
            price = float(price_raw) if price_raw else 0
            currency = course_details.get('currency', 'USD')
            # Formatear precio sin decimales innecesarios
            price_formatted = f"{price:.0f}" if price == int(price) else f"{price:.2f}"
            price_str = f"{price_formatted} {currency}" if price > 0 else "dato no encontrado"
        except (ValueError, TypeError):
            price_str = "dato no encontrado"
        
        return f"""🎯 **{name}**

{description}

💰 **Inversión:** ${price_str}"""

    @staticmethod
    def format_course_welcome(course_details: dict, user_name: str) -> str:
        """
        Formatea el mensaje de bienvenida personalizado con información del curso.
        MIGRADO: Usa campos de ai_courses
        """
        name = course_details.get('name', 'Dato no encontrado')
        description = course_details.get('short_description', 'Dato no encontrado')
        
        return f"""¡Hola {user_name}! 😊 

Soy Brenda de **Aprenda y Aplique IA** 🤖✨

Me da muchísimo gusto que te interese nuestro curso:

🎓 **{name}**

{description}

Te voy a compartir el programa completo del curso y algunos materiales para que veas todo lo que vas a aprender 📚"""

    @staticmethod
    def format_course_details_with_benefits(course_details: dict) -> str:
        """
        Formatea información detallada del curso con beneficios.
        MIGRADO: Usa campos de ai_courses y ai_subthemes con conversión robusta de tipos
        """
        name = course_details.get('name', 'Dato no encontrado')
        description = course_details.get('short_description', 'Dato no encontrado')
        
        # Cambios en nueva estructura - CORREGIDO: Manejo robusto de tipos
        duration_min_raw = course_details.get('total_duration_min', 0)
        try:
            duration_min = int(duration_min_raw) if duration_min_raw else 0
            if duration_min > 0:
                hours = duration_min // 60
                minutes = duration_min % 60
                duration = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            else:
                duration = "dato no encontrado"
        except (ValueError, TypeError):
            duration = "dato no encontrado"
        
        level = course_details.get('level', 'dato no encontrado')
        
        price_raw = course_details.get('price', 0)
        try:
            price = float(price_raw) if price_raw else 0
            currency = course_details.get('currency', 'USD')
            # Formatear precio sin decimales innecesarios
            price_formatted = f"{price:.0f}" if price == int(price) else f"{price:.2f}"
            price_str = f"{price_formatted} {currency}" if price > 0 else "dato no encontrado"
        except (ValueError, TypeError):
            price_str = "dato no encontrado"
        
        # Información del subtema (nueva funcionalidad)
        subtheme_text = ""
        if course_details.get('subtheme_name'):
            subtheme_text = f"🎯 **Categoría:** {course_details['subtheme_name']}\n"
        
        # Conteo de sesiones (nueva funcionalidad)
        session_count_raw = course_details.get('session_count', 0)
        try:
            session_count = int(session_count_raw) if session_count_raw else 0
            session_text = f"📚 **Sesiones:** {session_count}\n" if session_count > 0 else ""
        except (ValueError, TypeError):
            session_text = ""
        
        return f"""🎓 **{name}**

{description}

{subtheme_text}{session_text}⏱️ **Duración:** {duration}
📊 **Nivel:** {level}
💰 **Inversión:** ${price_str}

✨ **¿Por qué este curso te va a cambiar la vida?**
• Aprenderás habilidades que están transformando el mundo laboral
• Automatizarás tareas repetitivas y ahorrarás horas de trabajo
• Te convertirás en un profesional más competitivo y valioso
• Tendrás acceso a herramientas que la mayoría no sabe usar

¿Te gustaría saber cómo este curso puede transformar específicamente tu carrera?"""

    @staticmethod
    def format_course_modules_detailed(course_details: dict) -> str:
        """
        Formatea las sesiones del curso de manera detallada.
        MIGRADO: Usa ai_course_sessions en lugar de course_modules
        """
        name = course_details.get('name', 'Dato no encontrado')
        sessions = course_details.get('sessions', [])
        
        sessions_text = "📚 **Sesiones del curso:**\n\n"
        
        if sessions and isinstance(sessions, list):
            for i, session in enumerate(sessions, 1):
                session_title = session.get('title', f'Sesión {i}')
                session_objective = session.get('objective', 'Objetivo no especificado')
                session_duration_raw = session.get('duration_minutes', 0)
                
                # Manejo robusto de duration_minutes
                try:
                    session_duration = int(session_duration_raw) if session_duration_raw else 0
                    duration_text = f" ({session_duration} min)" if session_duration > 0 else ""
                except (ValueError, TypeError):
                    duration_text = ""
                
                sessions_text += f"**{i}. {session_title}**{duration_text}\n"
                sessions_text += f"   {session_objective}\n\n"
        else:
            sessions_text = "dato no encontrado"
        
        return f"""🎓 **{name}**

{sessions_text}

¿Cuál de estas sesiones te emociona más? 🚀"""

    @staticmethod
    def format_course_pricing(course_details: dict) -> str:
        """
        Formatea información de precios.
        MIGRADO: Campos de descuento eliminados en nueva estructura con conversión robusta
        """
        name = course_details.get('name', 'Dato no encontrado')
        
        # Manejo robusto del precio
        price_raw = course_details.get('price', 0)
        try:
            price = float(price_raw) if price_raw else 0
            currency = course_details.get('currency', 'USD')
            price_formatted = f"{price:.0f}" if price == int(price) else f"{price:.2f}"
            price_str = f"{price_formatted} {currency}" if price > 0 else "dato no encontrado"
        except (ValueError, TypeError):
            price_str = "dato no encontrado"
        
        # Información adicional de la nueva estructura con manejo robusto
        session_count_raw = course_details.get('session_count', 0)
        try:
            session_count = int(session_count_raw) if session_count_raw else 0
            session_text = f"• {session_count} sesiones completas\n" if session_count > 0 else ""
        except (ValueError, TypeError):
            session_text = ""
        
        duration_min_raw = course_details.get('total_duration_min', 0)
        try:
            duration_min = int(duration_min_raw) if duration_min_raw else 0
            duration_text = f"• {duration_min} minutos de contenido\n" if duration_min > 0 else ""
        except (ValueError, TypeError):
            duration_text = ""
        
        return f"""🎓 **{name}**

💰 **Inversión:** ${price_str}

✨ **¿Qué incluye tu inversión?**
{session_text}{duration_text}• Acceso completo al curso por tiempo ilimitado
• Certificado al completar el programa
• Soporte directo con instructores
• Comunidad privada de estudiantes
• Actualizaciones gratuitas del contenido

¿Te gustaría conocer las opciones de pago disponibles?"""

    @staticmethod
    def format_session_detail(session_details: dict) -> str:
        """
        Formatea información detallada de una sesión específica.
        NUEVO: Funcionalidad agregada para nueva estructura con manejo robusto
        """
        title = session_details.get('title', 'Sesión sin título')
        objective = session_details.get('objective', 'Objetivo no especificado')
        duration_minutes_raw = session_details.get('duration_minutes', 0)
        modality = session_details.get('modality', 'online')
        
        # Manejo robusto de duration_minutes
        try:
            duration_minutes = int(duration_minutes_raw) if duration_minutes_raw else 0
            duration_text = f"{duration_minutes} minutos" if duration_minutes > 0 else "Duración no especificada"
        except (ValueError, TypeError):
            duration_text = "Duración no especificada"
        
        return f"""📖 **{title}**

🎯 **Objetivo:** {objective}

⏱️ **Duración:** {duration_text}
📱 **Modalidad:** {modality}

¿Te gustaría ver las prácticas y entregables de esta sesión?"""

    @staticmethod
    def format_subtheme_info(subtheme_details: dict) -> str:
        """
        Formatea información de un subtema.
        NUEVO: Funcionalidad agregada para nueva estructura
        """
        name = subtheme_details.get('name', 'Subtema sin nombre')
        description = subtheme_details.get('description', 'Descripción no disponible')
        
        return f"""🎯 **Categoría: {name}**

{description}

¿Te gustaría ver todos los cursos de esta categoría?"""

    @staticmethod
    def format_error_message(course_id: str) -> str:
        """
        Formatea mensaje de error cuando no se puede obtener información del curso.
        MANTENIDO: Sin cambios
        """
        return f"""❌ **Error al obtener información del curso**

Lo siento, no pude obtener los detalles del curso desde la base de datos.
ID del curso: {course_id}

Por favor, intenta nuevamente o contacta a nuestro equipo de soporte.

¿Te gustaría que te ayude con algo más?"""

    @staticmethod
    def _extract_sessions_from_data(course_data: dict) -> list:
        """
        Extrae sesiones de los datos del curso.
        MIGRADO: Usa sessions en lugar de modules
        """
        sessions = course_data.get('sessions', [])
        if not sessions:
            return []
        
        session_list = []
        for session in sessions:
            if isinstance(session, dict):
                session_title = session.get('title', 'Sesión sin título')
                session_objective = session.get('objective', '')
                if session_title and len(session_title) > 5:
                    session_list.append({
                        'title': session_title,
                        'objective': session_objective
                    })
        
        return session_list[:10]  # Máximo 10 sesiones