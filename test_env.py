"""
Script para probar la carga de variables de entorno.
"""
import os
from dotenv import load_dotenv
from config.settings import settings

def test_env_vars():
    # Cargar variables de entorno
    load_dotenv()
    
    # Lista de variables requeridas según settings.py
    required_vars = {
        'SUPABASE_URL': settings.supabase_url,
        'SUPABASE_KEY': settings.supabase_key,
        'OPENAI_API_KEY': settings.openai_api_key,
        'TELEGRAM_API_TOKEN': settings.telegram_api_token,
        'SMTP_SERVER': settings.smtp_server,
        'SMTP_PORT': str(settings.smtp_port),
        'SMTP_USERNAME': settings.smtp_username,
        'SMTP_PASSWORD': settings.smtp_password,
        'ADVISOR_EMAIL': settings.advisor_email
    }
    
    # Verificar cada variable
    results = []
    for var_name, var_value in required_vars.items():
        if var_value:
            # Mostrar solo los primeros caracteres para seguridad
            safe_value = str(var_value)[:10] + "..." if len(str(var_value)) > 10 else str(var_value)
            results.append(f"✅ {var_name}: Encontrada ({safe_value})")
        else:
            results.append(f"❌ {var_name}: No encontrada o vacía")
    
    return results

if __name__ == "__main__":
    print("\nVerificando variables de entorno...")
    print("-" * 50)
    try:
        for result in test_env_vars():
            print(result)
    except Exception as e:
        print(f"❌ Error al cargar las variables: {str(e)}")
    print("-" * 50) 