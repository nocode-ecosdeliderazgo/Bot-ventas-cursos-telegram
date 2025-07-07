#!/usr/bin/env python3
"""
Minimal test to check if we can import from our own modules
"""

import sys
import os

# Add the venv site-packages to the Python path
venv_path = os.path.join(os.getcwd(), 'venv', 'Lib', 'site-packages')
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

def test_core_modules():
    """Test core modules that should work"""
    print("Testing core modules...")
    print("-" * 40)
    
    # Test our own modules first
    try:
        from core.services.database import DatabaseService
        print("✅ Database Service")
    except Exception as e:
        print(f"❌ Database Service: {e}")
        return False
    
    try:
        from core.agents.smart_sales_agent import SmartSalesAgent  
        print("✅ Smart Sales Agent")
    except Exception as e:
        print(f"❌ Smart Sales Agent: {e}")
        return False
    
    try:
        from core.utils.memory import GlobalMemory
        print("✅ Global Memory")
    except Exception as e:
        print(f"❌ Global Memory: {e}")
        return False
    
    try:
        from core.utils.message_templates import MessageTemplates
        print("✅ Message Templates")
    except Exception as e:
        print(f"❌ Message Templates: {e}")
        return False
    
    print("-" * 40)
    print("✅ Core modules working!")
    return True

def test_external_packages():
    """Test external packages from venv"""
    print("\nTesting external packages...")
    print("-" * 40)
    
    try:
        import telegram
        print("✅ Telegram library")
    except Exception as e:
        print(f"❌ Telegram library: {e}")
        return False
    
    try:
        import asyncpg
        print("✅ AsyncPG")
    except Exception as e:
        print(f"❌ AsyncPG: {e}")
        return False
    
    try:
        import requests
        print("✅ Requests")
    except Exception as e:
        print(f"❌ Requests: {e}")
        return False
    
    try:
        from pydantic_settings import BaseSettings
        print("✅ Pydantic Settings")
    except Exception as e:
        print(f"❌ Pydantic Settings: {e}")
        return False
    
    print("-" * 40)
    print("✅ External packages working!")
    return True

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print(f"Python path includes venv: {venv_path in sys.path}")
    
    core_success = test_core_modules()
    external_success = test_external_packages()
    
    if core_success and external_success:
        print("\n🎉 All tests passed! Bot should be ready to run.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)