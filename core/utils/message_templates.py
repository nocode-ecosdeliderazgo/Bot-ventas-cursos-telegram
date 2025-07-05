"""
Plantillas de mensajes para diferentes estrategias de venta y situaciones.
Incluye mensajes personalizados según el contexto y nivel de interés del usuario.
"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

def create_menu_message() -> str:
    """Crea el mensaje del menú principal."""
    return """¡Bienvenido al Bot de Ventas! 🤖

¿En qué puedo ayudarte hoy?

🎓 Ver cursos disponibles
📱 Contactar con un asesor
❓ Preguntas frecuentes
🔒 Política de privacidad"""

def create_menu_keyboard() -> InlineKeyboardMarkup:
    """Crea el teclado del menú principal."""
    keyboard = [
        [InlineKeyboardButton("🎓 Ver Cursos", callback_data="menu_courses")],
        [InlineKeyboardButton("📱 Contactar Asesor", callback_data="menu_contact")],
        [InlineKeyboardButton("❓ FAQ", callback_data="menu_faq")],
        [InlineKeyboardButton("🔒 Privacidad", callback_data="menu_privacy")]
    ]
    return InlineKeyboardMarkup(keyboard)

class MessageTemplates:
    """
    Plantillas de mensajes optimizadas para conversión y experiencia del usuario.
    """
    
    def __init__(self):
        self.emoji_map = {
            'success': '🎉',
            'info': 'ℹ️',
            'warning': '⚠️',
            'urgent': '🚨',
            'money': '💰',
            'time': '⏰',
            'rocket': '🚀',
            'star': '⭐',
            'fire': '🔥',
            'light': '💡',
            'heart': '❤️',
            'check': '✅'
        }

    def get_privacy_notice_message(self, user_name: str = "amigo") -> str:
        """
        Mensaje de aviso de privacidad cálido y profesional.
        """
        return f"""¡Hola {user_name}! 👋 

Soy Brenda, tu asesora especializada en cursos de Inteligencia Artificial. Me da mucho gusto conectar contigo.

Para poder brindarte la mejor experiencia personalizada, necesito tu consentimiento para:

📋 **Procesar tus datos personales** (nombre, preferencias de comunicación)
📞 **Contactarte** con información relevante sobre nuestros cursos
📊 **Personalizar** las recomendaciones según tus intereses

🔒 **Tu privacidad es importante:** Cumplimos con todas las normativas de protección de datos y nunca compartiremos tu información con terceros.

¿Estás de acuerdo con continuar? ¡Te aseguro que valdrá la pena! 😊"""

    def get_name_request_message(self, user_name: str = "") -> str:
        """
        Solicitud de nombre de manera cálida y personal.
        """
        greeting = f"Perfecto, {user_name}!" if user_name else "¡Perfecto!"
        
        return f"""{greeting} 

Para hacer nuestra conversación más personal y poder ayudarte mejor, me encantaría saber...

**¿Cómo te gusta que te llamen?** 

Puede ser tu nombre, apodo, o como prefieras que me dirija a ti. ¡Quiero que te sientas cómodo/a! 😊

Solo escríbeme y continuamos con toda la información del curso que te interesa."""

    def get_course_presentation_message(self, user_name: str, course_info: Dict) -> str:
        """
        Presentación inicial del curso con información clave.
        """
        return f"""¡Excelente, {user_name}! 🎯

Te voy a enviar ahora mismo toda la información del curso que viste en el anuncio. ¡Estoy segura de que te va a encantar!

**{course_info.get('name', 'Curso de IA')}** ⭐

{course_info.get('description', 'Un curso transformador que cambiará tu perspectiva profesional')}

📊 **Detalles importantes:**
• **Modalidad:** {course_info.get('modality', 'Online')}
• **Duración:** {course_info.get('duration', '12 horas')}
• **Horario:** {course_info.get('schedule', 'Flexible')}
• **Inversión:** ${course_info.get('price', 120)} USD
• **Incluye:** Material completo, certificación y soporte

{user_name}, este curso está diseñado específicamente para personas como tú que quieren dominar la IA y llevar su carrera al siguiente nivel.

¿Qué te gustaría saber primero? 👇"""

    def get_immediate_close_message(self, user_name: str) -> str:
        """
        Mensaje para cerrar la venta cuando hay alta intención de compra.
        """
        return f"""¡{user_name}, me encanta tu decisión! 🚀

