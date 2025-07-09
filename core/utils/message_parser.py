"""
Utilidades para procesar mensajes y extraer información relevante.
"""

import re
from typing import List, Optional

def extract_hashtags(text: str) -> List[str]:
    """
    Extrae hashtags de un mensaje.
    Retorna lista de hashtags sin el símbolo #.
    Actualizado para soportar hashtags con guiones bajos y caracteres especiales.
    """
    hashtag_pattern = r'#([a-zA-Z0-9_]+)'
    return re.findall(hashtag_pattern, text)

async def get_course_from_hashtag(hashtags: List[str], db) -> Optional[str]:
    """
    Identifica el curso basado en los hashtags del mensaje.
    Retorna el ID del curso si se encuentra.
    """
    course_tag = next((tag for tag in hashtags if 'CURSO' in tag), None)
    if not course_tag:
        return None

    # Mapeo de hashtags a palabras clave de cursos
    course_keywords = {
        'CURSO_IA_CHATGPT': ['chat', 'gpt', 'dia', 'profesional'],
        'CURSO_PROMPTS': ['prompts', 'ingenieria', 'optimizacion'],
        'CURSO_IMAGENES': ['imagenes', 'generacion', 'diseño'],
        'CURSO_AUTOMATIZACION': ['automatización', 'inteligente', 'asistentes'],
        'curso:ia_chatgpt': ['chat', 'gpt', 'dia', 'profesional'],
        'curso:prompts': ['prompts', 'ingenieria', 'optimizacion'],
        'curso:imagenes': ['imagenes', 'generacion', 'diseño'],
        'curso:automatizacion': ['automatización', 'inteligente', 'asistentes'],
        'Experto_IA_GPT_Gemini': ['experto', 'gpt', 'gemini', 'ia'],
        'EXPERTO_IA_GPT_GEMINI': ['experto', 'gpt', 'gemini', 'ia'],
        'curso:experto_ia_gpt_gemini': ['experto', 'gpt', 'gemini', 'ia'],
        'curso_nuevo': ['curso', 'nuevo', 'especial'],
        'CURSO_NUEVO': ['curso', 'nuevo', 'especial'],
        'curso:nuevo': ['curso', 'nuevo', 'especial']
    }

    # Obtener palabras clave para el hashtag actual
    keywords = course_keywords.get(course_tag, [])
    
    if not keywords:
        return None

    # Buscar curso que coincida con las palabras clave
    query = """
    SELECT id 
    FROM courses 
    WHERE LOWER(name) LIKE ALL($1)
    LIMIT 1;
    """
    
    # Convertir keywords a patrones SQL LIKE
    patterns = [f'%{kw}%' for kw in keywords]
    
    result = await db.fetch_one(query, patterns)
    return result['id'] if result else None 