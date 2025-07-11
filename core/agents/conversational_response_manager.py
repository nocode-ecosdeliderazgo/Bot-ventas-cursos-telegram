"""
Gestor de Respuestas Conversacionales
Evita el envío masivo de archivos y mantiene conversación natural
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from core.utils.memory import LeadMemory

logger = logging.getLogger(__name__)

class ConversationalResponseManager:
    """
    Gestor que controla cuándo enviar recursos y cuándo solo conversar
    para mantener una experiencia natural y no abrumar al usuario
    """
    
    def __init__(self):
        self.response_strategies = {
            "first_interaction": self._handle_first_interaction,
            "exploring": self._handle_exploration,
            "interested": self._handle_interest,
            "objecting": self._handle_objection,
            "ready_to_buy": self._handle_buying_signals
        }
    
    async def manage_response(
        self,
        ai_response: str,
        user_memory: LeadMemory,
        suggested_tools: List[str],
        conversation_analysis: Dict[str, Any],
        course_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Gestiona la respuesta de manera conversacional
        """
        try:
            # Determinar estado de la conversación
            conversation_state = self._determine_conversation_state(user_memory, conversation_analysis)
            
            # Evaluar si debe enviar recursos ahora
            should_send_resources = self._should_send_resources_now(
                user_memory, 
                suggested_tools, 
                conversation_state,
                conversation_analysis
            )
            
            # Preparar respuesta base
            response_data = {
                "primary_response": ai_response,
                "resources_to_send": [],
                "follow_up_action": None,
                "conversation_state": conversation_state,
                "delay_resources": False
            }
            
            if should_send_resources:
                # Seleccionar recursos estratégicamente
                selected_resources = self._select_strategic_resources(
                    suggested_tools,
                    conversation_state,
                    user_memory,
                    course_info
                )
                response_data["resources_to_send"] = selected_resources
            else:
                # Programar recursos para después
                response_data["delay_resources"] = True
                response_data["follow_up_action"] = self._plan_follow_up(
                    suggested_tools,
                    conversation_state,
                    user_memory
                )
            
            # Log de decisión
            logger.info(f"🎯 Estado conversación: {conversation_state}")
            logger.info(f"📦 Recursos ahora: {'Sí' if should_send_resources else 'No'}")
            logger.info(f"🔄 Follow-up: {response_data['follow_up_action']}")
            
            return response_data
            
        except Exception as e:
            logger.error(f"❌ Error gestionando respuesta conversacional: {e}")
            return {
                "primary_response": ai_response,
                "resources_to_send": [],
                "follow_up_action": None,
                "conversation_state": "unknown",
                "delay_resources": False
            }
    
    def _determine_conversation_state(
        self, 
        user_memory: LeadMemory, 
        conversation_analysis: Dict[str, Any]
    ) -> str:
        """
        Determina el estado actual de la conversación
        """
        interaction_count = user_memory.interaction_count
        user_profile = conversation_analysis.get("user_profile", {})
        intent_category = user_profile.get("intent_category", "exploration")
        engagement_level = user_profile.get("engagement_level", "medium")
        
        # Primera interacción
        if interaction_count <= 1:
            return "first_interaction"
        
        # Usuario con objeciones
        if intent_category in ["OBJECTION_PRICE", "OBJECTION_VALUE", "OBJECTION_TIME", "OBJECTION_TRUST"]:
            return "objecting"
        
        # Usuario listo para comprar
        if intent_category == "BUYING_SIGNALS" or engagement_level == "very_high":
            return "ready_to_buy"
        
        # Usuario mostrando interés
        if engagement_level in ["high", "medium"] and interaction_count > 2:
            return "interested"
        
        # Usuario explorando
        return "exploring"
    
    def _should_send_resources_now(
        self,
        user_memory: LeadMemory,
        suggested_tools: List[str],
        conversation_state: str,
        conversation_analysis: Dict[str, Any]
    ) -> bool:
        """
        Decide si debe enviar recursos ahora o esperar
        """
        user_profile = conversation_analysis.get("user_profile", {})
        intent_category = user_profile.get("intent_category", "exploration")
        
        # SIEMPRE enviar si solicita específicamente
        if intent_category == "FREE_RESOURCES":
            return True
        
        # SIEMPRE enviar si pregunta por contenido específico
        explicit_requests = [
            "mostrar_syllabus_interactivo",
            "enviar_preview_curso",
            "contactar_asesor_directo"
        ]
        if any(tool in suggested_tools for tool in explicit_requests):
            return True
        
        # Estrategias por estado
        if conversation_state == "first_interaction":
            # Primera vez: solo conversar, no abrumar
            return False
        
        elif conversation_state == "exploring":
            # Explorando: enviar recursos ocasionalmente
            resources_sent = len(user_memory.resources_sent or [])
            return resources_sent < 2  # Máximo 2 recursos en exploración
        
        elif conversation_state == "interested":
            # Interesado: más liberal con recursos
            return True
        
        elif conversation_state == "objecting":
            # Objeciones: recursos estratégicos para vencer objeciones
            objection_tools = [
                "mostrar_comparativa_precios",
                "mostrar_testimonios_relevantes",
                "mostrar_garantia_satisfaccion"
            ]
            return any(tool in suggested_tools for tool in objection_tools)
        
        elif conversation_state == "ready_to_buy":
            # Listo para comprar: recursos de cierre
            return True
        
        return False
    
    def _select_strategic_resources(
        self,
        suggested_tools: List[str],
        conversation_state: str,
        user_memory: LeadMemory,
        course_info: Optional[Dict]
    ) -> List[str]:
        """
        Selecciona recursos estratégicamente según el estado
        """
        if not suggested_tools:
            return []
        
        # Prioridades por estado
        priorities = {
            "first_interaction": [],  # No enviar en primera interacción
            "exploring": ["enviar_recursos_gratuitos", "mostrar_syllabus_interactivo"],
            "interested": ["mostrar_syllabus_interactivo", "enviar_preview_curso", "mostrar_bonos_exclusivos"],
            "objecting": ["mostrar_comparativa_precios", "mostrar_testimonios_relevantes", "enviar_recursos_gratuitos"],
            "ready_to_buy": ["contactar_asesor_directo", "generar_link_pago_personalizado", "mostrar_garantia_satisfaccion"]
        }
        
        state_priorities = priorities.get(conversation_state, [])
        
        # Filtrar herramientas sugeridas por prioridades del estado
        selected = []
        for tool in state_priorities:
            if tool in suggested_tools:
                selected.append(tool)
                if len(selected) >= 2:  # Máximo 2 herramientas por vez
                    break
        
        # Si no hay herramientas prioritarias, tomar las primeras sugeridas
        if not selected and suggested_tools:
            selected = suggested_tools[:1]  # Solo 1 si no hay prioridades específicas
        
        return selected
    
    def _plan_follow_up(
        self,
        delayed_tools: List[str],
        conversation_state: str,
        user_memory: LeadMemory
    ) -> Optional[Dict[str, Any]]:
        """
        Planifica acciones de seguimiento para herramientas no enviadas
        """
        if not delayed_tools:
            return None
        
        return {
            "next_interaction": "offer_resources",
            "tools_to_offer": delayed_tools,
            "trigger_message": self._get_follow_up_message(conversation_state),
            "timing": "next_message"
        }
    
    def _get_follow_up_message(self, conversation_state: str) -> str:
        """
        Obtiene mensaje de seguimiento según el estado
        """
        messages = {
            "first_interaction": "¿Te gustaría que te comparta algunos recursos útiles?",
            "exploring": "¿Quieres que te muestre el contenido específico del curso?",
            "interested": "¿Te interesaría ver algunos materiales del curso?",
            "objecting": "¿Te ayudaría si te comparto más información?",
            "ready_to_buy": "¿Te gustaría hablar con un asesor especializado?"
        }
        
        return messages.get(conversation_state, "¿Hay algo específico que te gustaría saber?")
    
    def _handle_first_interaction(self, **kwargs) -> Dict[str, Any]:
        """Maneja primera interacción - enfoque conversacional"""
        return {
            "send_resources": False,
            "focus": "build_rapport",
            "max_tools": 0
        }
    
    def _handle_exploration(self, **kwargs) -> Dict[str, Any]:
        """Maneja fase de exploración"""
        return {
            "send_resources": True,
            "focus": "provide_value",
            "max_tools": 1
        }
    
    def _handle_interest(self, **kwargs) -> Dict[str, Any]:
        """Maneja interés mostrado"""
        return {
            "send_resources": True,
            "focus": "deepen_interest",
            "max_tools": 2
        }
    
    def _handle_objection(self, **kwargs) -> Dict[str, Any]:
        """Maneja objeciones"""
        return {
            "send_resources": True,
            "focus": "overcome_objection",
            "max_tools": 1
        }
    
    def _handle_buying_signals(self, **kwargs) -> Dict[str, Any]:
        """Maneja señales de compra"""
        return {
            "send_resources": True,
            "focus": "close_sale",
            "max_tools": 2
        }

class ResponsePacing:
    """
    Controla el ritmo de envío de respuestas para sentirse más natural
    """
    
    @staticmethod
    def should_delay_response(message_length: int, has_resources: bool) -> int:
        """
        Determina si debe haber delay y cuánto
        Retorna delay en segundos
        """
        base_delay = 0
        
        # Delay basado en longitud del mensaje
        if message_length > 200:
            base_delay += 2
        elif message_length > 100:
            base_delay += 1
        
        # Delay adicional si incluye recursos
        if has_resources:
            base_delay += 1
        
        return min(base_delay, 5)  # Máximo 5 segundos
    
    @staticmethod
    def format_typing_indicator(seconds: int) -> str:
        """
        Formato para indicador de escritura
        """
        if seconds <= 1:
            return "Brenda está escribiendo..."
        elif seconds <= 3:
            return "Brenda está preparando tu respuesta..."
        else:
            return "Brenda está buscando la mejor información para ti..."