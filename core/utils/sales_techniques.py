"""
Técnicas de ventas probadas para manejo de objeciones,
construcción de valor y cierre de ventas.
"""

import logging
from typing import Dict, List, Optional
import re

logger = logging.getLogger(__name__)

class SalesTechniques:
    """
    Implementa técnicas de ventas consultivas y probadas
    para maximizar la conversión respetando al cliente.
    """
    
    def __init__(self):
        self.objection_patterns = {
            'price': [
                'caro', 'costoso', 'precio', 'dinero', 'presupuesto', 
                'barato', 'económico', 'descuento', 'oferta'
            ],
            'time': [
                'tiempo', 'ocupado', 'horario', 'disponible', 
                'rápido', 'lento', 'duración', 'cuando'
            ],
            'trust': [
                'confianza', 'seguro', 'garantía', 'estafa', 
                'real', 'verdad', 'experiencia', 'testimonio'
            ],
            'value': [
                'necesito', 'útil', 'sirve', 'funciona', 
                'beneficio', 'resultado', 'vale la pena'
            ],
            'decision': [
                'pensarlo', 'decidir', 'consultar', 'esposa', 
                'jefe', 'después', 'más tarde', 'mañana'
            ],
            'competition': [
                'otro', 'comparar', 'mejor', 'diferente', 
                'competencia', 'alternativa', 'similar'
            ]
        }
        
        self.closing_techniques = {
            'assumptive': "Perfecto, vamos a proceder con tu inscripción...",
            'alternative': "¿Prefieres empezar el lunes o el viernes?",
            'urgency': "Solo quedan 3 lugares disponibles...",
            'summary': "Entonces, hemos visto que este curso te dará...",
            'question': "¿Qué te impide empezar hoy mismo?",
            'puppy_dog': "¿Qué tal si probamos la primera clase sin compromiso?"
        }

    def identify_objection_type(self, message: str) -> str:
        """
        Identifica el tipo de objeción basado en el mensaje del usuario.
        """
        message_lower = message.lower()
        
        # Contar coincidencias por tipo de objeción
        objection_scores = {}
        
        for objection_type, keywords in self.objection_patterns.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                objection_scores[objection_type] = score
        
        # Retornar el tipo con mayor puntuación
        if objection_scores:
            return max(objection_scores, key=objection_scores.get)
        else:
            return 'general'

    def handle_objection(self, objection_type: str, user_name: str) -> str:
        """
        Maneja la objeción específica con técnicas consultivas.
        """
        if objection_type == 'price':
            return self._handle_price_objection(user_name)
        elif objection_type == 'time':
            return self._handle_time_objection(user_name)
        elif objection_type == 'trust':
            return self._handle_trust_objection(user_name)
        elif objection_type == 'value':
            return self._handle_value_objection(user_name)
        elif objection_type == 'decision':
            return self._handle_decision_objection(user_name)
        elif objection_type == 'competition':
            return self._handle_competition_objection(user_name)
        else:
            return self._handle_general_objection(user_name)

    def _handle_price_objection(self, user_name: str) -> str:
        """
        Maneja objeciones de precio usando técnica de valor vs costo.
        """
        return f"""Entiendo perfectamente, {user_name}. Es una excelente pregunta 💰

Déjame ponértelo en perspectiva:

🧮 **Análisis de inversión:**
• Costo del curso: $120 USD
• Aumento salarial promedio: +$1,250 USD/mes
• **ROI en el primer mes: 1,000%**

💡 **Comparemos costos:**
• Una cena para dos: ~$80 USD (se disfruta una noche)
• Este curso: $120 USD (beneficios de por vida)

🎯 **Pregunta clave:**
¿Cuánto te está costando NO saber IA en términos de oportunidades perdidas?

{user_name}, no es un gasto... es la mejor inversión que puedes hacer en ti mismo. 

Además, tenemos opciones de pago sin intereses para que sea más cómodo. ¿Te interesa conocerlas? 🤝"""

    def _handle_time_objection(self, user_name: str) -> str:
        """
        Maneja objeciones de tiempo con técnica de priorización.
        """
        return f"""Te entiendo completamente, {user_name}. El tiempo es nuestro recurso más valioso ⏰

Pero déjame compartirte algo importante:

🎯 **Inversión de tiempo mínima:**
• Solo 2 horas por semana
• Clases los viernes por la noche
• Todo queda grabado (ves cuando puedas)

⚡ **Ahorro de tiempo futuro:**
• La IA te ahorrará 10+ horas semanales
• Automatización de tareas repetitivas
• **Recuperas la inversión de tiempo en 2 semanas**

💭 **Reflexión importante:**
Piensa en cuánto tiempo pasas viendo series o en redes sociales. ¿No vale la pena invertir 2 horas semanales en transformar tu futuro?

{user_name}, las personas exitosas encuentran tiempo para lo que realmente importa.

¿Qué tal si empezamos y adaptas el horario a tu ritmo? 🚀"""

    def _handle_trust_objection(self, user_name: str) -> str:
        """
        Maneja objeciones de confianza con prueba social y garantías.
        """
        return f"""Excelente pregunta, {user_name}. La confianza se gana con hechos 🛡️

**Respaldos que nos avalan:**

🏆 **Credenciales verificables:**
• 500+ estudiantes graduados
• 4.9/5 estrellas en reseñas
• Instructor certificado por Google
• Avalado por instituciones reconocidas

📊 **Resultados comprobables:**
• 94% de estudiantes mejora su situación laboral
• 87% recomienda el curso a amigos
• 100% de testimonios verificables

🔒 **Garantías de protección:**
• 30 días de garantía total
• Reembolso completo sin preguntas
• Soporte técnico incluido
• Acceso de por vida

👥 **Puedes hablar con egresados:**
Tengo contactos de estudiantes que aceptan compartir su experiencia contigo.

{user_name}, entiendo que la confianza es fundamental. ¿Qué necesitas ver específicamente para sentirte seguro/a? 🤝"""

    def _handle_value_objection(self, user_name: str) -> str:
        """
        Maneja objeciones de valor con beneficios tangibles.
        """
        return f"""Perfecto, {user_name}. Hablemos de valor real y tangible 📈

**Valor inmediato (primeras 2 semanas):**
• Automatizas tu trabajo diario
• Creas contenido 10x más rápido
• Analizas datos como experto
• **Valor: $500+ en tiempo ahorrado**

💼 **Valor profesional (3-6 meses):**
• Nuevas oportunidades laborales
• Aumento salarial promedio: $15,000/año
• Proyectos freelance: $2,000+/mes
• **Valor: $30,000+ anuales**

🚀 **Valor a largo plazo:**
• Habilidad demandada por 10+ años
• Ventaja competitiva permanente
• Red profesional exclusiva
• **Valor: Incalculable**

🎁 **Bonus incluidos:**
• Plantillas premium ($200)
• Acceso de por vida ($300)
• Mentoría 1-on-1 ($150)
• Certificación ($100)

{user_name}, ¿hay algún beneficio específico que te gustaría explorar más? 💎"""

    def _handle_decision_objection(self, user_name: str) -> str:
        """
        Maneja objeciones de decisión con técnica de urgencia suave.
        """
        return f"""Lo entiendo perfectamente, {user_name}. Es normal querer reflexionar 🤔

Pero déjame compartirte algo importante:

⚡ **El costo de esperar:**
• Cada día sin IA = oportunidades perdidas
• Los precios suben 20% el próximo mes
• Las plazas son limitadas (quedan 6)
• El siguiente grupo inicia en 3 meses

💭 **Pregunta honesta:**
¿Qué información adicional necesitas que no hayamos cubierto? Porque todo lo que necesitas saber ya está aquí.

🎯 **Técnica del "¿Qué pasaría si...?"**
• ¿Qué pasaría si en 6 meses sigues igual?
• ¿Qué pasaría si tu competencia ya domina IA?
• ¿Qué pasaría si pierdes esta oportunidad?

{user_name}, las personas exitosas toman decisiones cuando tienen suficiente información. Y tú ya la tienes.

¿Qué te parece si aseguramos tu lugar y si surge alguna duda, resolvemos sobre la marcha? 🚀"""

    def _handle_competition_objection(self, user_name: str) -> str:
        """
        Maneja objeciones de competencia destacando diferenciadores únicos.
        """
        return f"""Excelente approach, {user_name}. Comparar es muy inteligente 🔍

**¿Qué nos hace únicos?**

🎯 **Enfoque práctico real:**
• Casos de empresas Fortune 500
• Proyectos que puedes implementar YA
• No solo teoría, sino aplicación inmediata

👨‍🏫 **Instructor nivel mundial:**
• Ex-Google, Microsoft Research
• 15+ años de experiencia real
• Autor de 3 libros sobre IA

🏆 **Resultados comprobables:**
• 94% mejora situación laboral
• Seguimiento post-curso incluido
• Red de egresados activa

💰 **Mejor relación calidad-precio:**
• Contenido premium a precio accesible
• Acceso de por vida (otros cobran mensual)
• Soporte 1-on-1 incluido

🤔 **Pregunta directa:**
¿Qué curso específico estás comparando? Puedo mostrarte exactamente las diferencias.

{user_name}, al final, no se trata del curso más barato, sino del que realmente transforme tu vida. ¿Estás de acuerdo? 💫"""

    def _handle_general_objection(self, user_name: str) -> str:
        """
        Maneja objeciones generales con técnica de exploración.
        """
        return f"""Entiendo, {user_name}. Me gustaría conocer mejor tu perspectiva 🤝

Para poder ayudarte de la mejor manera, déjame preguntarte:

🎯 **¿Cuál es tu principal preocupación?**
• ¿Es el tiempo que requiere?
• ¿Es la inversión económica?
• ¿Es si realmente necesitas estos conocimientos?
• ¿Es si el curso cumplirá tus expectativas?

💡 **Mi compromiso contigo:**
Sea cual sea tu duda, trabajemos juntos para resolverla. No quiero que tomes una decisión sin estar 100% convencido/a.

He ayudado a 500+ personas en tu misma situación, y siempre encontramos la mejor solución.

{user_name}, ¿podrías contarme qué específicamente te tiene dudando? Así puedo darte información exacta y útil 😊"""

    def get_closing_technique(self, technique_type: str, user_name: str, context: Dict = None) -> str:
        """
        Obtiene una técnica de cierre específica personalizada.
        """
        if technique_type == 'assumptive':
            return f"Perfecto, {user_name}! Vamos a proceder con tu inscripción. ¿Prefieres el pago único con descuento o el plan de 3 pagos?"
        
        elif technique_type == 'alternative':
            return f"{user_name}, tengo dos opciones excelentes para ti: ¿empezamos este viernes o prefieres el grupo del próximo lunes?"
        
        elif technique_type == 'urgency':
            return f"¡{user_name}, excelente timing! Solo quedan 3 lugares disponibles y el precio sube mañana. ¿Aseguramos tu lugar ahora?"
        
        elif technique_type == 'summary':
            return f"Entonces, {user_name}, hemos visto que este curso te dará las habilidades de IA que necesitas, con certificación oficial, acceso de por vida y garantía total. ¿Empezamos?"
        
        elif technique_type == 'question':
            return f"{user_name}, has visto todo el valor, los beneficios y las garantías. ¿Qué te impide empezar hoy mismo tu transformación profesional?"
        
        elif technique_type == 'puppy_dog':
            return f"¿Sabes qué, {user_name}? ¿Qué tal si pruebas la primera clase sin compromiso? Si no te convence, te reembolsamos completamente."
        
        else:
            return f"{user_name}, ¿estás listo/a para transformar tu carrera con IA? ¡Empecemos!"

    def detect_buying_signals(self, message: str) -> List[str]:
        """
        Detecta señales de compra en el mensaje del usuario.
        """
        buying_signals = []
        message_lower = message.lower()
        
        signal_patterns = {
            'ready_to_buy': ['comprar', 'adquirir', 'inscribir', 'registrar'],
            'payment_interest': ['pagar', 'precio', 'costo', 'tarjeta', 'transferencia'],
            'timing_questions': ['cuando', 'inicio', 'empezar', 'comenzar'],
            'urgency': ['ya', 'ahora', 'inmediato', 'rápido', 'urgente'],
            'value_accepted': ['perfecto', 'excelente', 'me gusta', 'interesante']
        }
        
        for signal_type, keywords in signal_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                buying_signals.append(signal_type)
        
        return buying_signals

    def calculate_interest_score(self, message: str, history: List[Dict]) -> int:
        """
        Calcula una puntuación de interés basada en el mensaje y historial.
        """
        score = 50  # Base score
        
        # Analizar mensaje actual
        buying_signals = self.detect_buying_signals(message)
        score += len(buying_signals) * 10
        
        # Analizar historial
        if history:
            # Más mensajes = más interés
            score += min(len(history) * 5, 30)
            
            # Buscar progresión de interés
            recent_messages = history[-3:] if len(history) >= 3 else history
            for msg in recent_messages:
                if any(word in msg.get('message', '').lower() for word in ['precio', 'pago', 'inscribir']):
                    score += 15
        
        # Normalizar entre 0-100
        return min(max(score, 0), 100) 