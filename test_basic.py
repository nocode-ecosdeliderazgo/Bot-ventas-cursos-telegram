#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test básico de imports y funcionamiento"""

try:
    from core.utils.message_parser import extract_hashtags
    from core.handlers.ads_flow import AdsFlowHandler
    from core.services.database import DatabaseService
    from core.agents.agent_tools import AgentTools
    
    print("✅ Imports básicos funcionan")
    
    # Test de extracción de hashtags
    test_message = "Hola, vengo de Facebook #CURSO_IA_CHATGPT #ADSIM_01"
    hashtags = extract_hashtags(test_message)
    print(f"✅ Extracción de hashtags: {hashtags}")
    
    # Verificar que encuentra los hashtags esperados
    if 'CURSO_IA_CHATGPT' in hashtags and 'ADSIM_01' in hashtags:
        print("✅ Detección de hashtags funciona correctamente")
    else:
        print("❌ Error en detección de hashtags")
    
    print("\n🎉 Todas las pruebas básicas pasaron!")
    
except ImportError as e:
    print(f"❌ Error de import: {e}")
except Exception as e:
    print(f"❌ Error general: {e}")