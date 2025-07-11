#!/usr/bin/env python3
"""
Test script para verificar que las herramientas están funcionando correctamente.
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.services.database import DatabaseService
from core.agents.agent_tools import AgentTools
from config.settings import settings

async def test_tools():
    """Test de las herramientas principales."""
    
    print("🔧 Testing AgentTools functionality")
    print("=" * 50)
    
    # Inicializar base de datos
    db = DatabaseService(settings.DATABASE_URL)
    await db.connect()
    
    # Inicializar herramientas
    agent_tools = AgentTools(db, None)
    
    # Curso de prueba
    test_course_id = "c76bc3dd-502a-4b99-8c6c-3f9fce33a14b"
    test_user_id = "test_user_123"
    
    print(f"📚 Testing tools with course: {test_course_id}")
    print()
    
    try:
        # Test 1: enviar_recursos_gratuitos
        print("1. Testing enviar_recursos_gratuitos:")
        result = await agent_tools.enviar_recursos_gratuitos(test_user_id, test_course_id)
        print(f"   Result type: {result.get('type', 'unknown')}")
        print(f"   Resources count: {len(result.get('resources', []))}")
        print("   ✅ SUCCESS" if result.get('resources') else "   ❌ FAILED")
        print()
        
        # Test 2: mostrar_syllabus_interactivo
        print("2. Testing mostrar_syllabus_interactivo:")
        result = await agent_tools.mostrar_syllabus_interactivo(test_user_id, test_course_id)
        print(f"   Result type: {result.get('type', 'unknown')}")
        print(f"   Resources count: {len(result.get('resources', []))}")
        print("   ✅ SUCCESS" if result.get('resources') else "   ❌ FAILED")
        print()
        
        # Test 3: mostrar_comparativa_precios
        print("3. Testing mostrar_comparativa_precios:")
        result = await agent_tools.mostrar_comparativa_precios(test_user_id, test_course_id)
        print(f"   Result type: {result.get('type', 'unknown')}")
        content = result.get('content', '')
        print(f"   Has content: {'✅ YES' if content else '❌ NO'}")
        print(f"   Has price info: {'✅ YES' if '$' in content else '❌ NO'}")
        print("   ✅ SUCCESS" if content and '$' in content else "   ❌ FAILED")
        print()
        
        # Test 4: Course data retrieval
        print("4. Testing course data retrieval:")
        course_data = await db.get_course_details(test_course_id)
        if course_data:
            print(f"   Course name: {course_data.get('name', 'unknown')}")
            print(f"   Course price: {course_data.get('price', 'unknown')}")
            print("   ✅ SUCCESS")
        else:
            print("   ❌ FAILED - No course data found")
        print()
        
    except Exception as e:
        print(f"❌ ERROR during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.disconnect()
    
    print("=" * 50)
    print("🏁 Testing completed")

if __name__ == "__main__":
    asyncio.run(test_tools())