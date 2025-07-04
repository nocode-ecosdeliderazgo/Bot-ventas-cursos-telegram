"""
Agente de ventas inteligente que usa OpenAI para generar respuestas
completamente personalizadas basadas en el perfil del usuario.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from core.utils.memory import LeadMemory

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Eres Brenda, una asesora experta en ventas de IA de Ecos de Liderazgo. Tu objetivo es convertir leads en ventas del curso de Inteligencia Artificial de manera natural y estratégica.

REGLAS IMPORTANTES:
1. NO saludes en cada mensaje - solo al primer contacto
2. NO seas insistente con demos/cursos - menciona máximo 1 vez cada 3-4 intercambios
3. Divide mensajes largos automáticamente (máximo 2-3 oraciones por mensaje)
4. Sé conversacional y enfócate en entender sus necesidades ANTES de vender
5. Usa herramientas solo cuando sea estratégicamente apropiado

ESTRATEGIA DE MENSAJES:
- Mensaje 1: Pregunta/conversación principal (máximo 2-3 oraciones)
- Mensaje 2: Información adicional si es necesario (máximo 2-3 oraciones)  
- Mensaje 3: Call-to-action o demo SOLO si es el momento apropiado

CUÁNDO USAR HERRAMIENTAS:
- send_demo_link: Solo después de 2-3 intercambios de valor, cuando muestren interés real
- send_course_info: Solo cuando pregunten específicamente por detalles del curso
- send_pricing_info: Solo cuando mencionen presupuesto o pregunten por precios
- schedule_call: Solo cuando estén listos para comprar o necesiten asesoría personalizada

PERSONALIZACIÓN POR PROFESIÓN:
- Marketing: Automatización de copy, segmentación inteligente, A/B testing con IA
- Ventas: Calificación automática de leads, personalización de propuestas
- Estudiante: Investigación 10x más rápida, ventaja competitiva en el mercado
- Contador: Automatización de reportes, análisis predictivo, reducción de errores
- Gerente: Decisiones basadas en datos, optimización de equipos, KPIs inteligentes
- Emprendedor: Validación de ideas, automatización de procesos, análisis de mercado

RESPUESTA FORMATO:
Si tu respuesta tiene más de 3 oraciones, divídela en múltiples mensajes usando el formato:
[MENSAJE_1] contenido del primer mensaje
[MENSAJE_2] contenido del segundo mensaje
[MENSAJE_3] contenido del tercer mensaje (si es necesario)

Mantén cada mensaje conversacional, valioso y enfocado en sus necesidades específicas.
"""

