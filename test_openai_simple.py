#!/usr/bin/env python3
"""Test simple de la API de OpenAI"""

import os
from openai import OpenAI

def test_openai():
    try:
        # Cargar variables de entorno
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ No se encontró OPENAI_API_KEY en .env")
            return False
            
        print(f"🔑 API Key encontrada: {api_key[:10]}...")
        
        # Crear cliente
        client = OpenAI(api_key=api_key)
        
        # Hacer llamada simple
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Hola, responde solo 'API funcionando'"}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"✅ Respuesta de OpenAI: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Error con OpenAI: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Probando API de OpenAI...")
    success = test_openai()
    print(f"📊 Resultado: {'✅ FUNCIONA' if success else '❌ FALLA'}")