Veo que estás listo/a para transformar tu carrera con la Inteligencia Artificial. ¡Es exactamente la actitud que necesitas para tener éxito!

🎯 **¿Por qué es el momento perfecto?**
• Las plazas son limitadas (solo quedan 8 lugares)
• Inicio confirmado: Próximo viernes
• Grupo pequeño para atención personalizada
• Acceso inmediato a la comunidad exclusiva

💡 **Bonus por decidir hoy:**
• Sesión 1-on-1 con el instructor
• Plantillas y recursos adicionales
• Acceso de por vida a actualizaciones

¡No esperes más, {user_name}! Este es TU momento. 💪"""

    def get_urgency_close_message(self, user_name: str) -> str:
        """
        Mensaje que crea urgencia para cerrar la venta.
        """
        return f"""¡{user_name}, tengo noticias importantes! ⏰

Acabo de revisar la disponibilidad del curso y queda **muy poco tiempo** para asegurar tu lugar:

🔥 **Situación actual:**
• Solo quedan **6 lugares disponibles**
• Cierre de inscripciones: **Mañana a las 6 PM**
• Siguiente grupo: **No confirmado aún**

💰 **Oferta especial de último momento:**
• 20% de descuento (válido solo por hoy)
• Plan de pagos sin intereses
• Garantía de satisfacción 100%

{user_name}, he visto a muchas personas perder oportunidades como esta por "pensarlo un poco más". No dejes que te pase a ti.

**¿Aseguramos tu lugar ahora?** 🚀"""

    def get_urgency_with_promotion_message(self, user_name: str, promotion: Dict) -> str:
        """
        Mensaje de urgencia con promoción activa.
        """
        return f"""🎉 ¡{user_name}, es tu día de suerte!

Justo ahora tenemos una **promoción especial** que termina en pocas horas:

🔥 **{promotion.get('name', 'Oferta Especial')}**
• **Descuento:** {promotion.get('discount', '25')}%
• **Precio normal:** ${promotion.get('original_price', 150)}
• **Precio con descuento:** ${promotion.get('discounted_price', 120)}
• **Termina:** {promotion.get('expires', 'Hoy a medianoche')}

💡 **¡Pero eso no es todo!** También incluye:
• Acceso anticipado al material
• Sesión bonus de Q&A
• Certificado premium
• Garantía extendida

{user_name}, esta combinación de precio + bonos no se va a repetir. Es literalmente la mejor oferta del año.

**¿Aprovechamos esta oportunidad única?** ⚡"""

    def get_value_building_message(self, user_name: str) -> str:
        """
        Mensaje que construye valor del curso.
        """
        return f"""Perfecto, {user_name}! Me encanta que quieras conocer más detalles 📊

Este curso no es solo "otro curso de IA". Es una **transformación completa** de tu forma de trabajar:

💼 **Valor profesional real:**
• Aumenta tu productividad hasta 400%
• Habilidades demandadas por empresas Fortune 500
• Salario promedio: +$15,000 USD anuales

🎯 **Metodología probada:**
• Casos reales de empresas exitosas
• Práctica desde la primera clase
• Proyectos para tu portafolio
• Mentoría personalizada

⭐ **Resultados de nuestros estudiantes:**
• 94% consigue mejor empleo en 6 meses
• 87% inicia proyecto propio exitoso
• 100% recomienda el curso

{user_name}, no estás comprando un curso... estás invirtiendo en tu futuro profesional.

¿Qué aspecto te interesa más explorar? 🚀"""

    def get_nurture_message(self, user_name: str) -> str:
        """
        Mensaje para nutrir el interés cuando es bajo.
        """
        return f"""Hola {user_name}, entiendo perfectamente 😊

Sé que tomar la decisión de invertir en tu educación no es algo que se hace a la ligera. ¡Y eso habla muy bien de ti!

🤔 **Es normal tener dudas como:**
• "¿Realmente es para mí?"
• "¿Tendré tiempo?"
• "¿Vale la pena la inversión?"

💡 **Por eso quiero ayudarte** a tomar la mejor decisión, sin presión:

Te puedo compartir contenido gratuito, historias de éxito de personas en tu situación, o simplemente resolver todas tus dudas.

