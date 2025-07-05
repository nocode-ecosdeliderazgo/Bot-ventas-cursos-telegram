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
    
    def __init__(self, openai_api_key: str = None):
        """Inicializa el servicio con una conexión a OpenAI."""
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        
        # Configuración para logging de consultas
        self.enable_logging = True
        self.log_queries = []
        self.max_log_entries = 100
    
    async def validate_response(self, response: str, course_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida que la respuesta del agente coincida con la información del curso en la base de datos.
        
        Args:
            response: Respuesta generada por el agente
            course_data: Datos del curso de la base de datos
            
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
            Eres un validador de precisión que verifica que las respuestas de un agente de ventas coincidan exactamente con la información de la base de datos.
            
            # Datos del curso en la base de datos:
            ```json
            {json.dumps(course_data, ensure_ascii=False, default=str)}
            ```
            
            # Respuesta del agente:
            ```
            {response}
            ```
            
            Verifica que TODA la información proporcionada por el agente esté presente en los datos del curso.
            El agente NO DEBE inventar información ni agregar detalles que no estén explícitamente en los datos.
            
            Devuelve un JSON con el siguiente formato:
            ```json
            {{
                "is_valid": true/false,
                "errors": ["lista de afirmaciones incorrectas o inventadas"],
                "warnings": ["lista de posibles problemas o ambigüedades"],
                "confidence": 0.0-1.0
            }}
            ```
            
            La confianza debe ser alta (>0.8) solo si estás seguro de que toda la información es correcta.
            """
            
            # Llamar a la API de OpenAI
            response = await self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": validation_prompt}],
                max_tokens=500,
                temperature=0.1
            )
            
            # Parsear la respuesta
            result = json.loads(response.choices[0].message.content)
            
            # Registrar la validación para auditoría
            if self.enable_logging:
                self._log_validation(course_data.get('id', 'unknown'), result)
            
            return result
        except Exception as e:
            logger.error(f"Error validando respuesta: {e}")
            return {
                "is_valid": False,
                "errors": [f"Error en validación: {str(e)}"],
                "warnings": ["La validación no pudo completarse correctamente"],
                "confidence": 0.0
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
            
            Devuelve un JSON con el siguiente formato:
            ```json
            {{
                "course_references": ["lista", "de", "referencias"],
                "topics": ["lista", "de", "temas"]
            }}
            ```
            
            Solo extrae información que esté claramente presente en el mensaje.
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": extraction_prompt}],
                max_tokens=300,
                temperature=0.1
            )
            
            # Parsear la respuesta
            result = json.loads(response.choices[0].message.content)
            
            # Combinar referencias a cursos y temas
            all_references = result.get('course_references', []) + result.get('topics', [])
            
            return all_references
        except Exception as e:
            logger.error(f"Error extrayendo referencias a cursos: {e}")
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