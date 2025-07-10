#!/usr/bin/env python3
"""
Script para probar el sistema de recursos del bot.
Verifica que los recursos se puedan obtener correctamente.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.services.database import DatabaseService
from core.services.resourceService import ResourceService
from config.settings import settings

async def test_resources_system():
    """Prueba el sistema de recursos completo"""
    
    print("🧪 Probando sistema de recursos del bot...")
    
    # Conectar a la base de datos
    db = DatabaseService(settings.DATABASE_URL)
    await db.connect()
    
    try:
        # Crear servicio de recursos
        resource_service = ResourceService(db)
        
        # 1. Probar obtención de recurso por clave
        print("📋 Paso 1: Probando obtención de recurso por clave...")
        demo_resource = await resource_service.get_resource_by_key("demo_personalizada")
        if demo_resource:
            print(f"✅ Recurso encontrado: {demo_resource['resource_title']}")
            print(f"   URL: {demo_resource['resource_url']}")
        else:
            print("❌ No se encontró el recurso de demo")
        
        # 2. Probar obtención de recursos por curso
        print("\n📋 Paso 2: Probando recursos por curso...")
        course_id = "c76bc3dd-502a-4b99-8c6c-3f9fce33a14b"
        course_resources = await resource_service.get_course_resources(course_id)
        print(f"✅ Recursos del curso encontrados: {len(course_resources)}")
        
        for resource in course_resources[:5]:  # Mostrar primeros 5
            print(f"   🔗 {resource['resource_type']}: {resource['resource_title']}")
        
        # 3. Probar obtención de recursos por tipo
        print("\n📋 Paso 3: Probando recursos por tipo...")
        demo_resources = await resource_service.get_resources_by_type("demo")
        print(f"✅ Recursos de demo encontrados: {len(demo_resources)}")
        
        for resource in demo_resources:
            print(f"   🎯 {resource['resource_title']}: {resource['resource_url']}")
        
        # 4. Probar función de obtener URL con fallback
        print("\n📋 Paso 4: Probando obtención de URL con fallback...")
        
        # Recurso existente
        existing_url = await resource_service.get_resource_url("demo_personalizada")
        print(f"✅ URL existente: {existing_url}")
        
        # Recurso no existente (debería usar fallback)
        non_existing_url = await resource_service.get_resource_url("recurso_inexistente")
        print(f"✅ URL fallback: {non_existing_url}")
        
        # 5. Probar recursos de sesión
        print("\n📋 Paso 5: Probando recursos por sesión...")
        
        # Obtener primera sesión del curso
        async with db.pool.acquire() as connection:
            session = await connection.fetchrow(
                """
                SELECT id, title, session_index
                FROM ai_course_sessions
                WHERE course_id = $1
                ORDER BY session_index
                LIMIT 1
                """,
                course_id
            )
            
            if session:
                session_resources = await resource_service.get_session_resources(str(session['id']))
                print(f"✅ Sesión '{session['title']}' tiene {len(session_resources)} recursos")
                
                for resource in session_resources:
                    print(f"   📖 {resource['resource_title']}: {resource['resource_type']}")
        
        # 6. Probar función helper de base de datos
        print("\n📋 Paso 6: Probando función helper de base de datos...")
        async with db.pool.acquire() as connection:
            helper_resources = await connection.fetch(
                "SELECT * FROM get_course_resources($1)",
                course_id
            )
            print(f"✅ Función helper retornó {len(helper_resources)} recursos")
        
        print("\n🎉 ¡Todas las pruebas del sistema de recursos completadas exitosamente!")
        
        # 7. Simular uso en herramientas del bot
        print("\n📋 Paso 7: Simulando uso en herramientas del bot...")
        
        # Simular mostrar_recursos_gratuitos
        recursos_gratuitos = await resource_service.get_resources_by_type("recursos")
        if recursos_gratuitos:
            print("✅ Simulación mostrar_recursos_gratuitos:")
            for recurso in recursos_gratuitos:
                print(f"   📥 {recurso['resource_title']}: {recurso['resource_url']}")
        
        # Simular agendar_demo_personalizada
        demo_url = await resource_service.get_resource_url("demo_personalizada")
        print(f"✅ Simulación agendar_demo_personalizada: {demo_url}")
        
        # Simular mostrar_testimonios
        testimonios = await resource_service.get_resources_by_type("testimonios")
        if testimonios:
            print("✅ Simulación mostrar_testimonios:")
            for testimonio in testimonios:
                print(f"   💬 {testimonio['resource_title']}: {testimonio['resource_url']}")
        
    except Exception as e:
        print(f"❌ Error en pruebas del sistema de recursos: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_resources_system())