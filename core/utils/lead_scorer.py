"""
Evaluador de leads para el bot de ventas.
Califica a los usuarios según su nivel de interés y probabilidad de compra.
"""

from typing import Dict, List, Optional
from datetime import datetime

class LeadScorer:
    """
    Sistema de puntuación de leads basado en comportamiento, interacciones y señales de compra.
    Asigna una puntuación de 0-100 a cada lead para priorizar seguimientos.
    """
    
    def __init__(self):
        """
        Inicializa el evaluador de leads.
        """
        # Factores de puntuación y sus pesos
        self.scoring_factors = {
            'buying_signals': 0.25,      # Señales de intención de compra
            'engagement': 0.20,          # Nivel de compromiso en la conversación
            'objections': 0.15,          # Objeciones expresadas (inverso)
            'personal_sharing': 0.15,    # Información personal compartida
            'interaction_frequency': 0.10,  # Frecuencia de interacción
            'response_quality': 0.10,    # Calidad de respuestas
            'session_progression': 0.05  # Progresión en el embudo
        }
        
        # Inicializar histórico de puntuaciones
        self.score_history = {}
    
    def update_score(self, user_id: str, message: str, user_memory) -> int:
        """
        Actualiza y devuelve la puntuación del lead basada en el mensaje actual y el historial.
        
        Args:
            user_id: ID del usuario
            message: Mensaje del usuario
            user_memory: Objeto de memoria del usuario
            
        Returns:
            Puntuación actualizada (0-100)
        """
        # Calcular puntuaciones por factor
        factor_scores = {
            'buying_signals': self._score_buying_signals(message),
            'engagement': self._score_engagement(message),
            'objections': self._score_objections(message),
            'personal_sharing': self._score_personal_sharing(message, user_memory),
            'interaction_frequency': self._score_interaction_frequency(user_memory),
            'response_quality': self._score_response_quality(message),
            'session_progression': self._score_session_progression(user_memory)
        }
        
        # Calcular puntuación ponderada
        weighted_score = sum(
            factor_scores[factor] * weight 
            for factor, weight in self.scoring_factors.items()
        )
        
        # Normalizar a escala 0-100
        normalized_score = min(int(weighted_score * 5), 100)
        
        # Guardar puntuación en historial
        if user_id not in self.score_history:
            self.score_history[user_id] = []
            
        self.score_history[user_id].append({
            'timestamp': datetime.now(),
            'score': normalized_score,
            'factors': factor_scores
        })
        
        # Guardar en memoria del usuario
        user_memory.lead_score = normalized_score
        
        # Guardar historial de puntuaciones en memoria
        if not hasattr(user_memory, 'score_history'):
            user_memory.score_history = []
            
        user_memory.score_history.append({
            'timestamp': datetime.now().isoformat(),
            'score': normalized_score
        })
        
        return normalized_score

    def _score_buying_signals(self, message: str) -> int:
        """
        Puntúa las señales de compra en el mensaje.
        """
        message_lower = message.lower()
        score = 0
        
        # Palabras clave de intención de compra
        buying_keywords = [
            'precio', 'costo', 'comprar', 'adquirir', 'pagar',
            'inscribir', 'inscripción', 'invertir', 'inversión', 
            'tarjeta', 'transferencia', 'descuento', 'oferta'
        ]
        
        # Contar palabras clave
        for keyword in buying_keywords:
            if keyword in message_lower:
                score += 5
        
        # Preguntas directas sobre compra
        buying_questions = [
            '¿cuánto cuesta', '¿cuál es el precio', 'cómo puedo pagar',
            'formas de pago', 'métodos de pago', 'cómo me inscribo'
        ]
        
        for question in buying_questions:
            if question in message_lower:
                score += 10
                
        return min(score, 20)  # Máximo 20 puntos

    def _score_engagement(self, message: str) -> int:
        """
        Puntúa el nivel de compromiso en la conversación.
        """
        score = 0
        
        # Longitud del mensaje
        if len(message) > 100:
            score += 5
        elif len(message) > 50:
            score += 3
        elif len(message) > 20:
            score += 1
        
        # Preguntas (indican interés)
        if '?' in message:
            score += 5
            # Múltiples preguntas
            if message.count('?') > 1:
                score += 3
        
        # Expresiones de entusiasmo
        enthusiasm_markers = ['!', 'genial', 'excelente', 'perfecto', 'increíble', 'interesante']
        for marker in enthusiasm_markers:
            if marker in message.lower():
                score += 2
        
        return min(score, 15)  # Máximo 15 puntos

    def _score_objections(self, message: str) -> int:
        """
        Puntúa las objeciones (inverso - más objeciones, menor puntuación).
        """
        message_lower = message.lower()
        score = 10  # Comenzamos con 10 y restamos
        
        # Palabras clave de objeción
        objection_keywords = [
            'caro', 'costoso', 'no puedo', 'imposible', 'difícil',
            'complicado', 'no tengo tiempo', 'no tengo dinero',
            'no me convence', 'tengo que pensarlo', 'no estoy seguro'
        ]
        
        for keyword in objection_keywords:
            if keyword in message_lower:
                score -= 2
        
        return max(score, 0)  # Mínimo 0 puntos

    def _score_personal_sharing(self, message: str, user_memory) -> int:
        """
        Puntúa la información personal compartida.
        """
        message_lower = message.lower()
        score = 0
        
        # Datos personales ya recopilados
        if getattr(user_memory, 'name', None):
            score += 3
        if getattr(user_memory, 'email', None):
            score += 5
        if getattr(user_memory, 'phone', None):
            score += 5
        if getattr(user_memory, 'profession', None):
            score += 3
        if getattr(user_memory, 'interests', None):
            score += 3
        
        # Metas y objetivos
        goal_indicators = [
            'quiero', 'necesito', 'busco', 'objetivo', 'meta',
            'sueño', 'plan', 'futuro', 'cambiar', 'mejorar'
        ]
        if any(indicator in message_lower for indicator in goal_indicators):
            score += 10
    
        return min(score, 15)

    def _score_interaction_frequency(self, user_memory) -> int:
        """
        Puntúa la frecuencia de interacción.
        """
        message_count = len(getattr(user_memory, 'message_history', []))
        
        if message_count >= 10:
            return 10  # Usuario muy activo
        elif message_count >= 5:
            return 7   # Usuario activo
        elif message_count >= 3:
            return 5   # Usuario moderado
        elif message_count >= 1:
            return 2   # Usuario nuevo
        else:
            return 0   # Sin historial

    def _score_response_quality(self, message: str) -> int:
        """
        Puntúa la calidad de la respuesta del usuario.
        """
        score = 0
        
        # Respuestas detalladas (más de 50 caracteres)
        if len(message) > 50:
            score += 5
        
        # Respuestas muy detalladas (más de 150 caracteres)
        if len(message) > 150:
            score += 3
        
        # Respuestas reflexivas (contienen palabras clave)
        thoughtful_words = [
            'pienso', 'creo', 'considero', 'entiendo', 'me parece',
            'reflexiono', 'analizo', 'evalúo', 'comparo'
        ]
        if any(word in message.lower() for word in thoughtful_words):
            score += 5
    
        return min(score, 10)

    def _score_session_progression(self, user_memory) -> int:
        """
        Puntúa el progreso en la sesión (avanza por el embudo).
        """
        stage = getattr(user_memory, 'stage', 'initial')
        
        stage_scores = {
            'initial': 0,
            'privacy_accepted': 2,
            'name_collected': 5,
            'course_presented': 8,
            'information_shared': 10,
            'objection_handled': 12,
            'pricing_discussed': 15,
            'ready_to_buy': 20
        }
        
        return stage_scores.get(stage, 0)

    def get_lead_category(self, score: int) -> str:
        """
        Categoriza el lead basado en su puntuación.
        """
        if score >= 80:
            return 'hot'        # Listo para comprar
        elif score >= 60:
            return 'warm'       # Alto interés
        elif score >= 40:
            return 'lukewarm'   # Interés moderado
        elif score >= 20:
            return 'cold'       # Poco interés
        else:
            return 'frozen'     # Sin interés

    def get_recommended_strategy(self, score: int, user_memory) -> str:
        """
        Recomienda una estrategia basada en la puntuación y contexto.
        """
        category = self.get_lead_category(score)
        stage = getattr(user_memory, 'stage', 'initial')
        
        if category == 'hot':
            return 'close_immediate'
        elif category == 'warm':
            if stage in ['pricing_discussed', 'objection_handled']:
                return 'urgency_close'
            else:
                return 'build_value'
        elif category == 'lukewarm':
            return 'provide_value_info'
        elif category == 'cold':
            return 'nurture_interest'
        else:
            return 'discover_needs'

    def analyze_score_trend(self, user_memory) -> Dict:
        """
        Analiza la tendencia de la puntuación del usuario.
        """
        score_history = getattr(user_memory, 'score_history', [])
        
        if len(score_history) < 2:
            return {'trend': 'insufficient_data', 'direction': 'neutral', 'velocity': 0}
        
        # Últimas 3 puntuaciones
        recent_scores = [entry['score'] for entry in score_history[-3:]]
        
        # Calcular tendencia
        if len(recent_scores) >= 3:
            if recent_scores[-1] > recent_scores[-2] > recent_scores[-3]:
                trend = 'increasing'
            elif recent_scores[-1] < recent_scores[-2] < recent_scores[-3]:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            if recent_scores[-1] > recent_scores[-2]:
                trend = 'increasing'
            elif recent_scores[-1] < recent_scores[-2]:
                trend = 'decreasing'
            else:
                trend = 'stable'
        
        # Calcular velocidad de cambio
        velocity = recent_scores[-1] - recent_scores[0] if len(recent_scores) > 1 else 0
        
        return {
            'trend': trend,
            'direction': 'positive' if velocity > 0 else 'negative' if velocity < 0 else 'neutral',
            'velocity': velocity,
            'current_score': recent_scores[-1],
            'score_change': velocity
        }

    def get_next_action_recommendation(self, user_memory) -> Dict:
        """
        Recomienda la próxima acción basada en el análisis completo.
        """
        score = getattr(user_memory, 'lead_score', 50)
        trend_analysis = self.analyze_score_trend(user_memory)
        strategy = self.get_recommended_strategy(score, user_memory)
        
        # Determinar urgencia
        if score >= 80 or (score >= 60 and trend_analysis['direction'] == 'positive'):
            urgency = 'high'
        elif score >= 40:
            urgency = 'medium'
        else:
            urgency = 'low'
        
        # Determinar timing de seguimiento
        if urgency == 'high':
            follow_up_hours = 2
        elif urgency == 'medium':
            follow_up_hours = 24
        else:
            follow_up_hours = 72
        
        return {
            'score': score,
            'category': self.get_lead_category(score),
            'strategy': strategy,
            'urgency': urgency,
            'follow_up_hours': follow_up_hours,
            'trend': trend_analysis,
            'recommended_actions': self._get_specific_actions(strategy, score, trend_analysis)
        }

    def _get_specific_actions(self, strategy: str, score: int, trend: Dict) -> List[str]:
        """
        Obtiene acciones específicas basadas en la estrategia.
        """
        actions = []
        
        if strategy == 'close_immediate':
            actions = [
                'Presentar opciones de pago inmediatamente',
                'Usar técnica de cierre asumptivo',
                'Crear urgencia con disponibilidad limitada',
                'Ofrecer bonos por decisión inmediata'
            ]
        elif strategy == 'urgency_close':
            actions = [
                'Crear urgencia genuina',
                'Presentar oferta limitada en tiempo',
                'Usar prueba social y escasez',
                'Ofrecer garantía extendida'
            ]
        elif strategy == 'build_value':
            actions = [
                'Enfatizar beneficios principales',
                'Compartir casos de éxito relevantes',
                'Ofrecer demostración personalizada',
                'Responder objeciones pendientes'
            ]
        elif strategy == 'provide_value_info':
            actions = [
                'Enviar contenido educativo gratuito',
                'Compartir testimonios específicos',
                'Ofrecer consulta gratuita',
                'Presentar comparativa de beneficios'
            ]
        elif strategy == 'nurture_interest':
            actions = [
                'Hacer preguntas para descubrir necesidades',
                'Compartir contenido introductorio',
                'Establecer relación de confianza',
                'Programar seguimiento en 3-5 días'
            ]
        else:  # discover_needs
            actions = [
                'Hacer preguntas abiertas sobre objetivos',
                'Identificar puntos de dolor',
                'Establecer rapport inicial',
                'Ofrecer pequeño recurso gratuito de valor'
            ]
        
        return actions 