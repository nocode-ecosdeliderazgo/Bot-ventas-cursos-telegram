"""
Implementación de herramientas inteligentes para el agente de ventas.
Módulo separado para mantener el código del agente principal más limpio.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class IntelligentSalesAgentTools:
    """Herramientas inteligentes para el agente de ventas"""
    
    def __init__(self, agent_tools=None):
        self.agent_tools = agent_tools
        
    async def _activate_tools_based_on_intent(
        self, 
        intent_analysis: Dict, 
        user_memory, 
        course_info: Optional[Dict],
        user_message: str,
        user_id: str
    ) -> List[str]:
        """Activa herramientas inteligentemente basado en el análisis de intención"""
        activated_tools = []
        
        if not course_info or not user_memory.selected_course or not self.agent_tools:
            return activated_tools
            
        try:
            category = intent_analysis.get('category', '')
            confidence = intent_analysis.get('confidence', 0.0)
            buying_signals = self._detect_buying_signals(user_message)
            interest_score = user_memory.lead_score or 50
            
            # HERRAMIENTAS BASADAS EN CATEGORÍA DE INTENCIÓN
            if category == 'EXPLORATION' and confidence > 0.6:
                if 'contenido' in user_message.lower() or 'módulo' in user_message.lower():
                    await self.agent_tools.mostrar_syllabus_interactivo(user_id, course_info['id'])
                    activated_tools.append('mostrar_syllabus_interactivo')
                elif 'ver' in user_message.lower() or 'ejemplo' in user_message.lower():
                    await self.agent_tools.enviar_preview_curso(user_id, course_info['id'])
                    activated_tools.append('enviar_preview_curso')
                else:
                    await self.agent_tools.mostrar_recursos_gratuitos(user_id, course_info['id'])
                    activated_tools.append('mostrar_recursos_gratuitos')
                    
            elif category == 'OBJECTION_PRICE' and confidence > 0.5:
                await self.agent_tools.mostrar_comparativa_precios(user_id, course_info['id'])
                await self.agent_tools.personalizar_oferta_por_budget(user_id, course_info['id'])
                activated_tools.extend(['mostrar_comparativa_precios', 'personalizar_oferta_por_budget'])
                
            elif category == 'OBJECTION_VALUE' and confidence > 0.5:
                await self.agent_tools.mostrar_casos_exito_similares(user_id, course_info['id'])
                await self.agent_tools.mostrar_testimonios_relevantes(user_id, course_info['id'])
                activated_tools.extend(['mostrar_casos_exito_similares', 'mostrar_testimonios_relevantes'])
                
            elif category == 'OBJECTION_TRUST' and confidence > 0.5:
                await self.agent_tools.mostrar_garantia_satisfaccion(user_id)
                await self.agent_tools.mostrar_social_proof_inteligente(user_id, course_info['id'])
                activated_tools.extend(['mostrar_garantia_satisfaccion', 'mostrar_social_proof_inteligente'])
                
            elif category == 'OBJECTION_TIME' and confidence > 0.5:
                await self.agent_tools.mostrar_syllabus_interactivo(user_id, course_info['id'])
                activated_tools.append('mostrar_syllabus_interactivo')
                
            elif category == 'BUYING_SIGNALS' and confidence > 0.6:
                if 'precio' in user_message.lower() or 'cuánto' in user_message.lower():
                    await self.agent_tools.presentar_oferta_limitada(user_id, course_info['id'])
                    activated_tools.append('presentar_oferta_limitada')
                elif 'hablar' in user_message.lower() or 'asesor' in user_message.lower():
                    await self.agent_tools.agendar_demo_personalizada(user_id, course_info['id'])
                    activated_tools.append('agendar_demo_personalizada')
                else:
                    await self.agent_tools.mostrar_bonos_exclusivos(user_id, course_info['id'])
                    activated_tools.append('mostrar_bonos_exclusivos')
                    
            elif category == 'AUTOMATION_NEED' and confidence > 0.6:
                await self.agent_tools.enviar_preview_curso(user_id, course_info['id'])
                activated_tools.append('enviar_preview_curso')
                
            # HERRAMIENTAS BASADAS EN COMPORTAMIENTO Y CONTEXTO
            
            # Usuario muy interesado (múltiples interacciones)
            if user_memory.interaction_count >= 3 and interest_score > 70:
                if 'mostrar_bonos_exclusivos' not in activated_tools:
                    await self.agent_tools.generar_urgencia_dinamica(user_id, course_info['id'])
                    activated_tools.append('generar_urgencia_dinamica')
                    
            # Usuario indeciso con múltiples preguntas
            if user_memory.interaction_count >= 2 and interest_score < 60:
                if not any('testimonios' in tool for tool in activated_tools):
                    await self.agent_tools.mostrar_testimonios_relevantes(user_id, course_info['id'])
                    activated_tools.append('mostrar_testimonios_relevantes')
                    
            # Usuario comparando (pregunta específica de diferencias)
            if any(word in user_message.lower() for word in ['mejor', 'diferencia', 'comparar', 'otro curso']):
                await self.agent_tools.mostrar_comparativa_competidores(user_id, course_info['id'])
                activated_tools.append('mostrar_comparativa_competidores')
                
            # Usuario con presupuesto ajustado
            if user_memory.automation_needs and user_memory.automation_needs.get('budget_concern'):
                if 'personalizar_oferta_por_budget' not in activated_tools:
                    await self.agent_tools.personalizar_oferta_por_budget(user_id, course_info['id'])
                    activated_tools.append('personalizar_oferta_por_budget')
                    
            # Usuario con señales de compra fuertes
            if len(buying_signals) >= 2:
                if not any('oferta' in tool for tool in activated_tools):
                    await self.agent_tools.presentar_oferta_limitada(user_id, course_info['id'])
                    activated_tools.append('presentar_oferta_limitada')
                    
            # Limitar a máximo 2 herramientas por interacción para no ser invasivo
            if len(activated_tools) > 2:
                # Priorizar herramientas más relevantes
                priority_tools = [
                    'presentar_oferta_limitada',
                    'agendar_demo_personalizada', 
                    'mostrar_comparativa_precios',
                    'mostrar_casos_exito_similares',
                    'mostrar_syllabus_interactivo'
                ]
                
                final_tools = []
                for priority_tool in priority_tools:
                    if priority_tool in activated_tools:
                        final_tools.append(priority_tool)
                        if len(final_tools) >= 2:
                            break
                            
                if len(final_tools) < 2:
                    remaining = [t for t in activated_tools if t not in final_tools]
                    final_tools.extend(remaining[:2-len(final_tools)])
                    
                activated_tools = final_tools
                
            # Registrar activación de herramientas en la memoria
            if activated_tools:
                user_memory.message_history = user_memory.message_history or []
                user_memory.message_history.append({
                    'role': 'system',
                    'content': f"Herramientas activadas: {', '.join(activated_tools)}",
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            return activated_tools
            
        except Exception as e:
            logger.error(f"Error activando herramientas: {e}")
            return []
    
    def _detect_buying_signals(self, message: str) -> List[str]:
        """Detecta señales de compra en el mensaje del usuario."""
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