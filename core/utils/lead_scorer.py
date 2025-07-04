"""
Sistema de puntuación de leads para analizar el interés del usuario
y determinar las mejores estrategias de conversión.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re

logger = logging.getLogger(__name__)

class LeadScorer:
    """
    Califica y puntúa leads basado en su comportamiento,
    interacciones y señales de interés.
    """
    
    def __init__(self):
        self.scoring_weights = {
            'message_frequency': 5,
            'buying_signals': 15,
            'objection_handling': 10,
            'engagement_time': 8,
            'content_interaction': 12,
            'personal_info_sharing': 20,
            'direct_questions': 10,
            'response_speed': 7,
            'session_length': 8,
            'return_visitor': 15
        }
        
        self.buying_signal_keywords = [
            'comprar', 'adquirir', 'inscribir', 'registrar', 'pagar',
            'precio', 'costo', 'tarjeta', 'transferencia', 'cuando',
            'empezar', 'comenzar', 'ya', 'ahora', 'listo'
        ]
        
        self.engagement_keywords = [
            'interesante', 'me gusta', 'genial', 'perfecto', 'excelente',
            'increíble', 'necesito', 'quiero', 'busco', 'ayuda'
        ]
        
        self.objection_keywords = [
            'caro', 'costoso', 'tiempo', 'ocupado', 'pensar',
            'después', 'más tarde', 'difícil', 'problema'
        ]

    def update_score(self, user_id: str, message: str, user_memory) -> int:
        """
        Actualiza la puntuación del lead basada en el nuevo mensaje.
        """
        try:
            current_score = getattr(user_memory, 'lead_score', 50)
            
            # Calcular puntuaciones individuales
            scores = {
                'buying_signals': self._score_buying_signals(message),
                'engagement': self._score_engagement(message),
                'objections': self._score_objections(message),
                'personal_sharing': self._score_personal_sharing(message, user_memory),
                'interaction_frequency': self._score_interaction_frequency(user_memory),
                'response_quality': self._score_response_quality(message),
                'session_progression': self._score_session_progression(user_memory)
            }
            
            # Calcular puntuación total
            total_adjustment = sum(scores.values())
            new_score = min(max(current_score + total_adjustment, 0), 100)
            
            # Actualizar memoria
            user_memory.lead_score = new_score
            user_memory.score_history = getattr(user_memory, 'score_history', [])
            user_memory.score_history.append({
                'timestamp': datetime.now().isoformat(),
                'score': new_score,
                'adjustments': scores,
                'message': message[:100]  # Primeros 100 chars
            })
            
            # Mantener solo los últimos 10 registros
            user_memory.score_history = user_memory.score_history[-10:]
            
            logger.info(f"Lead score updated for {user_id}: {current_score} -> {new_score}")
            return new_score
            
        except Exception as e:
            logger.error(f"Error updating lead score: {e}")
            return getattr(user_memory, 'lead_score', 50)

    def _score_buying_signals(self, message: str) -> int:
        """
        Puntúa señales de compra en el mensaje.
        """
        message_lower = message.lower()
        signals_found = [kw for kw in self.buying_signal_keywords if kw in message_lower]
        
        if len(signals_found) >= 3:
            return 20  # Múltiples señales fuertes
        elif len(signals_found) == 2:
            return 15  # Señales moderadas
        elif len(signals_found) == 1:
            return 10  # Una señal
        else:
            return 0   # Sin señales

    def _score_engagement(self, message: str) -> int:
        """
        Puntúa el nivel de engagement del mensaje.
        """
        message_lower = message.lower()
        
        # Longitud del mensaje (más largo = más engagement)
        length_score = min(len(message) // 20, 5)
        
        # Palabras de engagement
        engagement_words = [kw for kw in self.engagement_keywords if kw in message_lower]
        engagement_score = len(engagement_words) * 3
        
        # Preguntas (indica interés)
        question_score = message.count('?') * 2
        
        # Emojis (indica engagement emocional)
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]')
        emoji_score = len(emoji_pattern.findall(message)) * 1
        
        return min(length_score + engagement_score + question_score + emoji_score, 15)

    def _score_objections(self, message: str) -> int:
        """
        Puntúa objeciones (negativo para el score).
        """
        message_lower = message.lower()
        objections_found = [kw for kw in self.objection_keywords if kw in message_lower]
        
        if len(objections_found) >= 2:
            return -10  # Múltiples objeciones
        elif len(objections_found) == 1:
            return -5   # Una objeción
        else:
            return 0    # Sin objeciones

    def _score_personal_sharing(self, message: str, user_memory) -> int:
        """
        Puntúa cuando el usuario comparte información personal.
        """
        score = 0
        message_lower = message.lower()
        
        # Información profesional
        professional_indicators = [
            'trabajo', 'empleo', 'empresa', 'jefe', 'carrera',
            'profesional', 'negocio', 'cliente', 'proyecto'
        ]
        if any(indicator in message_lower for indicator in professional_indicators):
            score += 8
        
        # Información personal
        personal_indicators = [
            'familia', 'casa', 'tiempo libre', 'hobby', 'estudios',
            'universidad', 'experiencia', 'edad', 'vivo en'
        ]
        if any(indicator in message_lower for indicator in personal_indicators):
            score += 5
        
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
                'Mostrar casos de éxito específicos',
                'Calcular ROI personalizado',
                'Presentar testimonios relevantes',
                'Demostrar diferenciadores únicos'
            ]
        elif strategy == 'provide_value_info':
            actions = [
                'Compartir contenido educativo',
                'Responder preguntas específicas',
                'Mostrar temario detallado',
                'Explicar metodología'
            ]
        elif strategy == 'nurture_interest':
            actions = [
                'Enviar contenido gratuito valioso',
                'Invitar a webinar informativo',
                'Compartir casos de éxito inspiradores',
                'Hacer seguimiento suave'
            ]
        else:  # discover_needs
            actions = [
                'Hacer preguntas abiertas',
                'Descubrir puntos de dolor',
                'Entender objetivos profesionales',
                'Personalizar la propuesta'
            ]
        
        return actions 