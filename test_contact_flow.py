#!/usr/bin/env python3
"""
Test script para verificar el flujo de contacto con asesor
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_contact_flow():
    """Simula el flujo de contacto con asesor"""
    print("🧪 TESTING FLUJO DE CONTACTO CON ASESOR")
    print("=" * 50)
    
    # Simular detección de palabras clave
    test_messages = [
        "Quiero contactar un asesor",
        "¿Puedo hablar con alguien?",
        "Necesito ayuda especializada",
        "¿Tienen soporte?",
        "Quiero hacer una consulta"
    ]
    
    # Palabras clave que deberían activar el flujo
    contact_keywords = ['asesor', 'contactar', 'hablar', 'ayuda', 'consulta', 'especialista', 'soporte']
    
    print("🔍 Probando detección de palabras clave:")
    for message in test_messages:
        detected = any(keyword in message.lower() for keyword in contact_keywords)
        status = "✅ DETECTADO" if detected else "❌ NO DETECTADO"
        print(f"   '{message}' → {status}")
    
    print("\n🔧 Verificando funciones importantes:")
    
    # 1. Verificar que existe contactar_asesor_directo
    try:
        from core.agents.agent_tools import AgentTools
        print("✅ AgentTools importado correctamente")
        
        # Verificar que la función existe
        if hasattr(AgentTools, 'contactar_asesor_directo'):
            print("✅ contactar_asesor_directo existe en AgentTools")
        else:
            print("❌ contactar_asesor_directo NO existe en AgentTools")
            
        if hasattr(AgentTools, 'activar_flujo_contacto_asesor'):
            print("✅ activar_flujo_contacto_asesor existe en AgentTools")
        else:
            print("❌ activar_flujo_contacto_asesor NO existe en AgentTools")
            
    except Exception as e:
        print(f"❌ Error importando AgentTools: {e}")
    
    # 2. Verificar que existe IntelligentSalesAgentTools
    try:
        from core.agents.intelligent_sales_agent_tools import IntelligentSalesAgentTools
        print("✅ IntelligentSalesAgentTools importado correctamente")
        
        if hasattr(IntelligentSalesAgentTools, '_activate_tools_based_on_intent'):
            print("✅ _activate_tools_based_on_intent existe")
        else:
            print("❌ _activate_tools_based_on_intent NO existe")
            
    except Exception as e:
        print(f"❌ Error importando IntelligentSalesAgentTools: {e}")
    
    # 3. Verificar el flujo de contacto
    try:
        from core.handlers.contact_flow import start_contact_flow, send_advisor_email
        print("✅ contact_flow functions importadas correctamente")
        
        # Simular datos del usuario
        user_data = {
            "name": "Usuario Test",
            "email": "test@example.com",
            "phone": "+1234567890",
            "course_name": "Curso de IA para Profesionales"
        }
        
        # Probar envío de email (sin realmente enviar)
        print(f"📧 Simulando envío de email con datos: {user_data}")
        
    except Exception as e:
        print(f"❌ Error importando contact_flow: {e}")
    
    print("\n✅ TEST COMPLETADO")
    print("=" * 50)
    print("🎯 PRÓXIMOS PASOS:")
    print("1. Ejecutar el bot real para probar")
    print("2. Enviar mensaje: 'Quiero contactar un asesor'")
    print("3. Verificar que aparezca el botón de contacto")
    print("4. Completar el flujo con email y teléfono")
    print("5. Verificar que se envíe el email al asesor")

if __name__ == "__main__":
    asyncio.run(test_contact_flow())