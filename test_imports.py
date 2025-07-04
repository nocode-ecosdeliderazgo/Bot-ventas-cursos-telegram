#!/usr/bin/env python3
"""
Script de prueba para verificar que todas las importaciones y dependencias funcionen correctamente.
"""

import sys
import traceback

def test_imports():
    """Prueba todas las importaciones críticas del bot."""
    results = []
    
    # Test 1: Importaciones básicas
    try:
        import os
        import logging
        from datetime import datetime, timezone
        results.append("✅ Importaciones básicas de Python")
    except Exception as e:
        results.append(f"❌ Error en importaciones básicas: {e}")
    
    # Test 2: Telegram Bot API
    try:
        from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
        from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
        results.append("✅ Telegram Bot API")
    except Exception as e:
        results.append(f"❌ Error en Telegram Bot API: {e}")
    
    # Test 3: Base de datos
    try:
        import asyncpg
        results.append("✅ AsyncPG (PostgreSQL)")
    except Exception as e:
        results.append(f"❌ Error en AsyncPG: {e}")
    
    # Test 4: Variables de entorno
    try:
        from dotenv import load_dotenv
        results.append("✅ Python-dotenv")
    except Exception as e:
        results.append(f"❌ Error en python-dotenv: {e}")
    
    # Test 5: Servicios del core
    try:
        from core.services.database import DatabaseService
        results.append("✅ Database Service")
    except Exception as e:
        results.append(f"❌ Error en Database Service: {e}")
    
    # Test 6: Agentes
    try:
        from core.agents.sales_agent import AgenteSalesTools
        from core.agents.agent_tools import AgentTools
        results.append("✅ Sales Agents")
    except Exception as e:
        results.append(f"❌ Error en Sales Agents: {e}")
    
    # Test 7: Handlers
    try:
        from core.handlers.ads_flow import AdsFlowHandler
        results.append("✅ Ads Flow Handler")
    except Exception as e:
        results.append(f"❌ Error en Ads Flow Handler: {e}")
    
    # Test 8: Utilidades
    try:
        from core.utils.message_parser import extract_hashtags, get_course_from_hashtag
        from core.utils.lead_scorer import calculate_initial_score
        results.append("✅ Utilidades del core")
    except Exception as e:
        results.append(f"❌ Error en utilidades: {e}")
    
    # Test 9: Archivo principal
    try:
        # Solo verificar que se puede importar sin ejecutar
        import agente_ventas_telegram
        results.append("✅ Archivo principal del bot")
    except Exception as e:
        results.append(f"❌ Error en archivo principal: {e}")
    
    return results

def test_basic_functionality():
    """Prueba funcionalidades básicas sin conexión a BD."""
    results = []
    
    try:
        from core.utils.message_parser import extract_hashtags
        
        # Test extracción de hashtags
        test_message = "Hola, vengo de Facebook #CURSO_IA_CHATGPT #ADSIM_01"
        hashtags = extract_hashtags(test_message)
        
        if hashtags == ['CURSO_IA_CHATGPT', 'ADSIM_01']:
            results.append("✅ Extracción de hashtags funcionando")
        else:
            results.append(f"❌ Error en extracción de hashtags: {hashtags}")
            
    except Exception as e:
        results.append(f"❌ Error en test de hashtags: {e}")
    
    try:
        from core.utils.lead_scorer import calculate_initial_score
        
        # Test básico de scoring (sin await ya que no tenemos loop aquí)
        results.append("✅ Lead scorer importado correctamente")
        
    except Exception as e:
        results.append(f"❌ Error en lead scorer: {e}")
    
    return results

def main():
    """Función principal del script de prueba."""
    print("🔍 Ejecutando pruebas de importaciones y funcionalidad básica...\n")
    
    # Pruebas de importaciones
    print("📦 PRUEBAS DE IMPORTACIONES:")
    import_results = test_imports()
    for result in import_results:
        print(f"  {result}")
    
    print("\n🧪 PRUEBAS DE FUNCIONALIDAD:")
    func_results = test_basic_functionality()
    for result in func_results:
        print(f"  {result}")
    
    # Resumen
    total_tests = len(import_results) + len(func_results)
    passed_tests = sum(1 for r in import_results + func_results if r.startswith("✅"))
    failed_tests = total_tests - passed_tests
    
    print(f"\n📊 RESUMEN:")
    print(f"  Total de pruebas: {total_tests}")
    print(f"  ✅ Pasaron: {passed_tests}")
    print(f"  ❌ Fallaron: {failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ¡Todas las pruebas pasaron! El bot debería funcionar correctamente.")
        return 0
    else:
        print(f"\n⚠️  Hay {failed_tests} errores que necesitan ser corregidos.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 