#!/usr/bin/env python3
"""
Clean import test script for the Telegram bot
"""

import sys
import os

def test_imports():
    """Test all critical imports for the bot"""
    print("Testing imports...")
    print("-" * 50)
    
    # Test 1: Basic Python imports
    try:
        import logging
        from datetime import datetime, timezone
        print("✅ Basic Python imports")
    except Exception as e:
        print(f"❌ Error in basic imports: {e}")
        return False
    
    # Test 2: Telegram Bot API  
    try:
        from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
        from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
        print("✅ Telegram Bot API")
    except Exception as e:
        print(f"❌ Error in Telegram Bot API: {e}")
        return False
    
    # Test 3: Database
    try:
        import asyncpg
        print("✅ AsyncPG (PostgreSQL)")
    except Exception as e:
        print(f"❌ Error in AsyncPG: {e}")
        return False
    
    # Test 4: HTTP requests
    try:
        import requests
        import httpx
        print("✅ HTTP libraries")
    except Exception as e:
        print(f"❌ Error in HTTP libraries: {e}")
        return False
    
    # Test 5: Settings
    try:
        from pydantic_settings import BaseSettings
        print("✅ Pydantic Settings")
    except Exception as e:
        print(f"❌ Error in Pydantic Settings: {e}")
        return False
    
    # Test 6: Core services
    try:
        from core.services.database import DatabaseService
        print("✅ Database Service")
    except Exception as e:
        print(f"❌ Error in Database Service: {e}")
        return False
    
    # Test 7: Smart sales agent
    try:
        from core.agents.smart_sales_agent import SmartSalesAgent
        print("✅ Smart Sales Agent")
    except Exception as e:
        print(f"❌ Error in Smart Sales Agent: {e}")
        return False
    
    # Test 8: Agent tools
    try:
        from core.agents.agent_tools import AgentTools
        print("✅ Agent Tools")
    except Exception as e:
        print(f"❌ Error in Agent Tools: {e}")
        return False
    
    # Test 9: Handlers
    try:
        from core.handlers.menu_handlers import handle_callback_query
        print("✅ Menu Handlers")
    except Exception as e:
        print(f"❌ Error in Menu Handlers: {e}")
        return False
    
    # Test 10: Utilities
    try:
        from core.utils.memory import GlobalMemory
        from core.utils.message_templates import MessageTemplates
        print("✅ Core Utilities")
    except Exception as e:
        print(f"❌ Error in Core Utilities: {e}")
        return False
    
    print("-" * 50)
    print("✅ All imports successful!")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)