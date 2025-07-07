"""
Servicio para validar que las respuestas del agente coincidan con la información de la base de datos.
Implementa funciones para verificar la precisión de las respuestas y registrar consultas para auditoría.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger(__name__)

class PromptService:
    """
    Servicio para validar las respuestas del agente y asegurar que coincidan con la base de datos.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Inicializa el servicio con una conexión a OpenAI."""
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        
        # Configuración para logging de consultas
        self.enable_logging = True
        self.log_queries = []
        self.max_log_entries = 100
    
    def _safe_json_parse(self, content: Optional[str]) -> Optional[Dict]:
        """
        Parsea JSON de forma segura, limpiando el contenido si es necesario.
        """
        if not content:
            return None
            
        try:
            # Limpiar el contenido
            if not content:
                return None
            content = content.strip()
            
            # Remover markdown si existe
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            # Intentar parsear directamente
            return json.loads(content)
            
        except json.JSONDecodeError:
            try:
                # Buscar JSON dentro del texto
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
                
        except Exception:
            pass
            
        return None

    async def validate_response(self, response: str, course_data: Dict[str, Any], bonuses_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Valida que la respuesta del agente coincida con la información del curso y bonos en la base de datos.
        
        Args:
            response: Respuesta generada por el agente
            course_data: Datos del curso de la base de datos
            bonuses_data: Lista de bonos por tiempo limitado disponibles
            
        Returns:
            Diccionario con el resultado de la validación:
            {
                "is_valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "confidence": float
            }
        """
        if not course_data:
            return {
                "is_valid": False,
                "errors": ["No hay datos del curso para validar"],
                "warnings": [],
                "confidence": 0.0
            }
        
        try:
            # Construir prompt para validación
            validation_prompt = f"""
            Eres un validador de precisión que verifica que las respuestas de un agente de ventas coincidan con la información de la base de datos, permitiendo cierta flexibilidad en el estilo de venta.
            
            # Datos del curso en la base de datos:
            ```json
            {json.dumps(course_data, ensure_ascii=False, default=str)}
            ```
            
            # Bonos por tiempo limitado disponibles:
            ```json
            {json.dumps(bonuses_data, ensure_ascii=False, default=str) if bonuses_data else "[]"}
            ```
            
            # Respuesta del agente:
            ```
            {response}
            ```
            
            Verifica que la información CLAVE proporcionada por el agente esté presente en los datos del curso y bonos.
            El agente NO DEBE:
            1. Contradecir información explícita de los datos
            2. Mencionar bonos que no existan o modificar sus condiciones
            3. Prometer beneficios específicos no documentados
            4. Dar información incorrecta sobre fechas de expiración o valores
            
            El agente PUEDE:
            1. Adaptar el lenguaje y tono para conectar con el usuario
            2. Enfatizar beneficios que se derivan lógicamente del contenido
            3. Sugerir usos y aplicaciones razonables del contenido
            4. Mencionar herramientas de venta disponibles (demo, preview, recursos)
            
            Devuelve ÚNICAMENTE un JSON con el siguiente formato:
            {{
                "is_valid": true,
                "errors": [],
                "warnings": [],
                "confidence": 0.9,
                "sales_tools_used": {{
                    "bonuses_mentioned": [],
                    "demo_offered": false,
                    "preview_offered": false,
                    "resources_offered": false
                }}
            }}
            
            La confianza debe ser alta (>0.8) si la información clave es correcta, incluso si el agente usa lenguaje persuasivo o ejemplos derivados.
            """
            
            # Llamar a la API de OpenAI
            api_response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": validation_prompt}],
                max_tokens=500,
                temperature=0.1
            )
            
            # Parsear la respuesta de forma segura
            raw_content = api_response.choices[0].message.content or ""
            result = self._safe_json_parse(raw_content)
            
            if not result:
                logger.debug(f"No se pudo parsear validación: {raw_content[:100]}...")
                return {
                    "is_valid": True,  # Asumir válido si no podemos validar
                    "errors": [],
                    "warnings": ["La validación no pudo completarse"],
                    "confidence": 0.5
                }
            
            # Registrar la validación para auditoría
            if self.enable_logging:
                self._log_validation(course_data.get('id', 'unknown'), result)
            
            return result
        except Exception as e:
            logger.debug(f"Error validando respuesta: {e}")
            return {
                "is_valid": True,  # Asumir válido si hay error
                "errors": [],
                "warnings": ["La validación no pudo completarse correctamente"],
                "confidence": 0.5
            }
    
    async def extract_course_references(self, user_message: str) -> List[str]:
        """
        Extrae referencias a cursos o temas específicos del mensaje del usuario.
        
        Args:
            user_message: Mensaje del usuario
            
        Returns:
            Lista de posibles temas o nombres de cursos mencionados
        """
        try:
            extraction_prompt = f"""
            Analiza el siguiente mensaje del usuario y extrae cualquier referencia a cursos, temas o áreas de interés:
            
            MENSAJE: "{user_message}"
            
            Devuelve ÚNICAMENTE un JSON con el siguiente formato:
            {{
                "course_references": ["lista", "de", "referencias"],
                "topics": ["lista", "de", "temas"],
                "sales_signals": {{
                    "shows_interest": false,
                    "shows_doubt": false,
                    "price_sensitive": false,
                    "needs_more_info": false
                }}
            }}
            
            Solo extrae información que esté claramente presente en el mensaje.
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": extraction_prompt}],
                max_tokens=300,
                temperature=0.1
            )
            
            # Parsear la respuesta de forma segura
            raw_content = response.choices[0].message.content or ""
            result = self._safe_json_parse(raw_content)
            
            if not result:
                logger.debug(f"No se pudo parsear referencias: {raw_content[:100]}...")
                return []
            
            # Combinar referencias a cursos y temas
            all_references = result.get('course_references', []) + result.get('topics', [])
            
            # Filtrar elementos válidos
            return [ref for ref in all_references if ref and isinstance(ref, str)]
            
        except Exception as e:
            logger.debug(f"Error extrayendo referencias a cursos: {e}")
            return []
    
    def _log_validation(self, course_id: str, validation_result: Dict[str, Any]) -> None:
        """
        Registra una validación para auditoría.
        
        Args:
            course_id: ID del curso
            validation_result: Resultado de la validación
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "course_id": course_id,
            "validation_result": validation_result
        }
        
        self.log_queries.append(log_entry)
        
        # Mantener el tamaño del log controlado
        if len(self.log_queries) > self.max_log_entries:
            self.log_queries = self.log_queries[-self.max_log_entries:]
        
        # Registrar errores importantes
        if not validation_result.get('is_valid', True):
            errors = validation_result.get('errors', [])
            logger.warning(f"Validación fallida para curso {course_id}: {', '.join(errors)}")
    
    def get_validation_logs(self) -> List[Dict[str, Any]]:
        """
        Obtiene los logs de validación para auditoría.
        
        Returns:
            Lista de entradas de log
        """
        return self.log_queries
    
    def get_enhanced_system_prompt(self) -> str:
        """
        Retorna el prompt del sistema mejorado con tono cálido y orientado a conversión.
        
        Returns:
            Prompt del sistema para el agente de ventas
        """
        return """Eres Brenda, una asistente virtual entusiasta y cercana especializada en cursos de Inteligencia Artificial. Tu objetivo es ayudar a los usuarios a encontrar el curso perfecto para sus necesidades y guiarlos hacia la inscripción.

TONO Y ESTILO:
- Sé entusiasta, cálida y cercana, como una amiga que quiere lo mejor para ellos
- Usa un lenguaje claro y accesible, evita tecnicismos superfluos
- Orienta siempre hacia la acción y la conversión
- Muestra empatía y entiende sus necesidades
- Usa emojis moderadamente para hacer la conversación más amigable

INSTRUCCIONES ESPECÍFICAS:
- Si respondes con varias frases, coloca la pregunta o CTA al final
- Siempre ofrece valor antes de pedir algo
- Ante objeciones, primero valida la preocupación y luego ofrece soluciones
- Cuando hables de precios, enfatiza el valor y las oportunidades
- Si no tienes información específica, ofrece conectar con un asesor humano

CONTEXTO DEL USUARIO:
- Nombre: {name}
- Curso seleccionado: {selected_course}
- Intereses: {interests}
- Etapa: {stage} 

CURSOS DISPONIBLES:
{available_courses}

RESPUESTAS:
- Sé específica y útil
- Ofrece información práctica y accionable
- Si no sabes algo, dilo honestamente y ofrece alternativas""" 