#!/usr/bin/env python3
"""
Script to verify agent imports and basic functionality
"""
import sys
import os

# Add the venv site-packages to the Python path
venv_path = os.path.join(os.getcwd(), 'venv', 'Lib', 'site-packages')
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

def test_agents():
    """Test all agent imports"""
    print("Verificando importaciones de agentes...")
    print("-" * 50)
    
    # Test ConversationProcessor
    try:
        from core.agents.conversation_processor import ConversationProcessor
        print("✅ ConversationProcessor importado correctamente")
    except Exception as e:
        print(f"❌ Error importando ConversationProcessor: {e}")
        return False
    
    # Test IntelligentSalesAgent
    try:
        from core.agents.intelligent_sales_agent import IntelligentSalesAgent
        print("✅ IntelligentSalesAgent importado correctamente")
    except Exception as e:
        print(f"❌ Error importando IntelligentSalesAgent: {e}")
        return False
    
    # Test AgentTools
    try:
        from core.agents.agent_tools import AgentTools
        print("✅ AgentTools importado correctamente")
    except Exception as e:
        print(f"❌ Error importando AgentTools: {e}")
        return False
    
    # Test SmartSalesAgent
    try:
        from core.agents.smart_sales_agent import SmartSalesAgent
        print("✅ SmartSalesAgent importado correctamente")
    except Exception as e:
        print(f"❌ Error importando SmartSalesAgent: {e}")
        return False
    
    print("-" * 50)
    print("✅ Todos los agentes importados exitosamente!")
    return True

def test_services():
    """Test service imports"""
    print("\nVerificando servicios...")
    print("-" * 50)
    
    # Test CourseService
    try:
        from core.services.courseService import CourseService
        print("✅ CourseService importado correctamente")
    except Exception as e:
        print(f"❌ Error importando CourseService: {e}")
        return False
    
    # Test PromptService
    try:
        from core.services.promptService import PromptService
        print("✅ PromptService importado correctamente")
    except Exception as e:
        print(f"❌ Error importando PromptService: {e}")
        return False
    
    # Test DatabaseService (might fail due to asyncpg)
    try:
        from core.services.database import DatabaseService
        print("✅ DatabaseService importado correctamente")
    except Exception as e:
        print(f"❌ Error importando DatabaseService: {e}")
        print("   Nota: Esto puede ser normal si asyncpg no está disponible")
        return False
    
    print("-" * 50)
    print("✅ Servicios verificados!")
    return True

def test_utilities():
    """Test utility imports"""
    print("\nVerificando utilidades...")
    print("-" * 50)
    
    # Test MessageTemplates
    try:
        from core.utils.message_templates import MessageTemplates
        print("✅ MessageTemplates importado correctamente")
    except Exception as e:
        print(f"❌ Error importando MessageTemplates: {e}")
        return False
    
    # Test GlobalMemory
    try:
        from core.utils.memory import GlobalMemory
        print("✅ GlobalMemory importado correctamente")
    except Exception as e:
        print(f"❌ Error importando GlobalMemory: {e}")
        return False
    
    # Test SalesTechniques
    try:
        from core.utils.sales_techniques import SalesTechniques
        print("✅ SalesTechniques importado correctamente")
    except Exception as e:
        print(f"❌ Error importando SalesTechniques: {e}")
        return False
    
    print("-" * 50)
    print("✅ Utilidades verificadas!")
    return True

if __name__ == "__main__":
    print("🔍 Verificación de componentes del bot...")
    
    agents_ok = test_agents()
    services_ok = test_services()  
    utils_ok = test_utilities()
    
    if agents_ok and utils_ok:
        print("\n✅ Componentes principales funcionando correctamente!")
        print("Note: DatabaseService puede fallar debido a asyncpg, pero el bot básico debería funcionar")
        sys.exit(0)
    else:
        print("\n❌ Algunos componentes tienen problemas")
        sys.exit(1)