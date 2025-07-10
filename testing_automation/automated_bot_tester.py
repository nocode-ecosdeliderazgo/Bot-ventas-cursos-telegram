#!/usr/bin/env python3
"""
Sistema de Testing Automatizado para Bot Brenda
Envía mensajes automáticamente a tu bot de Telegram y registra respuestas.

NOTA IMPORTANTE: Para botones, tendrás que presionarlos manualmente.
El script pausará y te avisará cuando necesites interactuar.
"""

import asyncio
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import sys

# Intentar importar bibliotecas de Telegram
try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    print("⚠️ python-telegram-bot no está instalado")
    print("Ejecuta: pip install python-telegram-bot")
    TELEGRAM_AVAILABLE = False

class BotTester:
    def __init__(self, bot_token: str, chat_id: str):
        """
        Inicializa el tester automatizado.
        
        Args:
            bot_token: Token de tu bot (para enviar mensajes)
            chat_id: ID del chat donde testear (tu user ID)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = None
        self.results = []
        self.current_flow = ""
        
        if TELEGRAM_AVAILABLE:
            self.bot = Bot(token=bot_token)
    
    def load_flow_messages(self, flow_number: int) -> List[Dict]:
        """Carga los mensajes del flujo especificado."""
        
        flow_1_messages = [
            {"step": 1, "message": "#Experto_IA_GPT_Gemini #ADSIM_01", "type": "text", "expect": "Flujo de privacidad"},
            {"step": 2, "message": "[MANUAL] Presionar botón: ✅ Acepto", "type": "button", "expect": "Solicitud de nombre"},
            {"step": 3, "message": "María González", "type": "text", "expect": "Bienvenida + PDF + imagen + info curso"},
            {"step": 4, "message": "¿Qué voy a aprender exactamente? Me gustaría ver el temario completo del curso", "type": "text", "expect": "mostrar_syllabus_interactivo"},
            {"step": 5, "message": "Se ve interesante pero trabajo tiempo completo, ¿cuánto tiempo necesito dedicarle diariamente?", "type": "text", "expect": "gestionar_objeciones_tiempo"},
            {"step": 6, "message": "¿Tienen algún material de muestra o recurso gratuito que pueda revisar antes?", "type": "text", "expect": "enviar_recursos_gratuitos"},
            {"step": 7, "message": "Me parece caro para mi presupuesto actual, $249 es mucho dinero", "type": "text", "expect": "mostrar_comparativa_precios"},
            {"step": 8, "message": "¿Qué pasa si no me gusta el curso? ¿Hay alguna garantía?", "type": "text", "expect": "mostrar_garantia_satisfaccion"},
            {"step": 9, "message": "¿Hay alguna promoción especial o bono adicional disponible?", "type": "text", "expect": "mostrar_bonos_exclusivos"},
            {"step": 10, "message": "Me convenciste, pero antes me gustaría hablar con alguien para resolver unas dudas específicas de mi caso", "type": "text", "expect": "agendar_demo_personalizada"}
        ]
        
        flow_2_messages = [
            {"step": 1, "message": "#Experto_IA_GPT_Gemini #ADSIM_01", "type": "text", "expect": "Flujo de privacidad"},
            {"step": 2, "message": "[MANUAL] Presionar botón: ✅ Acepto", "type": "button", "expect": "Solicitud de nombre"},
            {"step": 3, "message": "Carlos Pérez", "type": "text", "expect": "Bienvenida + PDF + imagen + info curso"},
            {"step": 4, "message": "He visto muchos cursos de IA que prometen mucho y no enseñan nada útil. ¿Cómo sé que este no es igual?", "type": "text", "expect": "mostrar_casos_exito_similares"},
            {"step": 5, "message": "Esos testimonios pueden ser inventados. ¿Tienen estudiantes reales que hayan aplicado esto en su trabajo?", "type": "text", "expect": "mostrar_social_proof_inteligente"},
            {"step": 6, "message": "Trabajo en finanzas y no tengo experiencia técnica. ¿No será muy avanzado para mí?", "type": "text", "expect": "personalizar_propuesta_por_perfil"},
            {"step": 7, "message": "Vi un curso similar en Coursera por $50, ¿por qué debería pagar 5 veces más?", "type": "text", "expect": "mostrar_comparativa_competidores"},
            {"step": 8, "message": "¿Cómo sé que voy a mantener la motivación? Siempre empiezo cursos y no los termino", "type": "text", "expect": "implementar_gamificacion"},
            {"step": 9, "message": "¿En cuánto tiempo voy a ver resultados reales en mi trabajo? Necesito algo concreto", "type": "text", "expect": "mostrar_timeline_resultados"},
            {"step": 10, "message": "Me interesa pero $249 está fuera de mi presupuesto este mes. ¿Hay opciones de pago?", "type": "text", "expect": "personalizar_oferta_por_budget"},
            {"step": 11, "message": "Déjame pensarlo hasta el fin de semana y te confirmo", "type": "text", "expect": "generar_urgencia_dinamica"}
        ]
        
        flow_3_messages = [
            {"step": 1, "message": "#Experto_IA_GPT_Gemini #ADSIM_01", "type": "text", "expect": "Flujo de privacidad"},
            {"step": 2, "message": "[MANUAL] Presionar botón: ✅ Acepto", "type": "button", "expect": "Solicitud de nombre"},
            {"step": 3, "message": "Ana Rodríguez", "type": "text", "expect": "Bienvenida + PDF + imagen + info curso"},
            {"step": 4, "message": "Tengo una agencia de marketing y paso 10 horas semanales creando reportes para clientes. ¿Puede ayudarme la IA?", "type": "text", "expect": "detectar_necesidades_automatizacion"},
            {"step": 5, "message": "Perfecto, ¿tienen ejemplos específicos de automatización de reportes como los míos?", "type": "text", "expect": "mostrar_casos_automatizacion"},
            {"step": 6, "message": "Si automatizo esos reportes, ¿cuánto podría ahorrar en tiempo y dinero mensualmente?", "type": "text", "expect": "calcular_roi_personalizado"},
            {"step": 7, "message": "Me gusta el ROI, pero ¿me van a ayudar a implementarlo en mi negocio específico?", "type": "text", "expect": "ofrecer_implementacion_asistida"},
            {"step": 8, "message": "¿Qué herramientas de IA específicas voy a aprender a usar para mi agencia?", "type": "text", "expect": "recomendar_herramientas_ia"},
            {"step": 9, "message": "¿Hay otros empresarios que hayan tomado el curso con quien pueda conectar?", "type": "text", "expect": "conectar_con_comunidad"},
            {"step": 10, "message": "Estoy convencida, ¿cómo puedo inscribirme hoy mismo?", "type": "text", "expect": "generar_link_pago_personalizado"},
            {"step": 11, "message": "Perfecto, después de pagar ¿cuándo empiezo y cómo es el proceso?", "type": "text", "expect": "establecer_seguimiento_automatico"}
        ]
        
        flows = {1: flow_1_messages, 2: flow_2_messages, 3: flow_3_messages}
        return flows.get(flow_number, [])
    
    async def send_message(self, message: str) -> bool:
        """Envía un mensaje al bot."""
        if not TELEGRAM_AVAILABLE or not self.bot:
            print(f"💬 [SIMULADO] Enviando: {message}")
            return True
            
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
            return True
        except TelegramError as e:
            print(f"❌ Error enviando mensaje: {e}")
            return False
    
    def wait_for_user_input(self, instruction: str, step: int):
        """Pausa el script y espera interacción manual del usuario."""
        print(f"\n🔄 PASO {step}: {instruction}")
        print("🖱️  ACCIÓN REQUERIDA: Presiona el botón en Telegram")
        print("⏸️  El script está pausado...")
        input("✅ Presiona ENTER cuando hayas presionado el botón en Telegram: ")
    
    def record_result(self, step: int, message: str, expected: str, actual_response: str = ""):
        """Registra el resultado de un paso."""
        result = {
            "step": step,
            "timestamp": datetime.now().isoformat(),
            "message_sent": message,
            "expected": expected,
            "actual_response": actual_response,
            "flow": self.current_flow
        }
        self.results.append(result)
    
    def save_results(self, flow_number: int):
        """Guarda los resultados en un archivo."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"testing_automation/results_flow_{flow_number}_{timestamp}.json"
        
        report_data = {
            "flow_number": flow_number,
            "flow_name": self.current_flow,
            "execution_date": datetime.now().isoformat(),
            "total_steps": len(self.results),
            "results": self.results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        # También crear un resumen en texto
        txt_filename = f"testing_automation/results_flow_{flow_number}_{timestamp}.txt"
        self.create_text_report(txt_filename, report_data)
        
        print(f"📊 Resultados guardados en:")
        print(f"   JSON: {filename}")
        print(f"   TXT:  {txt_filename}")
    
    def create_text_report(self, filename: str, data: Dict):
        """Crea un reporte en texto legible."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# REPORTE DE TESTING AUTOMATIZADO\n")
            f.write(f"# Bot Brenda - {data['flow_name']}\n")
            f.write(f"# Fecha: {data['execution_date']}\n")
            f.write(f"# Total de pasos: {data['total_steps']}\n")
            f.write("=" * 60 + "\n\n")
            
            for i, result in enumerate(data['results'], 1):
                f.write(f"## PASO {result['step']}\n")
                f.write(f"**Timestamp:** {result['timestamp']}\n")
                f.write(f"**Mensaje enviado:** {result['message_sent']}\n")
                f.write(f"**Respuesta esperada:** {result['expected']}\n")
                f.write(f"**Respuesta actual:** {result.get('actual_response', 'NO REGISTRADA')}\n")
                f.write(f"**Resultado:** [ ] ✅ Éxito / [ ] ❌ Fallo\n")
                f.write("-" * 40 + "\n\n")
            
            f.write("## RESUMEN DE VALIDACIONES\n")
            f.write("- [ ] Herramientas activadas correctamente\n")
            f.write("- [ ] Información real de BD mostrada\n")
            f.write("- [ ] Memoria persistente funcionando\n")
            f.write("- [ ] Personalización adecuada\n")
            f.write("- [ ] Manejo de objeciones efectivo\n")
            f.write("- [ ] Sin errores críticos\n\n")
            
            f.write("## NOTAS ADICIONALES\n")
            f.write("(Agregar observaciones manuales aquí)\n\n")
    
    async def run_flow(self, flow_number: int):
        """Ejecuta un flujo completo de testing."""
        flow_names = {
            1: "FLUJO 1: USUARIO EXPLORADOR INTERESADO",
            2: "FLUJO 2: USUARIO ESCÉPTICO CON OBJECIONES", 
            3: "FLUJO 3: USUARIO DECIDIDO QUE BUSCA AUTOMATIZACIÓN"
        }
        
        self.current_flow = flow_names.get(flow_number, f"FLUJO {flow_number}")
        messages = self.load_flow_messages(flow_number)
        
        if not messages:
            print(f"❌ Flujo {flow_number} no encontrado")
            return
        
        print(f"\n🚀 INICIANDO {self.current_flow}")
        print("=" * 60)
        print(f"📱 Chat ID: {self.chat_id}")
        print(f"🤖 Bot Token: {self.bot_token[:10]}...")
        print(f"📝 Total de pasos: {len(messages)}")
        print("=" * 60)
        
        # Limpiar resultados previos
        self.results = []
        
        for msg_data in messages:
            step = msg_data["step"]
            message = msg_data["message"]
            msg_type = msg_data["type"]
            expected = msg_data["expect"]
            
            print(f"\n📤 PASO {step}")
            print(f"Mensaje: {message}")
            print(f"Esperado: {expected}")
            
            if msg_type == "button":
                # Acción manual requerida
                self.wait_for_user_input(message, step)
                self.record_result(step, message, expected, "ACCIÓN MANUAL COMPLETADA")
            else:
                # Enviar mensaje automáticamente
                success = await self.send_message(message)
                if success:
                    print("✅ Mensaje enviado")
                    self.record_result(step, message, expected)
                else:
                    print("❌ Error enviando mensaje")
                    self.record_result(step, message, expected, "ERROR DE ENVÍO")
            
            # Esperar respuesta del bot
            wait_time = 15  # 15 segundos como pediste
            print(f"⏰ Esperando {wait_time} segundos para respuesta del bot...")
            
            for i in range(wait_time, 0, -1):
                print(f"\r⏳ {i} segundos restantes...", end="", flush=True)
                await asyncio.sleep(1)
            
            print(f"\n✅ Tiempo de espera completado")
            
            # Pausa para que el usuario pueda observar la respuesta
            if step < len(messages):
                input("📋 Presiona ENTER para continuar al siguiente paso (o Ctrl+C para salir): ")
        
        # Guardar resultados
        self.save_results(flow_number)
        
        print(f"\n🎉 {self.current_flow} COMPLETADO")
        print("📊 Revisa los archivos de resultados para el análisis detallado")

def main():
    print("🤖 SISTEMA DE TESTING AUTOMATIZADO - BOT BRENDA")
    print("=" * 60)
    
    if not TELEGRAM_AVAILABLE:
        print("❌ python-telegram-bot no está disponible")
        print("Ejecuta: pip install python-telegram-bot")
        return
    
    # Solicitar configuración
    print("\n📋 CONFIGURACIÓN INICIAL")
    print("-" * 30)
    
    bot_token = input("🔑 Token de tu bot (desde BotFather): ").strip()
    if not bot_token:
        print("❌ Token requerido")
        return
    
    chat_id = input("💬 Tu chat ID (número): ").strip()
    if not chat_id:
        print("❌ Chat ID requerido")
        return
    
    # Menú de selección de flujo
    print("\n🎯 SELECCIONA EL FLUJO A EJECUTAR")
    print("-" * 40)
    print("1. 👨‍💼 Flujo 1: Usuario Explorador Interesado (10 pasos)")
    print("2. 🤔 Flujo 2: Usuario Escéptico con Objeciones (11 pasos)")
    print("3. 🚀 Flujo 3: Usuario Decidido que busca Automatización (11 pasos)")
    print("0. ❌ Salir")
    
    try:
        choice = int(input("\n➡️ Ingresa tu opción (0-3): "))
        
        if choice == 0:
            print("👋 ¡Hasta luego!")
            return
        elif choice not in [1, 2, 3]:
            print("❌ Opción inválida")
            return
        
        # Crear tester y ejecutar
        tester = BotTester(bot_token, chat_id)
        
        print(f"\n⚠️ IMPORTANTE:")
        print("• El script enviará mensajes automáticamente cada 15 segundos")
        print("• Para botones, tendrás que presionarlos manualmente")
        print("• Los resultados se guardarán en archivos JSON y TXT")
        print("• Presiona Ctrl+C en cualquier momento para salir")
        
        input("\n🚦 Presiona ENTER para iniciar el testing...")
        
        # Ejecutar el flujo seleccionado
        asyncio.run(tester.run_flow(choice))
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Testing interrumpido por el usuario")
    except ValueError:
        print("❌ Por favor ingresa un número válido")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    main()