Mi trabajo es asegurarme de que tengas toda la información necesaria para decidir con confianza.

{user_name}, ¿hay algo específico que te preocupa o te gustaría saber? Estoy aquí para ti 🤝"""

    def get_needs_discovery_message(self, user_name: str) -> str:
        """
        Mensaje para descubrir las necesidades del usuario.
        """
        return f"""¡Excelente, {user_name}! 🎯

Para poder ayudarte de la mejor manera y personalizar toda la información, me encantaría conocerte un poco mejor.

**¿Cuál describe mejor tu situación actual?**

Esto me permitirá enfocar todo en lo que realmente necesitas y mostrarte exactamente cómo este curso puede ayudarte a alcanzar tus objetivos.

No hay respuestas correctas o incorrectas, solo quiero entender mejor tu contexto para darte la información más relevante 😊

¿Con cuál te identificas más? 👇"""

    def get_curriculum_info_message(self, user_name: str, course_name: str) -> str:
        """
        Información detallada del temario.
        """
        return f"""¡Perfecto, {user_name}! Aquí tienes el temario completo 📚

**{course_name} - Programa Detallado:**

🎯 **Módulo 1: Fundamentos de IA**
• Introducción práctica a ChatGPT
• Prompts efectivos y técnicas avanzadas
• Casos de uso empresariales

💼 **Módulo 2: IA para Productividad**
• Automatización de tareas repetitivas
• Creación de contenido profesional
• Análisis de datos con IA

🚀 **Módulo 3: IA para Negocios**
• Estrategias de implementación
• ROI y métricas de éxito
• Casos de estudio reales

🎓 **Módulo 4: Proyecto Final**
• Implementación práctica
• Presentación profesional
• Certificación oficial

Cada módulo incluye ejercicios prácticos, plantillas descargables y acceso a herramientas premium.

{user_name}, ¿hay algún módulo que te emociona especialmente? 💡"""

    def get_instructor_info_message(self, user_name: str) -> str:
        """
        Información del instructor.
        """
        return f"""¡Excelente pregunta, {user_name}! 👨‍🏫

**Conoce a tu instructor:**

🎓 **Dr. Carlos Mendoza**
• 15+ años en Inteligencia Artificial
• Ex-Google, Microsoft Research
• Autor de 3 libros sobre IA
• Mentor de 500+ profesionales

🏆 **Logros destacados:**
• Implementó IA en Fortune 100
• Speaker en conferencias internacionales
• Investigación citada 1000+ veces
• Fundador de 2 startups exitosas

💡 **Su enfoque:**
"No importa tu nivel inicial. Mi método se enfoca en aplicación práctica inmediata. Al final del curso, no solo entenderás la IA, sino que la estarás usando para transformar tu trabajo."

👥 **Testimonio de estudiante:**
"Carlos no solo enseña teoría, te acompaña paso a paso hasta que dominas cada herramienta. Cambió completamente mi carrera." - Ana M.

{user_name}, ¿te gustaría saber algo específico sobre su metodología? 🚀"""

    def get_certification_info_message(self, user_name: str) -> str:
        """
        Información sobre la certificación.
        """
        return f"""¡Excelente pregunta, {user_name}! 🎓

**Certificación Oficial:**

✅ **Certificado avalado por:**
• Instituto Tecnológico de IA
• Asociación Internacional de Profesionales en IA
• Válido internacionalmente

📜 **Incluye:**
• Certificado digital verificable
• Badge profesional para LinkedIn
• Transcripción de competencias
• Portfolio de proyectos

💼 **Valor profesional:**
• Reconocido por 200+ empresas
• Cumple estándares ISO 9001
• Incluido en bases de datos de reclutadores
• Válido para puntos de educación continua

🚀 **Bonus de certificación:**
• Carta de recomendación personalizada
• Acceso a bolsa de trabajo exclusiva
• Red de alumni profesionales
• Actualizaciones gratuitas del certificado

{user_name}, este certificado realmente abre puertas. ¿Hay algún aspecto específico sobre su validez que te interese? 💫"""

    def get_error_message(self) -> str:
        """
        Mensaje de error amigable.
        """
        return """Lo siento, parece que hubo un pequeño problema técnico 😅

¡Pero no te preocupes! Estoy aquí para ayudarte.

Por favor, inténtalo de nuevo o escríbeme directamente lo que necesitas. Siempre hay una solución 💪

