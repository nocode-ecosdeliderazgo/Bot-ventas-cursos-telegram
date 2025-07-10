#!/usr/bin/env python3
"""
Script para verificar la estructura del bot sin dependencias externas.
Verifica que todos los archivos críticos existen y tienen la estructura correcta.
"""

import os
import sys

def check_file_exists(filepath):
    """Verifica si un archivo existe y retorna su estado."""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        return True, size
    return False, 0

def verify_bot_structure():
    """Verifica la estructura completa del bot."""
    
    print("🔍 VERIFICACIÓN DE ESTRUCTURA DEL BOT BRENDA")
    print("=" * 60)
    
    # Archivos principales
    main_files = [
        "agente_ventas_telegram.py",
        "config/settings.py",
        "requirements.txt",
        ".env.example"
    ]
    
    # Servicios core
    service_files = [
        "core/services/database.py",
        "core/services/courseService.py",
        "core/services/resourceService.py",
        "core/services/supabase_service.py"
    ]
    
    # Agentes y herramientas
    agent_files = [
        "core/agents/smart_sales_agent.py",
        "core/agents/intelligent_sales_agent.py",
        "core/agents/agent_tools.py",
        "core/agents/conversation_processor.py"
    ]
    
    # Handlers de flujos
    handler_files = [
        "core/handlers/ads_flow.py",
        "core/handlers/contact_flow.py",
        "core/handlers/course_flow.py",
        "core/handlers/faq_flow.py"
    ]
    
    # Utils
    util_files = [
        "core/utils/memory.py",
        "core/utils/message_templates.py",
        "core/utils/course_templates.py",
        "core/utils/lead_scorer.py",
        "core/utils/message_parser.py"
    ]
    
    # Scripts de base de datos
    sql_files = [
        "database/sql/bot_resources_table.sql",
        "database/sql/insert_bot_resources.sql",
        "database/sql/base_estructura.sql"
    ]
    
    # Scripts de testing
    test_files = [
        "test_tools_system.py",
        "verificar_servicios.py",
        "verificar_agentes.py"
    ]
    
    # Documentación
    doc_files = [
        "CLAUDE.md",
        "PROGRESO_MIGRACION.md",
        "PLAN_IMPLEMENTACION_HERRAMIENTAS.md"
    ]
    
    all_categories = [
        ("📋 ARCHIVOS PRINCIPALES", main_files),
        ("🔧 SERVICIOS CORE", service_files),
        ("🤖 AGENTES Y HERRAMIENTAS", agent_files),
        ("📊 HANDLERS DE FLUJOS", handler_files),
        ("🛠️ UTILIDADES", util_files),
        ("💾 SCRIPTS SQL", sql_files),
        ("🧪 SCRIPTS DE TESTING", test_files),
        ("📚 DOCUMENTACIÓN", doc_files)
    ]
    
    total_files = 0
    existing_files = 0
    total_size = 0
    
    for category_name, file_list in all_categories:
        print(f"\n{category_name}")
        print("-" * 40)
        
        for filepath in file_list:
            total_files += 1
            exists, size = check_file_exists(filepath)
            
            if exists:
                existing_files += 1
                total_size += size
                size_kb = size / 1024
                status = "✅"
                if size_kb > 50:
                    size_info = f"({size_kb:.1f}KB)"
                else:
                    size_info = f"({size}B)"
            else:
                status = "❌"
                size_info = "(MISSING)"
            
            print(f"   {status} {filepath} {size_info}")
    
    # Verificar directorios críticos
    print(f"\n📁 DIRECTORIOS CRÍTICOS")
    print("-" * 40)
    
    critical_dirs = [
        "core/",
        "core/services/",
        "core/agents/",
        "core/handlers/",
        "core/utils/",
        "config/",
        "database/",
        "database/sql/",
        "data/",
        "memorias/"
    ]
    
    existing_dirs = 0
    for directory in critical_dirs:
        if os.path.exists(directory) and os.path.isdir(directory):
            status = "✅"
            existing_dirs += 1
        else:
            status = "❌"
        print(f"   {status} {directory}")
    
    # Resumen
    print(f"\n📊 RESUMEN DE VERIFICACIÓN")
    print("=" * 60)
    print(f"📄 Archivos verificados: {existing_files}/{total_files}")
    print(f"📁 Directorios encontrados: {existing_dirs}/{len(critical_dirs)}")
    print(f"💾 Tamaño total: {total_size/1024:.1f}KB")
    
    completion_percentage = (existing_files / total_files) * 100
    print(f"🎯 Completitud: {completion_percentage:.1f}%")
    
    if completion_percentage >= 90:
        print("🟢 ESTRUCTURA COMPLETA - BOT LISTO")
    elif completion_percentage >= 75:
        print("🟡 ESTRUCTURA MAYORMENTE COMPLETA")
    else:
        print("🔴 ESTRUCTURA INCOMPLETA")
    
    return existing_files, total_files

