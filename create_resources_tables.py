#!/usr/bin/env python3
"""
Script para crear las tablas de recursos del bot en la base de datos.
Ejecuta los SQLs necesarios para soportar las herramientas del bot.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.services.database import DatabaseService
from config.settings import settings

async def create_resources_tables():
    """Crea las tablas de recursos y inserta datos iniciales"""
    
    print("🚀 Creando tablas de recursos para el bot...")
    
    # Conectar a la base de datos
    db = DatabaseService(settings.DATABASE_URL)
    await db.connect()
    
    try:
        # 1. Leer y ejecutar script de creación de tablas
        print("📋 Paso 1: Creando tablas de recursos...")
        with open("database/sql/bot_resources_table.sql", "r") as f:
            create_tables_sql = f.read()
        
        async with db.pool.acquire() as connection:
            await connection.execute(create_tables_sql)
            print("✅ Tablas de recursos creadas exitosamente")
        
        # 2. Leer y ejecutar script de inserción de datos
        print("📋 Paso 2: Insertando recursos básicos...")
        with open("database/sql/insert_bot_resources.sql", "r") as f:
            insert_resources_sql = f.read()
        
        async with db.pool.acquire() as connection:
            await connection.execute(insert_resources_sql)
            print("✅ Recursos básicos insertados exitosamente")
        
        # 3. Leer y ejecutar script de vinculación
        print("📋 Paso 3: Vinculando recursos a cursos...")
        with open("database/sql/link_resources_to_courses.sql", "r") as f:
            link_resources_sql = f.read()
        
        async with db.pool.acquire() as connection:
            await connection.execute(link_resources_sql)
            print("✅ Recursos vinculados a cursos exitosamente")
        
        # 4. Verificar que todo se creó correctamente
        print("📋 Paso 4: Verificando creación...")
        async with db.pool.acquire() as connection:
            # Contar recursos
            resource_count = await connection.fetchval("SELECT COUNT(*) FROM bot_resources")
            print(f"✅ Total de recursos creados: {resource_count}")
            
            # Contar recursos por curso
            course_resources = await connection.fetchval(
                "SELECT COUNT(*) FROM bot_course_resources WHERE course_id = 'c76bc3dd-502a-4b99-8c6c-3f9fce33a14b'::uuid"
            )
            print(f"✅ Recursos vinculados al curso principal: {course_resources}")
            
            # Contar recursos por sesión
            session_resources = await connection.fetchval(
                """
                SELECT COUNT(*) FROM bot_session_resources bsr
                JOIN ai_course_sessions s ON bsr.session_id = s.id
                WHERE s.course_id = 'c76bc3dd-502a-4b99-8c6c-3f9fce33a14b'::uuid
                """
            )
            print(f"✅ Recursos vinculados a sesiones: {session_resources}")
        
        print("\n🎉 ¡Todas las tablas de recursos creadas exitosamente!")
        print("📊 Resumen:")
        print(f"   - {resource_count} recursos totales")
        print(f"   - {course_resources} recursos del curso principal")
        print(f"   - {session_resources} recursos de sesiones")
        
        # 5. Mostrar algunos ejemplos de recursos
        print("\n📋 Ejemplos de recursos creados:")
        async with db.pool.acquire() as connection:
            examples = await connection.fetch(
                """
                SELECT resource_key, resource_title, resource_type, resource_url
                FROM bot_resources
                WHERE resource_type IN ('demo', 'pdf', 'video', 'testimonios')
                ORDER BY resource_type
                LIMIT 8
                """
            )
            
            for example in examples:
                print(f"   🔗 {example['resource_type']}: {example['resource_title']}")
                print(f"      Key: {example['resource_key']}")
                print(f"      URL: {example['resource_url']}")
                print()
        
    except Exception as e:
        print(f"❌ Error creando tablas de recursos: {e}")
        raise
    
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(create_resources_tables())