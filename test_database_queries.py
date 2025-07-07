#!/usr/bin/env python3
"""
Test de consultas a la base de datos para verificar acceso correcto.
Prueba las mismas consultas que usa el agente inteligente.
"""

import asyncio
import sys
import os
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.services.database import DatabaseService
from core.services.courseService import CourseService
from config.settings import settings

# ID del curso que mapea #CURSO_IA_CHATGPT
COURSE_ID = 'a392bf83-4908-4807-89a9-95d0acc807c9'

async def test_database_connection():
    """Prueba la conexión básica a la base de datos."""
    print("=" * 60)
    print("🔍 TESTING CONEXIÓN A BASE DE DATOS")
    print("=" * 60)
    
    try:
        db = DatabaseService(settings.DATABASE_URL)
        await db.connect()
        print("✅ Conexión a base de datos: EXITOSA")
        return db
    except Exception as e:
        print(f"❌ Error conectando a BD: {e}")
        return None

async def test_course_details(course_service, course_id):
    """Prueba obtener detalles completos del curso."""
    print(f"\n📚 CONSULTANDO DETALLES DEL CURSO: {course_id}")
    print("-" * 50)
    
    try:
        course_details = await course_service.getCourseDetails(course_id)
        if course_details:
            print("✅ Detalles del curso obtenidos exitosamente:")
            print(f"  • Nombre: {course_details.get('name', 'N/A')}")
            print(f"  • Descripción corta: {course_details.get('short_description', 'N/A')[:100]}...")
            print(f"  • Duración: {course_details.get('total_duration', 'N/A')}")
            print(f"  • Precio USD: ${course_details.get('price_usd', 'N/A')}")
            print(f"  • Nivel: {course_details.get('level', 'N/A')}")
            print(f"  • Herramientas: {course_details.get('tools_used', 'N/A')}")
            print(f"  • Prerrequisitos: {course_details.get('prerequisites', 'N/A')}")
            print(f"  • Horario: {course_details.get('schedule', 'N/A')}")
            return course_details
        else:
            print("❌ No se obtuvieron detalles del curso")
            return None
    except Exception as e:
        print(f"❌ Error obteniendo detalles: {e}")
        return None

async def test_course_modules(course_service, course_id):
    """Prueba obtener módulos del curso."""
    print(f"\n🎓 CONSULTANDO MÓDULOS DEL CURSO: {course_id}")
    print("-" * 50)
    
    try:
        modules = await course_service.getCourseModules(course_id)
        if modules:
            print(f"✅ Se encontraron {len(modules)} módulos:")
            for i, module in enumerate(modules, 1):
                print(f"  {i}. {module.get('name', 'Sin nombre')}")
                if module.get('description'):
                    print(f"     📝 {module.get('description')[:100]}...")
                if module.get('duration'):
                    print(f"     ⏱️ Duración: {module.get('duration')}")
                print()
            return modules
        else:
            print("❌ No se encontraron módulos para este curso")
            return []
    except Exception as e:
        print(f"❌ Error obteniendo módulos: {e}")
        return []

async def test_course_bonuses(course_service, course_id):
    """Prueba obtener bonos disponibles del curso."""
    print(f"\n🎁 CONSULTANDO BONOS DISPONIBLES: {course_id}")
    print("-" * 50)
    
    try:
        bonuses = await course_service.getAvailableBonuses(course_id)
        if bonuses:
            print(f"✅ Se encontraron {len(bonuses)} bonos:")
            for i, bonus in enumerate(bonuses, 1):
                print(f"  {i}. {bonus.get('name', 'Sin nombre')}")
                print(f"     💰 Valor: ${bonus.get('original_value', 'N/A')}")
                print(f"     📅 Expira: {bonus.get('expires_at', 'N/A')}")
                print(f"     🎯 Propuesta: {bonus.get('value_proposition', 'N/A')}")
                print(f"     ✅ Activo: {bonus.get('active', False)}")
                print()
            return bonuses
        else:
            print("❌ No se encontraron bonos para este curso")
            return []
    except Exception as e:
        print(f"❌ Error obteniendo bonos: {e}")
        return []

async def test_course_search(course_service):
    """Prueba búsqueda de cursos."""
    print(f"\n🔍 PROBANDO BÚSQUEDA DE CURSOS")
    print("-" * 50)
    
    search_terms = ["IA", "ChatGPT", "inteligencia artificial"]
    
    for term in search_terms:
        try:
            results = await course_service.searchCourses(term)
            print(f"  Búsqueda '{term}': {len(results) if results else 0} resultados")
            if results:
                for result in results[:3]:  # Mostrar solo los primeros 3
                    print(f"    - {result.get('name', 'Sin nombre')}")
        except Exception as e:
            print(f"  ❌ Error buscando '{term}': {e}")

