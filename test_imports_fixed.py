#!/usr/bin/env python3
"""
Script de prueba para verificar que todas las importaciones y dependencias funcionen correctamente.
"""

import sys
import traceback

def test_imports():
    """Prueba todas las importaciones criticas del bot."""
    print("Iniciando test de importaciones...")
    
    tests = [
        # Core services
        ("core.services.database", "DatabaseService"),
        ("core.services.courseService", "CourseService"),
        ("core.services.promptService", "PromptService"),
        
        # Agents
        ("core.agents.smart_sales_agent", "SmartSalesAgent"),
        ("core.agents.intelligent_sales_agent", "IntelligentSalesAgent"),
        ("core.agents.agent_tools", "AgentTools"),
        
        # Utils
        ("core.utils.memory", "GlobalMemory", "LeadMemory"),
        ("core.utils.lead_scorer", "LeadScorer"),
        
        # Configuration
        ("config.settings", "settings"),
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        module_name = test[0]
        imports = test[1:] if len(test) > 1 else []
        
        try:
            if imports:
                import_str = f"from {module_name} import {', '.join(imports)}"
            else:
                import_str = f"import {module_name}"
                
            exec(import_str)
            print(f"OK {import_str}")
            passed += 1
        except Exception as e:
            print(f"ERROR {import_str} - {str(e)}")
            failed += 1
    
    print(f"\nResultados:")
    print(f"Exitosos: {passed}")
    print(f"Fallidos: {failed}")
    
    return failed == 0

if __name__ == "__main__":
    print("Bot Ventas Telegram - Test Suite")
    print("=" * 50)
    
    imports_ok = test_imports()
    
    if imports_ok:
        print("TODOS LOS TESTS PASARON - El bot esta listo!")
        sys.exit(0)
    else:
        print("ALGUNOS TESTS FALLARON - Revisar errores arriba")
        sys.exit(1)