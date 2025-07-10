#!/usr/bin/env python3
"""
Script para obtener tu Chat ID de Telegram fácilmente.
Usa este script para obtener tu user ID que necesitas para el testing automatizado.
"""

import sys
import os

try:
    from telegram import Bot
    from telegram.error import TelegramError
    import asyncio
    TELEGRAM_AVAILABLE = True
except ImportError:
    print("⚠️ python-telegram-bot no está instalado")
    print("Ejecuta: pip install python-telegram-bot")
    TELEGRAM_AVAILABLE = False

async def get_chat_id(bot_token: str):
    """Obtiene el chat ID usando el token del bot."""
    if not TELEGRAM_AVAILABLE:
        return None
    
    try:
        bot = Bot(token=bot_token)
        
        print("🔍 Obteniendo actualizaciones del bot...")
        print("💬 Envía cualquier mensaje a tu bot en Telegram AHORA")
        print("⏰ Esperando 30 segundos...")
        
        # Esperar un poco para que el usuario envíe un mensaje
        for i in range(30, 0, -1):
            print(f"\r⏳ {i} segundos restantes...", end="", flush=True)
            await asyncio.sleep(1)
        
        print("\n\n📡 Consultando mensajes...")
        
        # Obtener actualizaciones
        updates = await bot.get_updates()
        
        if not updates:
            print("❌ No se encontraron mensajes")
            print("💡 Asegúrate de:")
            print("   1. Enviar un mensaje a tu bot")
            print("   2. Que el bot esté activo")
            print("   3. Que el token sea correcto")
            return None
        
        # Mostrar todos los chat IDs encontrados
        chat_ids = set()
        print(f"\n📨 Se encontraron {len(updates)} actualizaciones:")
        print("-" * 50)
        
        for update in updates[-10:]:  # Mostrar solo las últimas 10
            if update.message:
                chat_id = update.message.chat.id
                user = update.message.from_user
                text = update.message.text[:50] if update.message.text else "[Multimedia]"
                
                chat_ids.add(chat_id)
                
                print(f"💬 Chat ID: {chat_id}")
                print(f"   👤 Usuario: {user.first_name} (@{user.username})")
                print(f"   📝 Mensaje: {text}")
                print(f"   🕒 Fecha: {update.message.date}")
                print("-" * 30)
        
        if chat_ids:
            print(f"\n✅ Chat IDs encontrados: {list(chat_ids)}")
            return list(chat_ids)[0]  # Retornar el primer chat ID
        else:
            print("❌ No se encontraron chat IDs válidos")
            return None
            
    except TelegramError as e:
        print(f"❌ Error de Telegram: {e}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return None

def manual_instructions():
    """Muestra instrucciones para obtener el chat ID manualmente."""
    print("\n📋 MÉTODO MANUAL PARA OBTENER TU CHAT ID:")
    print("=" * 60)
    print("1. 📱 Abre Telegram")
    print("2. 🔍 Busca el bot @userinfobot")
    print("3. 💬 Envía /start al bot")
    print("4. 📊 El bot te responderá con tu información, incluyendo tu ID")
    print("5. 📋 Copia el número que aparece como 'Id: XXXXXXXX'")
    print("\n🔗 Alternativamente:")
    print("1. 🌐 Ve a https://web.telegram.org")
    print("2. 📱 Abre cualquier chat")
    print("3. 👀 Mira la URL: el número después de #/im?p=u es tu chat ID")
    print("\n💡 Tu chat ID es un número como: 123456789")

async def main():
    print("🔍 OBTENER CHAT ID DE TELEGRAM")
    print("=" * 40)
    print("Este script te ayuda a obtener tu Chat ID para usar en el testing")
    
    if not TELEGRAM_AVAILABLE:
        manual_instructions()
        return
    
    print("\n🔑 CONFIGURACIÓN:")
    bot_token = input("Token de tu bot (desde @BotFather): ").strip()
    
    if not bot_token:
        print("❌ Token requerido")
        manual_instructions()
        return
    
    print(f"\n🤖 Token configurado: {bot_token[:10]}...")
    
    # Intentar obtener el chat ID automáticamente
    chat_id = await get_chat_id(bot_token)
    
    if chat_id:
        print(f"\n🎉 ¡ÉXITO! Tu Chat ID es: {chat_id}")
        print(f"📋 Úsalo en el testing automatizado")
        
        # Guardar en archivo para uso futuro
        config_file = "testing_automation/config.txt"
        with open(config_file, "w") as f:
            f.write(f"CHAT_ID={chat_id}\n")
            f.write(f"BOT_TOKEN={bot_token}\n")
        
        print(f"💾 Configuración guardada en: {config_file}")
    else:
        print(f"\n⚠️ No se pudo obtener automáticamente")
        manual_instructions()

if __name__ == "__main__":
    if TELEGRAM_AVAILABLE:
        asyncio.run(main())
    else:
        manual_instructions()