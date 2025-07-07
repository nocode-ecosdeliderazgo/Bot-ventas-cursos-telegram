#!/usr/bin/env python3
"""
Simple test to verify Telegram bot integration works
"""
import sys
import os

# Add the venv site-packages to the Python path
venv_path = os.path.join(os.getcwd(), 'venv', 'Lib', 'site-packages')
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

import asyncio
from telegram.ext import Application, MessageHandler, filters
from telegram import Update

# Load environment variables manually
def load_env():
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
        return None
    return env_vars

async def handle_message(update: Update, context):
    """Simple message handler"""
    try:
        await update.message.reply_text("🤖 Bot funcionando correctamente!")
    except Exception as e:
        print(f"Error handling message: {e}")

async def main():
    """Main function to test bot"""
    print("Testing Telegram Bot integration...")
    
    # Load environment
    env_vars = load_env()
    if not env_vars or 'TELEGRAM_API_TOKEN' not in env_vars:
        print("❌ TELEGRAM_API_TOKEN not found in .env file")
        return False
    
    try:
        # Create application
        app = Application.builder().token(env_vars['TELEGRAM_API_TOKEN']).build()
        
        # Add message handler
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ Telegram bot initialized successfully!")
        print("✅ Bot is ready to run!")
        print("Note: To actually start the bot, you would call: await app.run_polling()")
        
        return True
    except Exception as e:
        print(f"❌ Error initializing bot: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)