#!/usr/bin/env python3
"""
Testing Simplificado para Bot Brenda
No requiere APIs de Telegram - solo te guía paso a paso y registra resultados.
"""

import time
import json
import os
from datetime import datetime
from typing import List, Dict

class SimpleBotTester:
    def __init__(self):
        self.results = []
        self.current_flow = ""
    
    def load_flow_messages(self, flow_number: int) -> List[Dict]:
        """Carga los mensajes del flujo especificado."""
        
        flow_1_messages = [
            {"step": 1, "message": "#Experto_IA_GPT_Gemini #ADSIM_01", "type": "text", "expect": "Flujo de privacidad → botón aceptar"},
            {"step": 2, "action": "Presionar botón: ✅ Acepto", "type": "button", "expect": "Solicitud de nombre"},
            {"step": 3, "message": "María González", "type": "text", "expect": "Bienvenida + PDF + imagen + info curso"},
            {"step": 4, "message": "¿Qué voy a aprender exactamente? Me gustaría ver el temario completo del curso", "type": "text", "expect": "Herramienta: mostrar_syllabus_interactivo"},
            {"step": 5, "message": "Se ve interesante pero trabajo tiempo completo, ¿cuánto tiempo necesito dedicarle diariamente?", "type": "text", "expect": "Herramienta: gestionar_objeciones_tiempo"},
            {"step": 6, "message": "¿Tienen algún material de muestra o recurso gratuito que pueda revisar antes?", "type": "text", "expect": "Herramienta: enviar_recursos_gratuitos"},
            {"step": 7, "message": "Me parece caro para mi presupuesto actual, $249 es mucho dinero", "type": "text", "expect": "Herramienta: mostrar_comparativa_precios"},
            {"step": 8, "message": "¿Qué pasa si no me gusta el curso? ¿Hay alguna garantía?", "type": "text", "expect": "Herramienta: mostrar_garantia_satisfaccion"},
            {"step": 9, "message": "¿Hay alguna promoción especial o bono adicional disponible?", "type": "text", "expect": "Herramienta: mostrar_bonos_exclusivos"},
            {"step": 10, "message": "Me convenciste, pero antes me gustaría hablar con alguien para resolver unas dudas específicas de mi caso", "type": "text", "expect": "Herramienta: agendar_demo_personalizada"},
            {"step": 11, "message": "Quiero hablar con un asesor", "type": "text", "expect": "Herramienta: contactar_asesor_directo → flujo de contacto"}
        ]
        
        flow_2_messages = [
            {"step": 1, "message": "#Experto_IA_GPT_Gemini #ADSIM_01", "type": "text", "expect": "Flujo de privacidad → botón aceptar"},
            {"step": 2, "action": "Presionar botón: ✅ Acepto", "type": "button", "expect": "Solicitud de nombre"},
            {"step": 3, "message": "Carlos Pérez", "type": "text", "expect": "Bienvenida + PDF + imagen + info curso"},
            {"step": 4, "message": "He visto muchos cursos de IA que prometen mucho y no enseñan nada útil. ¿Cómo sé que este no es igual?", "type": "text", "expect": "Herramienta: mostrar_casos_exito_similares"},
            {"step": 5, "message": "Esos testimonios pueden ser inventados. ¿Tienen estudiantes reales que hayan aplicado esto en su trabajo?", "type": "text", "expect": "Herramienta: mostrar_social_proof_inteligente"},
            {"step": 6, "message": "Trabajo en finanzas y no tengo experiencia técnica. ¿No será muy avanzado para mí?", "type": "text", "expect": "Herramienta: personalizar_propuesta_por_perfil"},
            {"step": 7, "message": "Vi un curso similar en Coursera por $50, ¿por qué debería pagar 5 veces más?", "type": "text", "expect": "Herramienta: mostrar_comparativa_competidores"},
            {"step": 8, "message": "¿Cómo sé que voy a mantener la motivación? Siempre empiezo cursos y no los termino", "type": "text", "expect": "Herramienta: implementar_gamificacion"},
            {"step": 9, "message": "¿En cuánto tiempo voy a ver resultados reales en mi trabajo? Necesito algo concreto", "type": "text", "expect": "Herramienta: mostrar_timeline_resultados"},
            {"step": 10, "message": "Me interesa pero $249 está fuera de mi presupuesto este mes. ¿Hay opciones de pago?", "type": "text", "expect": "Herramienta: personalizar_oferta_por_budget"},
            {"step": 11, "message": "Déjame pensarlo hasta el fin de semana y te confirmo", "type": "text", "expect": "Herramienta: generar_urgencia_dinamica"}
        ]
        
        flow_3_messages = [
            {"step": 1, "message": "#Experto_IA_GPT_Gemini #ADSIM_01", "type": "text", "expect": "Flujo de privacidad → botón aceptar"},
            {"step": 2, "action": "Presionar botón: ✅ Acepto", "type": "button", "expect": "Solicitud de nombre"},
            {"step": 3, "message": "Ana Rodríguez", "type": "text", "expect": "Bienvenida + PDF + imagen + info curso"},
            {"step": 4, "message": "Tengo una agencia de marketing y paso 10 horas semanales creando reportes para clientes. ¿Puede ayudarme la IA?", "type": "text", "expect": "Herramienta: detectar_necesidades_automatizacion"},
            {"step": 5, "message": "Perfecto, ¿tienen ejemplos específicos de automatización de reportes como los míos?", "type": "text", "expect": "Herramienta: mostrar_casos_automatizacion"},
            {"step": 6, "message": "Si automatizo esos reportes, ¿cuánto podría ahorrar en tiempo y dinero mensualmente?", "type": "text", "expect": "Herramienta: calcular_roi_personalizado"},
            {"step": 7, "message": "Me gusta el ROI, pero ¿me van a ayudar a implementarlo en mi negocio específico?", "type": "text", "expect": "Herramienta: ofrecer_implementacion_asistida"},
            {"step": 8, "message": "¿Qué herramientas de IA específicas voy a aprender a usar para mi agencia?", "type": "text", "expect": "Herramienta: recomendar_herramientas_ia"},
            {"step": 9, "message": "¿Hay otros empresarios que hayan tomado el curso con quien pueda conectar?", "type": "text", "expect": "Herramienta: conectar_con_comunidad"},
            {"step": 10, "message": "Estoy convencida, ¿cómo puedo inscribirme hoy mismo?", "type": "text", "expect": "Herramienta: generar_link_pago_personalizado"},
            {"step": 11, "message": "Perfecto, después de pagar ¿cuándo empiezo y cómo es el proceso?", "type": "text", "expect": "Herramienta: establecer_seguimiento_automatico"}
        ]
        
        flows = {1: flow_1_messages, 2: flow_2_messages, 3: flow_3_messages}
        return flows.get(flow_number, [])
    
    def display_step(self, step_data: Dict):
        """Muestra un paso del testing."""
        step = step_data["step"]
        msg_type = step_data["type"]
        expected = step_data["expect"]
        
        print(f"\n{'='*60}")
        print(f"📍 PASO {step}")
        print('='*60)
        
        if msg_type == "button":
            action = step_data["action"]
            print(f"🖱️  ACCIÓN: {action}")
        else:
            message = step_data["message"]
            print(f"💬 ENVIAR: {message}")
        
        print(f"🎯 ESPERADO: {expected}")
        print('='*60)
        
        if msg_type == "text":
            print(f"\n📱 COPIA Y PEGA en Telegram:")
            print(f"📋 {step_data['message']}")
        
        return step_data.get("message", step_data.get("action", ""))
    
    def wait_and_record(self, step: int, sent_message: str, expected: str):
        """Espera 15 segundos y permite al usuario registrar el resultado."""
        
        print(f"\n⏰ Esperando 15 segundos para que el bot responda...")
        
        # Cuenta regresiva
        for i in range(15, 0, -1):
            print(f"\r⏳ {i:2d} segundos restantes...", end="", flush=True)
            time.sleep(1)
        
        print(f"\n\n📊 REGISTRAR RESULTADO DEL PASO {step}")
        print("-" * 40)
        
        # Preguntar por el resultado
        print("¿Qué pasó después de enviar el mensaje?")
        print("1. ✅ Funcionó como esperado")
        print("2. ⚠️ Funcionó parcialmente") 
        print("3. ❌ No funcionó / Error")
        print("4. 🔄 Necesita más tiempo")
        
        while True:
            try:
                choice = input("\n➡️ Resultado (1-4): ").strip()
                if choice in ['1', '2', '3', '4']:
                    break
                print("❌ Por favor ingresa 1, 2, 3 o 4")
            except KeyboardInterrupt:
                return False
        
        result_map = {
            '1': {'status': 'success', 'icon': '✅', 'desc': 'Funcionó como esperado'},
            '2': {'status': 'partial', 'icon': '⚠️', 'desc': 'Funcionó parcialmente'},
            '3': {'status': 'failed', 'icon': '❌', 'desc': 'No funcionó / Error'}, 
            '4': {'status': 'timeout', 'icon': '🔄', 'desc': 'Necesita más tiempo'}
        }
        
        result = result_map[choice]
        
        # Solicitar observaciones adicionales
        observations = input("📝 Observaciones adicionales (opcional): ").strip()
        
        # Registrar resultado
        record = {
            "step": step,
            "timestamp": datetime.now().isoformat(),
            "message_sent": sent_message,
            "expected": expected,
            "result_status": result['status'],
            "result_description": result['desc'],
            "observations": observations,
            "flow": self.current_flow
        }
        
        self.results.append(record)
        
        print(f"{result['icon']} Resultado registrado: {result['desc']}")
        
        return True
    
    def save_results(self, flow_number: int):
        """Guarda los resultados en archivos."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Crear directorio de resultados si no existe
        os.makedirs("testing_automation/results", exist_ok=True)
        
        # Archivo JSON
        json_filename = f"testing_automation/results/flow_{flow_number}_{timestamp}.json"
        
        report_data = {
            "flow_number": flow_number,
            "flow_name": self.current_flow,
            "execution_date": datetime.now().isoformat(),
            "total_steps": len(self.results),
            "successful_steps": len([r for r in self.results if r['result_status'] == 'success']),
            "failed_steps": len([r for r in self.results if r['result_status'] == 'failed']),
            "results": self.results
        }
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        # Archivo de texto legible
        txt_filename = f"testing_automation/results/flow_{flow_number}_{timestamp}.txt"
        self.create_text_report(txt_filename, report_data)
        
        return json_filename, txt_filename
    
    def create_text_report(self, filename: str, data: Dict):
        """Crea un reporte en texto legible."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# REPORTE DE TESTING BOT BRENDA\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Flujo: {data['flow_name']}\n")
            f.write(f"Fecha: {data['execution_date']}\n")
            f.write(f"Total de pasos: {data['total_steps']}\n")
            f.write(f"Exitosos: {data['successful_steps']}\n")
            f.write(f"Fallidos: {data['failed_steps']}\n")
            f.write(f"Tasa de éxito: {(data['successful_steps']/data['total_steps']*100):.1f}%\n\n")
            
            f.write("## DETALLE POR PASO\n")
            f.write("-" * 30 + "\n\n")
            
            for result in data['results']:
                status_icons = {
                    'success': '✅',
                    'partial': '⚠️', 
                    'failed': '❌',
                    'timeout': '🔄'
                }
                
                icon = status_icons.get(result['result_status'], '❓')
                
                f.write(f"### PASO {result['step']} {icon}\n")
                f.write(f"**Mensaje:** {result['message_sent']}\n")
                f.write(f"**Esperado:** {result['expected']}\n")
                f.write(f"**Resultado:** {result['result_description']}\n")
                if result['observations']:
                    f.write(f"**Observaciones:** {result['observations']}\n")
                f.write(f"**Timestamp:** {result['timestamp']}\n")
                f.write("\n")
            
            f.write("## RESUMEN DE HERRAMIENTAS\n")
            f.write("-" * 30 + "\n\n")
            
            tools_mentioned = []
            for result in data['results']:
                if 'Herramienta:' in result['expected']:
                    tool = result['expected'].split('Herramienta: ')[-1].split(' →')[0]
                    status = '✅' if result['result_status'] == 'success' else '❌'
                    tools_mentioned.append(f"{status} {tool}")
            
            for tool in tools_mentioned:
                f.write(f"- {tool}\n")
            
            f.write(f"\n## CONCLUSIONES\n")
            f.write("-" * 30 + "\n\n")
            f.write("[ ] Bot responde adecuadamente\n")
            f.write("[ ] Herramientas se activan correctamente\n")
            f.write("[ ] Información es precisa y de BD\n")
            f.write("[ ] Memoria funciona entre mensajes\n")
            f.write("[ ] Flujo de contacto operativo\n")
            f.write("[ ] Sin errores críticos\n\n")
    
    def run_flow(self, flow_number: int):
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
        
        # Limpiar resultados previos
        self.results = []
        
        print(f"\n🚀 INICIANDO {self.current_flow}")
        print(f"📝 Total de pasos: {len(messages)}")
        print(f"⏱️ Tiempo estimado: {len(messages) * 1} minutos")
        print("\n🔸 INSTRUCCIONES:")
        print("  • Ten Telegram abierto con tu bot")
        print("  • Copia y pega cada mensaje cuando se indique")
        print("  • Presiona botones cuando sea necesario")
        print("  • Observa la respuesta del bot")
        print("  • Registra el resultado cuando se te pida")
        
        input("\n✅ Presiona ENTER para comenzar...")
        
        try:
            for i, msg_data in enumerate(messages):
                # Mostrar paso actual
                sent_message = self.display_step(msg_data)
                
                # Esperar confirmación del usuario
                if msg_data["type"] == "button":
                    input("\n🖱️ Presiona ENTER después de hacer clic en el botón: ")
                else:
                    input("\n📤 Presiona ENTER después de enviar el mensaje: ")
                
                # Registrar resultado
                success = self.wait_and_record(
                    msg_data["step"], 
                    sent_message, 
                    msg_data["expect"]
                )
                
                if not success:
                    print("\n⏹️ Testing interrumpido")
                    break
                
                # Preguntar si continuar (excepto en el último paso)
                if i < len(messages) - 1:
                    continue_choice = input("\n🔄 ¿Continuar al siguiente paso? (Enter=Sí, n=No): ").strip().lower()
                    if continue_choice == 'n':
                        print("⏹️ Testing pausado por el usuario")
                        break
            
            # Guardar resultados
            json_file, txt_file = self.save_results(flow_number)
            
            print(f"\n🎉 {self.current_flow} COMPLETADO")
            print(f"📊 Resultados guardados en:")
            print(f"   📄 {txt_file}")
            print(f"   📊 {json_file}")
            
            # Mostrar resumen rápido
            successful = len([r for r in self.results if r['result_status'] == 'success'])
            total = len(self.results)
            success_rate = (successful / total * 100) if total > 0 else 0
            
            print(f"\n📈 RESUMEN RÁPIDO:")
            print(f"   ✅ Exitosos: {successful}/{total}")
            print(f"   📊 Tasa de éxito: {success_rate:.1f}%")
            
        except KeyboardInterrupt:
            print(f"\n\n⏹️ Testing interrumpido")
            if self.results:
                json_file, txt_file = self.save_results(flow_number)
                print(f"📊 Resultados parciales guardados en: {txt_file}")

def main():
    print("🤖 TESTING MANUAL GUIADO - BOT BRENDA")
    print("=" * 50)
    print("📋 Este script te guía paso a paso para probar tu bot")
    print("🕒 Cada paso incluye espera de 15 segundos")
    print("📊 Los resultados se guardan automáticamente")
    
    # Menú de selección
    print("\n🎯 SELECCIONA EL FLUJO A PROBAR:")
    print("-" * 40)
    print("1. 👨‍💼 Explorador Interesado (11 pasos - ~15 min)")
    print("2. 🤔 Escéptico con Objeciones (11 pasos - ~15 min)")
    print("3. 🚀 Decidido / Automatización (11 pasos - ~15 min)")
    print("0. ❌ Salir")
    
    try:
        choice = input("\n➡️ Tu opción (0-3): ").strip()
        
        if choice == '0':
            print("👋 ¡Hasta luego!")
            return
        elif choice not in ['1', '2', '3']:
            print("❌ Opción inválida")
            return
        
        flow_number = int(choice)
        
        # Crear tester y ejecutar
        tester = SimpleBotTester()
        tester.run_flow(flow_number)
        
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    except ValueError:
        print("❌ Por favor ingresa un número válido")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    main()