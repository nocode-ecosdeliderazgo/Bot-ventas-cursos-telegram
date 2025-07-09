"""
Plantillas centralizadas para mostrar información de cursos.
Todas las plantillas construyen la información dinámicamente desde la base de datos.
"""

class CourseTemplates:
    """Plantillas para mostrar información de cursos de manera consistente."""
    
    @staticmethod
    def format_course_info(course_details: dict) -> str:
        """Formatea la información completa del curso para mostrar al usuario."""
        name = course_details.get('name', 'Dato no encontrado en la base de datos')
        description = course_details.get('short_description', 'Dato no encontrado en la base de datos')
        duration = course_details.get('total_duration', 'Dato no encontrado en la base de datos')
        level = course_details.get('level', 'Dato no encontrado en la base de datos')
        price = course_details.get('price_usd', 'Dato no encontrado en la base de datos')
        
        # Extraer módulos de la descripción larga si existe
        modules_text = ""
        long_desc = course_details.get('long_description', '')
        if long_desc:
            modules = CourseTemplates._extract_modules_from_description(long_desc)
            if modules:
                modules_text = "\n\n📚 **Módulos del curso:**\n"
                for i, module in enumerate(modules[:5], 1):  # Mostrar máximo 5 módulos
                    modules_text += f"{i}. {module}\n"
        
        return f"""🎓 **{name}**

{description}

⏱️ **Duración:** {duration}
📊 **Nivel:** {level}
💰 **Inversión:** ${price} USD
{modules_text}

¿Qué te gustaría saber más sobre este curso?"""

    @staticmethod
    def format_course_summary(course_details: dict) -> str:
        """Formatea un resumen básico del curso."""
        name = course_details.get('name', 'Dato no encontrado en la base de datos')
        description = course_details.get('short_description', 'Dato no encontrado en la base de datos')
        price = course_details.get('price_usd', 'Dato no encontrado en la base de datos')
        
        return f"""🎯 **{name}**

{description}

💰 **Inversión:** ${price} USD"""

    @staticmethod
    def format_course_welcome(course_details: dict, user_name: str) -> str:
        """Formatea el mensaje de bienvenida personalizado con información del curso."""
        name = course_details.get('name', 'Dato no encontrado en la base de datos')
        description = course_details.get('short_description', 'Dato no encontrado en la base de datos')
        
        return f"""¡Hola {user_name}! 😊 

Soy Brenda de **Aprenda y Aplique IA** 🤖✨

Me da muchísimo gusto que te interese nuestro curso:

🎓 **{name}**

{description}

Te voy a compartir el programa completo del curso y algunos materiales para que veas todo lo que vas a aprender 📚"""

    @staticmethod
    def format_course_details_with_benefits(course_details: dict) -> str:
        """Formatea información detallada del curso con beneficios."""
        name = course_details.get('name', 'Dato no encontrado en la base de datos')
        description = course_details.get('short_description', 'Dato no encontrado en la base de datos')
        duration = course_details.get('total_duration', 'Dato no encontrado en la base de datos')
        level = course_details.get('level', 'Dato no encontrado en la base de datos')
        price = course_details.get('price_usd', 'Dato no encontrado en la base de datos')
        tools = course_details.get('tools_used', [])
        
        tools_text = ""
        if tools and isinstance(tools, list):
            tools_text = "\n\n🛠️ **Herramientas que usarás:**\n"
            for tool in tools[:5]:  # Mostrar máximo 5 herramientas
                tools_text += f"• {tool}\n"
        
        return f"""🎓 **{name}**

{description}

⏱️ **Duración:** {duration}
📊 **Nivel:** {level}
💰 **Inversión:** ${price} USD
{tools_text}

✨ **¿Por qué este curso te va a cambiar la vida?**
• Aprenderás habilidades que están transformando el mundo laboral
• Automatizarás tareas repetitivas y ahorrarás horas de trabajo
• Te convertirás en un profesional más competitivo y valioso
• Tendrás acceso a herramientas que la mayoría no sabe usar

¿Te gustaría saber cómo este curso puede transformar específicamente tu carrera?"""

    @staticmethod
    def format_course_modules_detailed(course_details: dict) -> str:
        """Formatea los módulos del curso de manera detallada."""
        name = course_details.get('name', 'Dato no encontrado en la base de datos')
        long_desc = course_details.get('long_description', '')
        
        modules_text = "📚 **Módulos del curso:**\n\n"
        
        if long_desc:
            modules = CourseTemplates._extract_modules_from_description(long_desc)
            if modules:
                for i, module in enumerate(modules, 1):
                    modules_text += f"**{i}. {module}**\n\n"
            else:
                modules_text = "Dato no encontrado en la base de datos"
        else:
            modules_text = "Dato no encontrado en la base de datos"
        
        return f"""🎓 **{name}**

{modules_text}

¿Cuál de estos módulos te emociona más? 🚀"""

    @staticmethod
    def format_course_pricing(course_details: dict) -> str:
        """Formatea información de precios y ofertas."""
        name = course_details.get('name', 'Dato no encontrado en la base de datos')
        price = course_details.get('price_usd', 'Dato no encontrado en la base de datos')
        original_price = course_details.get('original_price_usd', price)
        discount = course_details.get('discount_percentage', 0)
        
        pricing_text = f"💰 **Inversión:** ${price} USD"
        
        if original_price != price and discount > 0:
            pricing_text = f"""💰 **Precio regular:** ~~${original_price} USD~~
🎯 **Precio especial:** ${price} USD ({discount}% de descuento)"""
        
        return f"""🎓 **{name}**

{pricing_text}

✨ **¿Qué incluye tu inversión?**
• Acceso completo al curso por tiempo ilimitado
• Certificado al completar el programa
• Soporte directo con instructores
• Comunidad privada de estudiantes
• Actualizaciones gratuitas del contenido

¿Te gustaría conocer las opciones de pago disponibles?"""

    @staticmethod
    def _extract_modules_from_description(long_description: str) -> list:
        """Extrae módulos específicos de la descripción larga del curso."""
        modules = []
        
        # Buscar patrones específicos del curso de IA
        lines = long_description.split('\n')
        for line in lines:
            line = line.strip()
            # Buscar líneas que contengan módulos específicos
            if ':' in line and any(keyword in line.lower() for keyword in [
                'chatgpt', 'documento', 'imagen', 'proyecto', 'creación', 'generación'
            ]):
                # Limpiar la línea y extraer el módulo
                module = line.split(':')[0].strip()
                if module and len(module) > 5:  # Evitar módulos muy cortos
                    modules.append(module)
        
        return modules[:5]  # Máximo 5 módulos

    @staticmethod
    def format_error_message(course_id: str) -> str:
        """Formatea mensaje de error cuando no se puede obtener información del curso."""
        return f"""❌ **Error al obtener información del curso**

Lo siento, no pude obtener los detalles del curso desde la base de datos.
ID del curso: {course_id}

Por favor, intenta nuevamente o contacta a nuestro equipo de soporte.

¿Te gustaría que te ayude con algo más?"""