def verify_key_functions():
    """Verifica que las funciones clave están implementadas."""
    
    print(f"\n🔍 VERIFICACIÓN DE FUNCIONES CLAVE")
    print("=" * 60)
    
    # Verificar agent_tools.py
    try:
        with open("core/agents/agent_tools.py", "r", encoding="utf-8") as f:
            content = f.read()
            
        key_functions = [
            "contactar_asesor_directo",
            "mostrar_syllabus_interactivo", 
            "mostrar_comparativa_precios",
            "enviar_recursos_gratuitos",
            "enviar_preview_curso",
            "agendar_demo_personalizada",
            "mostrar_garantia_satisfaccion",
            "mostrar_testimonios_relevantes",
            "ResourceService"
        ]
        
        print("🔧 FUNCIONES EN agent_tools.py:")
        found_functions = 0
        for func in key_functions:
            if func in content:
                print(f"   ✅ {func}")
                found_functions += 1
            else:
                print(f"   ❌ {func}")
        
        print(f"\n📊 Funciones encontradas: {found_functions}/{len(key_functions)}")
        
    except FileNotFoundError:
        print("❌ core/agents/agent_tools.py no encontrado")
    
    # Verificar resourceService.py
    try:
        with open("core/services/resourceService.py", "r", encoding="utf-8") as f:
            content = f.read()
            
        resource_methods = [
            "get_resource_url",
            "get_resources_by_type", 
            "get_course_resources",
            "get_session_resources"
        ]
        
        print("\n💾 MÉTODOS EN resourceService.py:")
        found_methods = 0
        for method in resource_methods:
            if method in content:
                print(f"   ✅ {method}")
                found_methods += 1
            else:
                print(f"   ❌ {method}")
        
        print(f"\n📊 Métodos encontrados: {found_methods}/{len(resource_methods)}")
        
    except FileNotFoundError:
        print("❌ core/services/resourceService.py no encontrado")

def verify_sql_scripts():
    """Verifica que los scripts SQL están completos."""
    
    print(f"\n💾 VERIFICACIÓN DE SCRIPTS SQL")
    print("=" * 60)
    
    sql_files_to_check = [
        ("bot_resources_table.sql", ["CREATE TABLE bot_resources", "bot_course_resources", "bot_session_resources"]),
        ("insert_bot_resources.sql", ["INSERT INTO bot_resources", "demo_personalizada", "curso_preview"]),
        ("base_estructura.sql", ["CREATE TABLE", "courses", "user_leads"])
    ]
    
    for sql_file, expected_content in sql_files_to_check:
        filepath = f"database/sql/{sql_file}"
        print(f"\n📄 {sql_file}:")
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            for expected in expected_content:
                if expected in content:
                    print(f"   ✅ Contiene: {expected}")
                else:
                    print(f"   ❌ Falta: {expected}")
                    
        except FileNotFoundError:
            print(f"   ❌ Archivo no encontrado: {filepath}")

if __name__ == "__main__":
    print("🚀 INICIANDO VERIFICACIÓN COMPLETA DEL BOT BRENDA")
    print("=" * 60)
    
    # Verificar estructura
    existing, total = verify_bot_structure()
    
    # Verificar funciones clave
    verify_key_functions()
    
    # Verificar scripts SQL
    verify_sql_scripts()
    
    print(f"\n🎉 VERIFICACIÓN COMPLETADA")
    print("=" * 60)
    
    if existing >= total * 0.9:
        print("✅ EL BOT ESTÁ LISTO PARA TESTING CON DEPENDENCIAS")
        print("📋 Próximos pasos:")
        print("   1. Instalar dependencias: pip install -r requirements.txt")
        print("   2. Configurar variables de entorno")
        print("   3. Ejecutar: python agente_ventas_telegram.py")
    else:
        print("❌ ESTRUCTURA INCOMPLETA - REVISAR ARCHIVOS FALTANTES")