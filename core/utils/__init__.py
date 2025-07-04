"""
Utilidades del bot de ventas.
"""

from .message_parser import extract_hashtags, get_course_from_hashtag
from .lead_scorer import calculate_initial_score

__all__ = ['extract_hashtags', 'get_course_from_hashtag', 'calculate_initial_score'] 