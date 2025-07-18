"""
Ejemplo de uso de los servicios de cursos y validación de respuestas.
Este script muestra cómo utilizar los servicios implementados para consultar
información de cursos y validar respuestas del agente.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any

from config.settings import settings
from core.services.courseService import CourseService
from core.services.promptService import PromptService
from core.agents.intelligent_sales_agent import IntelligentSalesAgent
from core.utils.memory import LeadMemory
from core.services.database import DatabaseService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    """Función principal que ejecuta ejemplos de uso de los servicios."""
    try:
        # Inicializar servicios
        db = DatabaseService(settings.DATABASE_URL)
        course_service = CourseService(db)
        prompt_service = PromptService(settings.OPENAI_API_KEY)
        intelligent_agent = IntelligentSalesAgent(settings.OPENAI_API_KEY, db)
        
        # ID de curso de ejemplo (IA para tu día a día profesional)
        curso_id = "a392bf83-4908-4807-89a9-95d0acc807c9"
        
        # 1. Obtener detalles del curso
        logger.info("Obteniendo detalles del curso...")
        course_details = await course_service.getCourseDetails(curso_id)
        if course_details:
            logger.info(f"Curso encontrado: {course_details.get('name')}")
            logger.info(f"Descripción: {course_details.get('short_description')}")
        else:
            logger.error("No se encontró el curso")
            return
        
        # 2. Obtener módulos del curso
        logger.info("\nObteniendo módulos del curso...")
        modules = await course_service.getCourseModules(curso_id)
        if modules:
            logger.info(f"Se encontraron {len(modules)} módulos:")
            for module in modules:
                logger.info(f"- Módulo {module.get('module_index')}: {module.get('name')}")
        else:
            logger.warning("No se encontraron módulos para este curso")
        
        # 3. Buscar cursos por palabra clave
        search_term = "inteligencia artificial"
        logger.info(f"\nBuscando cursos con el término '{search_term}'...")
        search_results = await course_service.searchCourses(search_term)
        if search_results:
            logger.info(f"Se encontraron {len(search_results)} cursos:")
            for course in search_results:
                logger.info(f"- {course.get('name')}")
        else:
            logger.warning(f"No se encontraron cursos con el término '{search_term}'")
        
        # 4. Extraer referencias a cursos de un mensaje
        user_message = "Me interesa aprender sobre inteligencia artificial para automatizar tareas en mi trabajo como contador"
        logger.info(f"\nExtrayendo referencias de cursos del mensaje: '{user_message}'")
        references = await prompt_service.extract_course_references(user_message)
        if references:
            logger.info(f"Referencias encontradas: {references}")
        else:
            logger.warning("No se encontraron referencias a cursos en el mensaje")
        
        # 5. Generar respuesta con el agente inteligente
        logger.info("\nGenerando respuesta con el agente inteligente...")
        user_memory = LeadMemory(user_id="example_user")
        user_memory.name = "Usuario de Ejemplo"
        user_memory.role = "Contador"
        user_memory.interests = ["automatización", "inteligencia artificial"]
        
        response = await intelligent_agent.generate_response(
            user_message=user_message,
            user_memory=user_memory,
            course_info=course_details
        )
        
        if isinstance(response, list):
            logger.info("Respuesta del agente (múltiples mensajes):")
            for msg in response:
                logger.info(f"- {msg.get('content')}")
        else:
            logger.info(f"Respuesta del agente: {response}")
        
        # 6. Validar respuesta del agente
        logger.info("\nValidando respuesta del agente...")
        if isinstance(response, list):
            response_text = response[0].get('content', '')
        else:
            response_text = response
            
        validation = await prompt_service.validate_response(response_text, course_details)
        logger.info(f"Resultado de validación: {json.dumps(validation, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error en la ejecución: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
