#!/usr/bin/env python3
"""
Simple environment test without external dependencies
"""
import os

def test_env_vars():
    # Read .env file manually
    env_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except FileNotFoundError:
        print("❌ .env file not found")
        return

    # Required variables
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_KEY', 
        'OPENAI_API_KEY',
        'TELEGRAM_API_TOKEN',
        'SMTP_SERVER',
        'SMTP_PORT',
        'SMTP_USERNAME',
        'SMTP_PASSWORD',
        'ADVISOR_EMAIL'
    ]
    
    print("Verificando variables de entorno...")
    print("-" * 50)
    
    for var_name in required_vars:
        if var_name in env_vars and env_vars[var_name]:
            # Show only first few characters for security
            safe_value = env_vars[var_name][:10] + "..." if len(env_vars[var_name]) > 10 else env_vars[var_name]
            print(f"✅ {var_name}: Encontrada ({safe_value})")
        else:
            print(f"❌ {var_name}: No encontrada o vacía")
    
    print("-" * 50)

if __name__ == "__main__":
    test_env_vars()