"""
Script para verificar las importaciones de servicios.
"""

from core.services.courseService import CourseService
from core.services.promptService import PromptService
from core.services.database import DatabaseService

def main():
    """Función principal para verificar importaciones."""
    print("Verificando importaciones de servicios...")
    
    # Inicializar servicios
    db = DatabaseService("postgres://usuario:contraseña@localhost:5432/db")
    course_service = CourseService(db)
    prompt_service = PromptService("api-key-ejemplo")
    
    print("¡Todas las importaciones de servicios funcionan correctamente!")
    
if __name__ == "__main__":
    main() 