Si el problema persiste, puedes contactar directamente con nuestro equipo de soporte."""

    def get_privacy_declined_message(self) -> str:
        """
        Mensaje cuando el usuario declina la privacidad.
        """
        return """Entiendo perfectamente tu decisión 😊

Respeto completamente tu privacidad y tu derecho a no compartir información.

Si en algún momento cambias de opinión y quieres conocer más sobre nuestros cursos, estaré aquí para ayudarte.

¡Que tengas un excelente día! 🌟"""

    def get_pricing_info_message(self, user_name: str) -> str:
        """
        Información detallada de precios.
        """
        return f"""Por supuesto, {user_name}! Hablemos de la inversión 💰

**Opciones de pago flexibles:**

💳 **Pago único:**
• Precio: $120 USD
• Descuento: 15% ($102 USD)
• Acceso inmediato completo

📅 **Plan de pagos:**
• 3 pagos de $45 USD
• Sin intereses ni cargos adicionales
• Inicio inmediato

🎁 **¿Qué incluye tu inversión?**
• 12 horas de contenido premium
• Materiales y plantillas ($200 valor)
• Certificación oficial ($150 valor)
• Acceso de por vida ($300 valor)
• Soporte 1-on-1 ($100 valor)

**Total de valor: $870 USD**
**Tu inversión: Solo $120 USD**

{user_name}, es menos de $10 USD por hora de contenido que puede transformar tu carrera completa.

¿Cuál opción se adapta mejor a ti? 🤔"""

    def get_general_info_message(self, user_name: str, course_name: str) -> str:
        """
        Información general del curso.
        """
        return f"""¡Por supuesto, {user_name}! Te comparto toda la información 📋

**{course_name} - Información Completa:**

🎯 **¿Para quién es?**
• Profesionales que quieren potenciar su carrera
• Emprendedores buscando ventaja competitiva
• Estudiantes con visión de futuro
• Cualquier persona curiosa sobre IA

⏰ **Modalidad y tiempo:**
• 100% online y en vivo
• Clases interactivas de 2 horas
• Grabaciones disponibles 24/7
• Horarios flexibles

🛠️ **Herramientas que dominarás:**
• ChatGPT (nivel avanzado)
• Claude AI, Midjourney
• APIs de OpenAI
• Automatizaciones con IA

🎓 **Garantías:**
• 30 días de garantía total
• Soporte técnico incluido
• Acceso de por vida
• Certificación oficial

{user_name}, ¿hay algo específico que te gustaría profundizar? Estoy aquí para resolver todas tus dudas 😊"""

    def get_full_privacy_policy(self) -> str:
        """
        Política de privacidad completa.
        """
        return """📋 **POLÍTICA DE PRIVACIDAD COMPLETA**

**Aprenda y Aplique IA** - Protección de Datos Personales

🔒 **1. INFORMACIÓN QUE RECOPILAMOS:**
• Nombre y datos de contacto que nos proporciones
• Información sobre tus intereses en nuestros cursos
• Historial de conversación para brindarte mejor servicio
• Datos técnicos básicos (horario de conexión, etc.)

🎯 **2. CÓMO USAMOS TU INFORMACIÓN:**
• Personalizar recomendaciones de cursos
• Enviarte información relevante sobre nuestros programas
• Mejorar nuestros servicios y contenidos
• Procesar tu inscripción si decides tomar un curso

🛡️ **3. PROTECCIÓN DE TUS DATOS:**
• Encriptación de extremo a extremo
• Servidores seguros con certificación ISO
• Acceso restringido solo a personal autorizado
• Copias de seguridad protegidas

📞 **4. COMUNICACIONES:**
• Solo te contactaremos con información relevante
• Puedes cancelar comunicaciones en cualquier momento
• Respetamos tus preferencias de frecuencia
• No compartimos tu información con terceros

⚖️ **5. TUS DERECHOS:**
• Acceder a tu información personal
• Rectificar datos incorrectos
• Solicitar eliminación de tus datos
• Portabilidad de tu información

📧 **6. CONTACTO:**
• Email: privacy@aprendayaplique.com
• Teléfono: +1-800-123-4567
• Respuesta garantizada en 48 horas

Última actualización: Enero 2025

Al aceptar, confirmas que has leído y entiendes esta política.""" 