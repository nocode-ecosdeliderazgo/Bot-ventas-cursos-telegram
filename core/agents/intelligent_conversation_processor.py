"""
Procesador Conversacional Inteligente con IA
Mantiene contexto, aprende del usuario y personaliza respuestas
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import asdict

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from core.utils.memory import LeadMemory, GlobalMemory
from core.services.courseService import CourseService

logger = logging.getLogger(__name__)

class IntelligentConversationProcessor:
    """
    Procesador que analiza conversaciones, aprende del usuario y mantiene contexto
    para generar respuestas completamente personalizadas
    """
    
    def __init__(self, openai_client: Optional[AsyncOpenAI], db_service, course_service: CourseService):
        self.client = openai_client
        self.db = db_service
        self.course_service = course_service
        self.global_memory = GlobalMemory()
        
    async def analyze_and_learn(self, user_id: str, message: str, course_id: str = None) -> Dict[str, Any]:
        """
        Analiza el mensaje del usuario y actualiza su perfil de aprendizaje
        """
        user_memory = self.global_memory.get_lead_memory(user_id)
        if not user_memory:
            user_memory = LeadMemory(user_id=user_id)
        
        # Inicializar listas si no existen
        if not user_memory.topics_discussed:
            user_memory.topics_discussed = []
        if not user_memory.questions_asked:
            user_memory.questions_asked = []
        if not user_memory.objections_raised:
            user_memory.objections_raised = []
        if not user_memory.current_challenges:
            user_memory.current_challenges = []
        if not user_memory.tools_used:
            user_memory.tools_used = []
        if not user_memory.conversation_context:
            user_memory.conversation_context = {}
        if not user_memory.learned_preferences:
            user_memory.learned_preferences = {}
        
        # Análisis con IA si está disponible
        if self.client:
            analysis = await self._ai_analysis(message, user_memory, course_id)
        else:
            analysis = await self._rule_based_analysis(message, user_memory)
        
        # Actualizar memoria con nuevos insights
        await self._update_user_profile(user_memory, message, analysis)
        
        # Guardar memoria actualizada
        self.global_memory.save_lead_memory(user_id, user_memory)
        
        return {
            "user_profile": analysis,
            "recommended_response_style": analysis.get("response_style", "friendly"),
            "suggested_tools": analysis.get("suggested_tools", []),
            "engagement_level": analysis.get("engagement_level", "medium"),
            "next_conversation_focus": analysis.get("next_focus", "general")
        }
    
    async def _ai_analysis(self, message: str, user_memory: LeadMemory, course_id: str = None) -> Dict[str, Any]:
        """
        Análisis avanzado usando OpenAI
        """
        try:
            # Obtener información del curso si está disponible
            course_info = ""
            if course_id:
                course_data = await self.course_service.getCourseDetails(course_id)
                if course_data:
                    course_info = f"""
                    CURSO ACTUAL: {course_data.get('name', 'N/A')}
                    Descripción: {course_data.get('short_description', 'N/A')}
                    Nivel: {course_data.get('level', 'N/A')}
                    """
            
            # Construir contexto histórico
            history_context = ""
            if user_memory.message_history:
                recent_messages = user_memory.message_history[-5:]  # Últimos 5 mensajes
                history_context = "HISTORIAL RECIENTE:\n" + "\n".join([
                    f"- {msg.get('role', 'user')}: {msg.get('content', '')[:100]}"
                    for msg in recent_messages
                ])
            
            analysis_prompt = f"""
            Analiza este mensaje del usuario y genera insights para personalizar la conversación:

            MENSAJE ACTUAL: "{message}"

            CONTEXTO DEL USUARIO:
            - Nombre: {user_memory.name or 'No especificado'}
            - Profesión: {user_memory.role or 'No especificada'}
            - Intereses conocidos: {', '.join(user_memory.interests or [])}
            - Temas discutidos previamente: {', '.join(user_memory.topics_discussed or [])}
            - Objeciones pasadas: {', '.join(user_memory.objections_raised or [])}
            - Desafíos actuales: {', '.join(user_memory.current_challenges or [])}
            - Nivel de engagement: {user_memory.engagement_level}
            - Estilo comunicación preferido: {user_memory.preferred_communication_style}
            - Interacciones totales: {user_memory.interaction_count}
            
            {course_info}
            {history_context}

            GENERA UN ANÁLISIS JSON CON:
            {{
                "sentiment": "positive|neutral|negative|frustrated|excited",
                "engagement_level": "low|medium|high|very_high",
                "intent_category": "exploration|objection|buying_signal|technical_question|personal_sharing",
                "detected_challenges": ["lista de desafíos mencionados"],
                "new_interests": ["nuevos intereses detectados"],
                "objections": ["objeciones o preocupaciones mencionadas"],
                "buying_signals": ["señales de interés en compra"],
                "response_style": "formal|casual|technical|consultative|empathetic",
                "suggested_tools": ["herramientas recomendadas"],
                "communication_style": "formal|casual|technical|friendly",
                "next_focus": "address_objection|provide_value|close_sale|explore_need|build_trust",
                "personality_insights": {{"trait": "description"}},
                "automation_interest": {{"level": "high|medium|low", "specific_areas": ["areas"]}},
                "timeline_urgency": "immediate|week|month|exploring",
                "key_phrases": ["frases importantes del usuario"],
                "questions_to_ask": ["preguntas estratégicas para hacer"],
                "personalization_notes": "notas para personalizar siguiente respuesta"
            }}
            """

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=800,
                temperature=0.3
            )

            content = response.choices[0].message.content
            if content:
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    logger.error(f"Error parsing AI analysis: {content}")
                    return self._get_default_analysis()
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
        
        return self._get_default_analysis()
    
    async def _rule_based_analysis(self, message: str, user_memory: LeadMemory) -> Dict[str, Any]:
        """
        Análisis basado en reglas cuando OpenAI no está disponible
        """
        message_lower = message.lower()
        
        # Detectar sentiment básico
        positive_words = ["genial", "excelente", "perfecto", "me gusta", "interesante", "bueno"]
        negative_words = ["caro", "costoso", "no", "pero", "problema", "dificil", "complicado"]
        
        sentiment = "neutral"
        if any(word in message_lower for word in positive_words):
            sentiment = "positive"
        elif any(word in message_lower for word in negative_words):
            sentiment = "negative"
        
        # Detectar intenciones
        intent_category = "exploration"
        if any(word in message_lower for word in ["precio", "costo", "cuanto", "dinero"]):
            intent_category = "objection"
        elif any(word in message_lower for word in ["comprar", "inscribir", "cuando empiezo"]):
            intent_category = "buying_signal"
        elif any(word in message_lower for word in ["trabajo", "empresa", "automatizar"]):
            intent_category = "personal_sharing"
        
        # Detectar nivel de engagement
        engagement_level = "medium"
        if len(message.split()) > 20:  # Mensajes largos = más engagement
            engagement_level = "high"
        elif len(message.split()) < 5:
            engagement_level = "low"
        
        return {
            "sentiment": sentiment,
            "engagement_level": engagement_level,
            "intent_category": intent_category,
            "detected_challenges": self._extract_challenges(message),
            "new_interests": self._extract_interests(message),
            "objections": self._extract_objections(message),
            "buying_signals": self._extract_buying_signals(message),
            "response_style": "friendly",
            "suggested_tools": [],
            "communication_style": "casual" if sentiment == "positive" else "formal",
            "next_focus": "explore_need"
        }
    
    async def _update_user_profile(self, user_memory: LeadMemory, message: str, analysis: Dict[str, Any]):
        """
        Actualiza el perfil del usuario con nuevos insights
        """
        # Incrementar contador de interacciones
        user_memory.interaction_count += 1
        
        # Actualizar engagement level
        user_memory.engagement_level = analysis.get("engagement_level", user_memory.engagement_level)
        
        # Actualizar estilo de comunicación
        user_memory.preferred_communication_style = analysis.get("communication_style", user_memory.preferred_communication_style)
        
        # Agregar nuevos desafíos
        new_challenges = analysis.get("detected_challenges", [])
        if new_challenges:
            if user_memory.current_challenges:
                user_memory.current_challenges.extend(new_challenges)
            else:
                user_memory.current_challenges = new_challenges
            # Eliminar duplicados
            user_memory.current_challenges = list(set(user_memory.current_challenges))
        
        # Agregar nuevos intereses
        new_interests = analysis.get("new_interests", [])
        if new_interests:
            if user_memory.interests:
                user_memory.interests.extend(new_interests)
            else:
                user_memory.interests = new_interests
            user_memory.interests = list(set(user_memory.interests))
        
        # Agregar objecciones
        objections = analysis.get("objections", [])
        if objections:
            if user_memory.objections_raised:
                user_memory.objections_raised.extend(objections)
            else:
                user_memory.objections_raised = objections
        
        # Actualizar timeline de decisión
        timeline = analysis.get("timeline_urgency")
        if timeline:
            user_memory.decision_timeline = timeline
        
        # Guardar análisis en contexto
        user_memory.conversation_context.update({
            "last_analysis": analysis,
            "last_message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Agregar mensaje al historial
        if not user_memory.message_history:
            user_memory.message_history = []
        
        user_memory.message_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis
        })
        
        # Mantener solo últimos 20 mensajes
        if len(user_memory.message_history) > 20:
            user_memory.message_history = user_memory.message_history[-20:]
    
    def _extract_challenges(self, message: str) -> List[str]:
        """Extrae desafíos mencionados en el mensaje"""
        challenges = []
        message_lower = message.lower()
        
        challenge_patterns = [
            (r".*no tengo tiempo.*", "falta de tiempo"),
            (r".*mucho trabajo.*", "exceso de trabajo"),
            (r".*reportes.*", "creación de reportes"),
            (r".*automatizar.*", "necesidad de automatización"),
            (r".*repetitivo.*", "tareas repetitivas"),
            (r".*cliente.*", "atención al cliente"),
            (r".*marketing.*", "gestión de marketing"),
            (r".*ventas.*", "proceso de ventas")
        ]
        
        for pattern, challenge in challenge_patterns:
            if re.search(pattern, message_lower):
                challenges.append(challenge)
        
        return challenges
    
    def _extract_interests(self, message: str) -> List[str]:
        """Extrae intereses mencionados en el mensaje"""
        interests = []
        message_lower = message.lower()
        
        interest_keywords = {
            "automatización": ["automatizar", "automatización", "automático"],
            "IA": ["inteligencia artificial", "ia", "chatgpt", "gpt"],
            "marketing": ["marketing", "publicidad", "mercadeo"],
            "productividad": ["productividad", "eficiencia", "optimizar"],
            "negocio": ["negocio", "empresa", "emprendimiento"],
            "reportes": ["reportes", "informes", "análisis"]
        }
        
        for interest, keywords in interest_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                interests.append(interest)
        
        return interests
    
    def _extract_objections(self, message: str) -> List[str]:
        """Extrae objeciones mencionadas en el mensaje"""
        objections = []
        message_lower = message.lower()
        
        objection_patterns = [
            (r".*caro.*|.*costoso.*|.*precio.*", "precio"),
            (r".*no tengo tiempo.*", "tiempo"),
            (r".*no funciona.*|.*no sirve.*", "efectividad"),
            (r".*dificil.*|.*complicado.*", "complejidad"),
            (r".*no estoy seguro.*|.*dudas.*", "confianza")
        ]
        
        for pattern, objection in objection_patterns:
            if re.search(pattern, message_lower):
                objections.append(objection)
        
        return objections
    
    def _extract_buying_signals(self, message: str) -> List[str]:
        """Extrae señales de compra del mensaje"""
        signals = []
        message_lower = message.lower()
        
        buying_patterns = [
            (r".*cuando.*empez.*", "pregunta sobre inicio"),
            (r".*como.*inscrib.*", "pregunta sobre inscripción"),
            (r".*cuanto.*cuesta.*", "pregunta sobre precio"),
            (r".*que.*incluye.*", "pregunta sobre contenido"),
            (r".*garantia.*", "pregunta sobre garantía"),
            (r".*pago.*", "pregunta sobre métodos de pago")
        ]
        
        for pattern, signal in buying_patterns:
            if re.search(pattern, message_lower):
                signals.append(signal)
        
        return signals
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Análisis por defecto cuando falla el procesamiento"""
        return {
            "sentiment": "neutral",
            "engagement_level": "medium",
            "intent_category": "exploration",
            "detected_challenges": [],
            "new_interests": [],
            "objections": [],
            "buying_signals": [],
            "response_style": "friendly",
            "suggested_tools": [],
            "communication_style": "casual",
            "next_focus": "explore_need"
        }
    
    async def generate_personalized_context(self, user_id: str, course_id: str = None) -> str:
        """
        Genera contexto personalizado para usar en respuestas
        """
        user_memory = self.global_memory.get_lead_memory(user_id)
        if not user_memory:
            return "Usuario nuevo sin historial."
        
        context_parts = []
        
        # Información básica
        if user_memory.name:
            context_parts.append(f"Nombre: {user_memory.name}")
        if user_memory.role:
            context_parts.append(f"Profesión: {user_memory.role}")
        
        # Intereses y desafíos
        if user_memory.interests:
            context_parts.append(f"Intereses: {', '.join(user_memory.interests)}")
        if user_memory.current_challenges:
            context_parts.append(f"Desafíos: {', '.join(user_memory.current_challenges)}")
        
        # Estado de la conversación
        context_parts.append(f"Interacciones: {user_memory.interaction_count}")
        context_parts.append(f"Engagement: {user_memory.engagement_level}")
        context_parts.append(f"Timeline: {user_memory.decision_timeline}")
        
        # Herramientas usadas
        if user_memory.tools_used:
            context_parts.append(f"Herramientas ya usadas: {', '.join(user_memory.tools_used)}")
        
        # Objecciones conocidas
        if user_memory.objections_raised:
            context_parts.append(f"Objeciones previas: {', '.join(user_memory.objections_raised)}")
        
        return " | ".join(context_parts)