async def test_course_long_description(course_service, course_id):
    """Prueba específica para verificar acceso al campo long_description."""
    print(f"\n📝 VERIFICANDO LONG_DESCRIPTION DEL CURSO: {course_id}")
    print("-" * 50)
    
    try:
        # Probar con el método directo de consulta a la BD
        db = course_service.db
        query = """
        SELECT id, name, short_description, long_description, 
               total_duration, price_usd, level
        FROM courses 
        WHERE id = $1
        """
        
        result = await db.fetch_one(query, course_id)
        
        if result:
            print("✅ Consulta directa a BD exitosa:")
            print(f"  • ID: {result['id']}")
            print(f"  • Nombre: {result['name']}")
            print(f"  • Descripción corta: {result['short_description'][:100] if result['short_description'] else 'N/A'}...")
            print(f"  • Duración: {result['total_duration']}")
            print(f"  • Precio USD: ${result['price_usd']}")
            print(f"  • Nivel: {result['level']}")
            
            # Verificar específicamente long_description
            if result['long_description']:
                print(f"\n📖 LONG_DESCRIPTION ENCONTRADA:")
                print(f"  • Longitud: {len(result['long_description'])} caracteres")
                print(f"  • Primeros 300 caracteres:")
                print(f"    {result['long_description'][:300]}...")
                
                # Buscar módulos en la descripción
                description = result['long_description'].lower()
                module_keywords = ['módulo', 'module', 'unidad', 'lección', 'capítulo']
                found_modules = []
                
                for keyword in module_keywords:
                    if keyword in description:
                        found_modules.append(keyword)
                
                if found_modules:
                    print(f"  • Palabras clave de módulos encontradas: {', '.join(found_modules)}")
                else:
                    print("  • ⚠️ No se encontraron palabras clave de módulos")
                
                return result
            else:
                print("❌ LONG_DESCRIPTION está VACÍA o es NULL")
                return result
        else:
            print("❌ No se encontró el curso en la BD")
            return None
            
    except Exception as e:
        print(f"❌ Error en consulta directa: {e}")
        return None

def analyze_course_for_careers(course_details, modules):
    """Analiza cómo el curso puede beneficiar a diferentes carreras."""
    print(f"\n💼 ANÁLISIS PARA DIFERENTES CARRERAS")
    print("=" * 60)
    
    if not course_details or not modules:
        print("❌ No hay suficientes datos para el análisis")
        return
    
    course_name = course_details.get('name', '')
    tools_used = course_details.get('tools_used', [])
    
    print(f"📚 Curso: {course_name}")
    print(f"🛠️ Herramientas: {', '.join(tools_used) if tools_used else 'No especificadas'}")
    print(f"📖 Total módulos: {len(modules)}")
    
    # Análisis para 3 carreras específicas
    careers_analysis = {
        "Marketing Digital": {
            "beneficios": [
                "Automatización de creación de contenido con ChatGPT",
                "Generación de imágenes para campañas publicitarias",
                "Optimización de textos publicitarios y copy",
                "Análisis y resumen de tendencias del mercado"
            ],
            "modulos_relevantes": ["ChatGPT como asistente", "Creación de documentos", "Generación de imágenes"]
        },
        "Ingeniería en Sistemas": {
            "beneficios": [
                "Automatización de documentación técnica",
                "Generación de código y comentarios",
                "Creación de diagramas y presentaciones técnicas",
                "Optimización de procesos de desarrollo"
            ],
            "modulos_relevantes": ["ChatGPT como asistente", "Creación de documentos", "Proyecto integrado"]
        },
        "Administración de Empresas": {
            "beneficios": [
                "Automatización de reportes ejecutivos",
                "Creación de presentaciones profesionales",
                "Análisis de datos y tendencias empresariales",
                "Optimización de comunicación interna"
            ],
            "modulos_relevantes": ["Creación de documentos", "ChatGPT como asistente", "Proyecto integrado"]
        }
    }
    
    for career, analysis in careers_analysis.items():
        print(f"\n🎯 {career.upper()}")
        print(f"   💡 Beneficios principales:")
        for benefit in analysis["beneficios"]:
            print(f"     • {benefit}")
        print(f"   📚 Módulos más relevantes:")
        for module in analysis["modulos_relevantes"]:
            print(f"     • {module}")

async def main():
    """Función principal del test."""
    print("🚀 INICIANDO TEST DE CONSULTAS A BASE DE DATOS")
    print(f"⏰ Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Curso objetivo: {COURSE_ID}")
    
    # 1. Probar conexión
    db = await test_database_connection()
    if not db:
        return
    
    # 2. Inicializar CourseService
    course_service = CourseService(db)
    
    # 3. Probar consultas específicas
    course_details = await test_course_details(course_service, COURSE_ID)
    modules = await test_course_modules(course_service, COURSE_ID)
    bonuses = await test_course_bonuses(course_service, COURSE_ID)
    
    # 4. Verificar específicamente long_description
    long_desc_result = await test_course_long_description(course_service, COURSE_ID)
    
    # 4. Probar búsquedas
    await test_course_search(course_service)
    
    # 5. Análisis para carreras
    analyze_course_for_careers(course_details, modules)
    
    # 6. Resumen final
    print(f"\n📊 RESUMEN DEL TEST")
    print("=" * 60)
    print(f"✅ Conexión BD: {'OK' if db else 'FALLÓ'}")
    print(f"✅ Detalles curso: {'OK' if course_details else 'FALLÓ'}")
    print(f"✅ Módulos: {len(modules) if modules else 0} encontrados")
    print(f"✅ Bonos: {len(bonuses) if bonuses else 0} encontrados")
    
    if modules:
        print(f"\n📚 MÓDULOS REALES CONFIRMADOS:")
        for i, module in enumerate(modules, 1):
            print(f"  {i}. {module.get('name', 'Sin nombre')}")
    else:
        print(f"\n⚠️ NO SE ENCONTRARON MÓDULOS - Esto explica por qué el agente inventa")
    
    # Cerrar conexión
    if hasattr(db, 'disconnect'):
        await db.disconnect()
    
    print(f"\n🎉 TEST COMPLETADO")

if __name__ == "__main__":
    asyncio.run(main())