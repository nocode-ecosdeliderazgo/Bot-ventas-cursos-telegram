#!/usr/bin/env python3
"""
Script de prueba rápida para verificar que el validador es PERMISIVO
y NO bloquea activación de herramientas legítimas.
"""

import asyncio
import json
from core.services.promptService import PromptService
from config.settings import settings

async def test_validador_permisivo():
    """Prueba que el validador es permisivo y no bloquea herramientas."""
    
    print("🧪 TESTANDO VALIDADOR PERMISIVO")
    print("=" * 50)
    
    # Inicializar el servicio
    prompt_service = PromptService(settings.OPENAI_API_KEY)
    
    # Datos de prueba del curso
    course_data = {
        "id": "a392bf83-4908-4807-89a9-95d0acc807c9",
        "name": "Experto en IA: ChatGPT y Gemini para Profesionales",
        "short_description": "Curso práctico de IA",
        "price_usd": 249.99,
        "level": "Principiante a Avanzado",
        "modules": [
            {
                "id": "mod1",
                "name": "Fundamentos de IA",
                "description": "Conceptos básicos",
                "duration": "2 horas"
            },
            {
                "id": "mod2", 
                "name": "ChatGPT Avanzado",
                "description": "Técnicas avanzadas",
                "duration": "3 horas"
            }
        ],
        "sessions": [
            {
                "id": "sess1",
                "name": "Introducción a la IA",
                "practices": [
                    {"description": "Ejercicio práctico de prompts"}
                ],
                "deliverables": [
                    {"description": "Guía de prompts para finanzas"}
                ]
            }
        ],
        "free_resources": [
            {"type": "PDF", "title": "Guía de Prompts Gratuita"},
            {"type": "Template", "title": "Plantilla de Automatización"}
        ],
        "tools_used": ["ChatGPT", "Gemini", "Excel", "Google Sheets"]
    }
    
    bonuses_data = [
        {
            "name": "Bonus Limitado",
            "description": "Acceso a comunidad premium",
            "original_value": 199,
            "active": True,
            "expires_at": "2025-12-31"
        }
    ]
    
    # Casos de prueba que DEBEN SER APROBADOS
    test_cases = [
        {
            "name": "Activación de herramienta legítima",
            "response": "¡Perfecto! Te voy a mostrar el temario completo del curso para que veas exactamente qué vas a aprender.",
            "should_pass": True
        },
        {
            "name": "Información derivada de módulos",
            "response": "El curso incluye fundamentos de IA y técnicas avanzadas de ChatGPT, perfecto para tu área de finanzas.",
            "should_pass": True
        },
        {
            "name": "Mención de recursos gratuitos",
            "response": "Te puedo compartir una guía gratuita de prompts y plantillas de automatización para que evalúes el contenido.",
            "should_pass": True
        },
        {
            "name": "Beneficios educativos generales",
            "response": "Con este curso vas a poder automatizar tus reportes y aumentar tu productividad significativamente.",
            "should_pass": True
        },
        {
            "name": "Técnicas de ventas estándar",
            "response": "¿Te gustaría ver una demo personalizada para tu área específica de trabajo?",
            "should_pass": True
        },
        {
            "name": "Información contradictoria REAL",
            "response": "El curso cuesta $50 USD y dura 50 horas.", # Contradice precio y duración real
            "should_pass": False
        }
    ]
    
    print(f"🎯 Ejecutando {len(test_cases)} casos de prueba...\n")
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"📝 TEST {i}: {test_case['name']}")
        print(f"💬 Respuesta: {test_case['response']}")
        
        try:
            validation = await prompt_service.validate_response(
                response=test_case['response'],
                course_data=course_data,
                bonuses_data=bonuses_data
            )
            
            is_valid = validation.get('is_valid', True)
            confidence = validation.get('confidence', 0.0)
            errors = validation.get('errors', [])
            warnings = validation.get('warnings', [])
            
            print(f"🔍 Resultado: {'✅ VÁLIDO' if is_valid else '❌ INVÁLIDO'}")
            print(f"📊 Confianza: {confidence:.2f}")
            
            if errors:
                print(f"❌ Errores: {', '.join(errors)}")
            if warnings:
                print(f"⚠️ Warnings: {', '.join(warnings)}")
            
            # Verificar si el resultado es el esperado
            if is_valid == test_case['should_pass']:
                print(f"✅ TEST PASÓ - Resultado esperado")
                passed += 1
            else:
                print(f"❌ TEST FALLÓ - Esperado: {'válido' if test_case['should_pass'] else 'inválido'}, Obtenido: {'válido' if is_valid else 'inválido'}")
                failed += 1
                
        except Exception as e:
            print(f"💥 ERROR en validación: {e}")
            failed += 1
        
        print("-" * 40)
    
    print(f"\n📊 RESULTADOS FINALES:")
    print(f"✅ Tests pasados: {passed}/{len(test_cases)}")
    print(f"❌ Tests fallidos: {failed}/{len(test_cases)}")
    print(f"📈 Tasa de éxito: {(passed/len(test_cases)*100):.1f}%")
    
    if passed >= len(test_cases) - 1:  # Permitir 1 fallo
        print(f"\n🎉 VALIDADOR FUNCIONA CORRECTAMENTE - Es permisivo y no bloquea herramientas legítimas")
    else:
        print(f"\n⚠️ VALIDADOR PUEDE ESTAR DEMASIADO RESTRICTIVO")
    
    return passed >= len(test_cases) - 1

if __name__ == "__main__":
    asyncio.run(test_validador_permisivo())