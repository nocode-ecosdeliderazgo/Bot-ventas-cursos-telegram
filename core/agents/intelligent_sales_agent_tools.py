"""
Implementación de herramientas inteligentes para el agente de ventas.
VERSIÓN REDISEÑADA - Procesa contenido retornado por herramientas unificadas.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class IntelligentSalesAgentTools:
    """Herramientas inteligentes para el agente de ventas - REDISEÑADAS"""
    
    def __init__(self, agent_tools=None):
        self.agent_tools = agent_tools
        
    async def _activate_tools_based_on_intent(
        self, 
        intent_analysis: Dict, 
        user_memory, 
        course_info: Optional[Dict],
        user_message: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        REDISEÑADO: Activa herramientas y retorna el contenido para que el agente lo procese.
        """
        activated_tools = []
        tool_contents = []
        
        if not course_info or not user_memory.selected_course or not self.agent_tools:
            return tool_contents
            
        try:
            category = intent_analysis.get('category', '')
            confidence = intent_analysis.get('confidence', 0.0)
            buying_signals = self._detect_buying_signals(user_message)
            interest_score = user_memory.lead_score or 50
            
            # Variables para control de activación
            course_id = course_info['id']
            max_tools = 1  # Máximo 1 herramienta por mensaje para ser directo
            
            # ACTIVACIÓN DIRECTA BASADA EN CATEGORÍA DE INTENCIÓN
            
            if category == 'EXPLORATION' and confidence > 0.6:
                if 'contenido' in user_message.lower() or 'módulo' in user_message.lower() or 'temario' in user_message.lower():
                    content = await self.agent_tools.mostrar_syllabus_interactivo(user_id, course_id)
                    if self._is_valid_content(content):
                        tool_contents.append(content)
                        activated_tools.append('mostrar_syllabus_interactivo')
                        
                elif 'ver' in user_message.lower() or 'ejemplo' in user_message.lower() or 'video' in user_message.lower():
                    content = await self.agent_tools.enviar_preview_curso(user_id, course_id)
                    if self._is_valid_content(content):
                        tool_contents.append(content)
                        activated_tools.append('enviar_preview_curso')
                else:
                    content = await self.agent_tools.enviar_recursos_gratuitos(user_id, course_id)
                    if self._is_valid_content(content):
                        tool_contents.append(content)
                        activated_tools.append('enviar_recursos_gratuitos')
                        
            elif category == 'FREE_RESOURCES' and confidence > 0.5:
                # DIRECTO: Enviar recursos sin preguntar
                content = await self.agent_tools.enviar_recursos_gratuitos(user_id, course_id)
                if self._is_valid_content(content):
                    tool_contents.append(content)
                    activated_tools.append('enviar_recursos_gratuitos')
                    
            elif category == 'OBJECTION_PRICE' and confidence > 0.5:
                content = await self.agent_tools.mostrar_comparativa_precios(user_id, course_id)
                if self._is_valid_content(content):
                    tool_contents.append(content)
                    activated_tools.append('mostrar_comparativa_precios')
                    
            elif category == 'OBJECTION_VALUE' and confidence > 0.5:
                content = await self.agent_tools.mostrar_casos_exito_similares(user_id, course_id)
                if self._is_valid_content(content):
                    tool_contents.append(content)
                    activated_tools.append('mostrar_casos_exito_similares')
                    
            elif category == 'OBJECTION_TRUST' and confidence > 0.5:
                content = await self.agent_tools.mostrar_garantia_satisfaccion(user_id)
                if self._is_valid_content(content):
                    tool_contents.append(content)
                    activated_tools.append('mostrar_garantia_satisfaccion')
                    
            elif category == 'OBJECTION_TIME' and confidence > 0.5:
                content = await self.agent_tools.gestionar_objeciones_tiempo(user_id, course_id)
                if self._is_valid_content(content):
                    tool_contents.append(content)
                    activated_tools.append('gestionar_objeciones_tiempo')
                    
            elif category == 'BUYING_SIGNALS' and confidence > 0.6:
                if 'precio' in user_message.lower() or 'cuánto' in user_message.lower():
                    content = await self.agent_tools.presentar_oferta_limitada(user_id, course_id)
                    if self._is_valid_content(content):
                        tool_contents.append(content)
                        activated_tools.append('presentar_oferta_limitada')
                elif any(keyword in user_message.lower() for keyword in ['hablar', 'asesor', 'contactar', 'consulta']):
                    # CRÍTICO: Para contactar asesor, usar el wrapper que retorna string
                    try:
                        response = await self.agent_tools.contactar_asesor_directo(user_id, course_id)
                        # Contactar asesor retorna un string, no un dict
                        if response and isinstance(response, str):
                            tool_contents.append({
                                "type": "contact_flow_activated",
                                "content": response
                            })
                            activated_tools.append('contactar_asesor_directo')
                    except Exception as e:
                        logger.error(f"Error activando contacto con asesor: {e}")
                else:
                    content = await self.agent_tools.mostrar_bonos_exclusivos(user_id, course_id)
                    if self._is_valid_content(content):
                        tool_contents.append(content)
                        activated_tools.append('mostrar_bonos_exclusivos')
                        
            elif category == 'AUTOMATION_NEED' and confidence > 0.6:
                content = await self.agent_tools.detectar_necesidades_automatizacion(user_id, course_id)
                if self._is_valid_content(content):
                    tool_contents.append(content)
                    activated_tools.append('detectar_necesidades_automatizacion')
                    
            # DETECCIÓN ESPECÍFICA PARA CONTACTO CON ASESOR (SIEMPRE PRIORITARIO)
            contact_keywords = ['asesor', 'contactar', 'hablar', 'ayuda', 'consulta', 'especialista', 'soporte']
            if any(keyword in user_message.lower() for keyword in contact_keywords):
                try:
                    response = await self.agent_tools.contactar_asesor_directo(user_id, course_id)
                    if response and isinstance(response, str):
                        tool_contents.append({
                            "type": "contact_flow_activated",
                            "content": response
                        })
                        activated_tools.append('contactar_asesor_directo')
                except Exception as e:
                    logger.error(f"Error activando contacto con asesor: {e}")
                    
            # DETECCIÓN ESPECÍFICA PARA SOLICITUDES DE RECURSOS (SIEMPRE DIRECTO)
            resource_keywords = ['recursos', 'material', 'guía', 'plantilla', 'template', 'gratis', 'gratuito']
            if any(keyword in user_message.lower() for keyword in resource_keywords) and 'enviar_recursos_gratuitos' not in activated_tools:
                content = await self.agent_tools.enviar_recursos_gratuitos(user_id, course_id)
                if self._is_valid_content(content):
                    tool_contents.append(content)
                    activated_tools.append('enviar_recursos_gratuitos')
                    
            # HERRAMIENTAS BASADAS EN COMPORTAMIENTO Y CONTEXTO (solo si no se activó nada)
            if not tool_contents:
                
                # Usuario muy interesado (múltiples interacciones)
                if user_memory.interaction_count >= 3 and interest_score > 70:
                    content = await self.agent_tools.mostrar_bonos_exclusivos(user_id, course_id)
                    if self._is_valid_content(content):
                        tool_contents.append(content)
                        activated_tools.append('mostrar_bonos_exclusivos')
                        
                # Usuario indeciso con múltiples preguntas
                elif user_memory.interaction_count >= 2 and interest_score < 60:
                    content = await self.agent_tools.mostrar_testimonios_relevantes(user_id, course_id)
                    if self._is_valid_content(content):
                        tool_contents.append(content)
                        activated_tools.append('mostrar_testimonios_relevantes')
                        
                # Usuario comparando (pregunta específica de diferencias)
                elif any(word in user_message.lower() for word in ['mejor', 'diferencia', 'comparar', 'otro curso']):
                    content = await self.agent_tools.mostrar_comparativa_competidores(user_id, course_id)
                    if self._is_valid_content(content):
                        tool_contents.append(content)
                        activated_tools.append('mostrar_comparativa_competidores')
                        
                # Usuario con señales de compra fuertes
                elif len(buying_signals) >= 2:
                    content = await self.agent_tools.presentar_oferta_limitada(user_id, course_id)
                    if self._is_valid_content(content):
                        tool_contents.append(content)
                        activated_tools.append('presentar_oferta_limitada')
                        
                # Fallback: mostrar syllabus si no hay otra cosa
                else:
                    content = await self.agent_tools.mostrar_syllabus_interactivo(user_id, course_id)
                    if self._is_valid_content(content):
                        tool_contents.append(content)
                        activated_tools.append('mostrar_syllabus_interactivo')
                    
            # Limitar a máximo 1 herramienta por mensaje para ser directo
            if len(tool_contents) > max_tools:
                tool_contents = tool_contents[:max_tools]
                activated_tools = activated_tools[:max_tools]
                
            # Registrar activación de herramientas en la memoria
            if activated_tools:
                user_memory.message_history = user_memory.message_history or []
                user_memory.message_history.append({
                    'role': 'system',
                    'content': f"Herramientas activadas: {', '.join(activated_tools)}",
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                logger.info(f"✅ Herramientas activadas para usuario {user_id}: {activated_tools}")
                
            return tool_contents
            
        except Exception as e:
            logger.error(f"Error activando herramientas: {e}")
            return []
    
    def _is_valid_content(self, content: Union[Dict, str, None]) -> bool:
        """Verifica si el contenido retornado por una herramienta es válido."""
        if not content:
            return False
            
        if isinstance(content, dict):
            return content.get('type') != 'error' and content.get('content')
        elif isinstance(content, str):
            return len(content.strip()) > 0
            
        return False
    
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

    def format_tool_content_for_agent(self, tool_contents: List[Dict[str, Any]]) -> str:
        """
        Formatea el contenido de las herramientas para que el agente lo incorpore en su respuesta.
        """
        if not tool_contents:
            return ""
            
        formatted_content = "\n\n## CONTENIDO DE HERRAMIENTAS ACTIVADAS:\n\n"
        
        for i, content in enumerate(tool_contents, 1):
            content_type = content.get('type', 'text')
            content_text = content.get('content', '')
            
            if content_type == 'contact_flow_activated':
                # Para contacto con asesor, el contenido ya es la respuesta completa
                return content_text
                
            elif content_type in ['text', 'multimedia']:
                formatted_content += f"### Herramienta {i}: {content_type.title()}\n"
                formatted_content += content_text + "\n\n"
                
                # Agregar información de recursos si existen
                resources = content.get('resources', [])
                if resources:
                    formatted_content += "**Recursos incluidos:**\n"
                    for resource in resources:
                        resource_type = resource.get('type', 'link')
                        if resource_type == 'document':
                            formatted_content += f"📄 {resource.get('caption', 'Documento')}\n"
                        elif resource_type == 'video':
                            formatted_content += f"🎥 {resource.get('caption', 'Video')}\n"
                        elif resource_type == 'link':
                            formatted_content += f"🔗 {resource.get('text', 'Enlace')}\n"
                    formatted_content += "\n"
                    
            elif content_type == 'error':
                logger.warning(f"Error en herramienta: {content_text}")
                continue
                
        return formatted_content if formatted_content != "\n\n## CONTENIDO DE HERRAMIENTAS ACTIVADAS:\n\n" else ""