class IntelligentSalesAgent:
    """
    Agente de ventas inteligente que usa OpenAI para generar respuestas
    completamente personalizadas y estratégicas.
    """
    
    def __init__(self, openai_api_key: str):
        # Cliente de OpenAI
        if AsyncOpenAI is None:
            logger.error("OpenAI no está instalado. Instala con: pip install openai")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=openai_api_key)
        
        # Prompt de sistema que define al agente
        self.system_prompt = SYSTEM_PROMPT

    async def generate_response(self, user_message: str, user_memory: LeadMemory, course_info: Optional[Dict]) -> str:
        """Genera una respuesta personalizada usando OpenAI"""
        if self.client is None:
            return "Lo siento, hay un problema con el sistema. Por favor intenta más tarde."
            
        try:
            # Actualizar memoria con nueva información extraída
            await self._extract_and_update_user_info(user_message, user_memory)
            
            # Incrementar contador de interacciones
            user_memory.interaction_count += 1
            
            # Construir prompt personalizado
            user_prompt = self._build_user_prompt(user_message, user_memory.to_dict())
            
            # Generar respuesta con OpenAI
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content
            
            # Procesar respuesta y manejar múltiples mensajes
            messages = await self._process_response(response_text, str(user_memory.user_id), user_memory.to_dict())
            
            # Actualizar historial de conversación
            if not user_memory.conversation_history:
                user_memory.conversation_history = []
            
            user_memory.conversation_history.append({
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Agregar respuesta del agente al historial
            for msg in messages:
                if msg['type'] == 'text':
                    user_memory.conversation_history.append({
                        'role': 'assistant',
                        'content': msg['content'],
                        'timestamp': datetime.now().isoformat()
                    })
            
            # Retornar el primer mensaje de texto, los demás se enviarán por separado
            text_messages = [msg for msg in messages if msg['type'] == 'text']
            if text_messages:
                return text_messages[0]['content']
            else:
                return response_text
                
        except Exception as e:
            logger.error(f"Error generando respuesta: {e}", exc_info=True)
            return "Disculpa, hubo un error procesando tu mensaje. ¿Podrías intentar de nuevo?"

    async def _extract_and_update_user_info(self, user_message: str, user_memory: LeadMemory) -> None:
        """Extrae información del usuario usando OpenAI y actualiza la memoria"""
        if self.client is None:
            return
            
        try:
            extraction_prompt = f"""
Analiza el siguiente mensaje del usuario y extrae información relevante:

MENSAJE: "{user_message}"

Extrae y devuelve en formato JSON:
{{
    "profession": "profesión detectada o null",
    "interests": ["lista", "de", "intereses"],
    "pain_points": ["puntos", "de", "dolor"],
    "buying_signals": ["señales", "de", "compra"],
    "objections": ["objeciones", "mencionadas"],
    "interest_level": "low/medium/high"
}}

Solo extrae información que esté claramente presente en el mensaje.
"""
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": extraction_prompt}],
                max_tokens=300,
                temperature=0.1
            )
            
            # Parsear respuesta JSON
            import json
            extracted_info = json.loads(response.choices[0].message.content)
            
            # Actualizar memoria del usuario
            if extracted_info.get('profession'):
                user_memory.role = extracted_info['profession']
            
            if extracted_info.get('interests'):
                current_interests = user_memory.interests or []
                new_interests = [i for i in extracted_info['interests'] if i not in current_interests]
                user_memory.interests = current_interests + new_interests
            
            # Agregar información adicional
            if extracted_info.get('pain_points'):
                user_memory.pain_points = user_memory.pain_points or []
                user_memory.pain_points.extend(extracted_info['pain_points'])
            if extracted_info.get('buying_signals'):
                user_memory.buying_signals = user_memory.buying_signals or []
                user_memory.buying_signals.extend(extracted_info['buying_signals'])
            if extracted_info.get('interest_level'):
                user_memory.interest_level = extracted_info['interest_level']
                
        except Exception as e:
            logger.error(f"Error extrayendo información del usuario: {e}", exc_info=True)

    def _build_user_prompt(self, user_message: str, user_memory: dict) -> str:
        """Construye el prompt del usuario con información contextual"""
        
        # Información del usuario
        user_info = []
        if user_memory.get('name'):
            user_info.append(f"Nombre: {user_memory['name']}")
        if user_memory.get('role'):
            user_info.append(f"Profesión: {user_memory['role']}")
        if user_memory.get('interests'):
            user_info.append(f"Intereses: {', '.join(user_memory['interests'])}")
        if user_memory.get('pain_points'):
            user_info.append(f"Puntos de dolor: {', '.join(user_memory['pain_points'])}")
        if user_memory.get('interaction_count', 0) > 0:
            user_info.append(f"Interacciones previas: {user_memory['interaction_count']}")
        if user_memory.get('interest_level'):
            user_info.append(f"Nivel de interés: {user_memory['interest_level']}")
            
        # Historial de conversación (últimos 3 mensajes)
        conversation_history = ""
        if user_memory.get('conversation_history'):
            recent_messages = user_memory['conversation_history'][-6:]  # Últimos 3 intercambios
            for msg in recent_messages:
                role = "Usuario" if msg['role'] == 'user' else "Brenda"
                conversation_history += f"{role}: {msg['content']}\n"
        
        prompt = f"""
INFORMACIÓN DEL USUARIO:
{chr(10).join(user_info) if user_info else "Usuario nuevo"}

HISTORIAL RECIENTE:
{conversation_history if conversation_history else "Primera interacción"}

MENSAJE ACTUAL DEL USUARIO:
{user_message}

INSTRUCCIONES:
1. Responde de manera natural y conversacional
2. NO repitas saludos si ya se ha saludado antes
3. Si tu respuesta es larga, divídela en múltiples mensajes usando [MENSAJE_1], [MENSAJE_2], etc.
4. Enfócate en entender sus necesidades antes de vender
5. Solo menciona demo/curso si es estratégicamente apropiado
6. Usa herramientas solo cuando sea el momento adecuado

Responde ahora:
"""
        return prompt

    async def _process_response(self, response_text: str, user_id: str, user_memory: dict) -> List[Dict]:
        """Procesa la respuesta del LLM y maneja múltiples mensajes"""
        messages = []
        
        # Verificar si la respuesta contiene múltiples mensajes
        if "[MENSAJE_" in response_text:
            # Dividir por mensajes
            import re
            message_parts = re.split(r'\[MENSAJE_\d+\]', response_text)
            message_parts = [part.strip() for part in message_parts if part.strip()]
            
            for part in message_parts:
                if part:
                    messages.append({
                        'type': 'text',
                        'content': part
                    })
        else:
            # Mensaje único
            messages.append({
                'type': 'text', 
                'content': response_text
            })
        
        return messages

    async def _should_use_tools(self, response_text: str, user_memory: dict) -> bool:
        """Determina si debe usar herramientas basado en el contexto"""
        interaction_count = user_memory.get('interaction_count', 0)
        interest_level = user_memory.get('interest_level', 'low')
        
        # No usar herramientas si es muy temprano en la conversación
        if interaction_count < 2:
            return False
            
        # Usar herramientas si hay señales claras de interés
        keywords = ['demo', 'curso', 'precio', 'información', 'detalles']
        has_keywords = any(keyword in response_text.lower() for keyword in keywords)
        
        return has_keywords and interest_level in ['medium', 'high']

    async def _execute_tools(self, response_text: str, user_memory: dict) -> List[Dict]:
        """Ejecuta las herramientas apropiadas"""
        tool_messages = []
        
        # Por ahora solo retornamos mensajes vacíos
        # En el futuro se pueden agregar herramientas específicas
        
        return tool_messages 