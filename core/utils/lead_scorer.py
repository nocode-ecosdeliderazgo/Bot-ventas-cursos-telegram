"""
Utilidad para calcular el score de interés de un lead basado en sus interacciones.
"""

from typing import Dict, List

async def calculate_initial_score(message: Dict, hashtags: List[str]) -> int:
    """
    Calcula el score inicial de interés basado en el primer mensaje.
    Retorna un valor entre 0 y 100.
    """
    score = 50  # Score base

    # Factores positivos
    if len(message['text']) > 100:  # Mensaje detallado
        score += 10
    
    if '?' in message['text']:  # Muestra interés haciendo preguntas
        score += 5
    
    if any(word in message['text'].lower() for word in ['precio', 'costo', 'inversión', 'pago']):
        score += 10  # Interés en precios indica intención de compra
    
    if any(word in message['text'].lower() for word in ['horario', 'fecha', 'cuando', 'tiempo']):
        score += 5  # Interés en logística
    
    if any(word in message['text'].lower() for word in ['contenido', 'temas', 'aprendo', 'incluye']):
        score += 5  # Interés en contenido
        
    # Factores de urgencia
    if any(word in message['text'].lower() for word in ['urgente', 'pronto', 'inmediato', 'ahora']):
        score += 15

    # Factores de origen
    if len(hashtags) >= 2:  # Viene de una campaña específica
        score += 10
    
    # Asegurar rango válido
    return min(max(score, 0), 100) 