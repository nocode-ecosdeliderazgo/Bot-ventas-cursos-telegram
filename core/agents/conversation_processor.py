"""
Procesador de conversaciones inteligente para el agente de ventas.
Maneja todas las interacciones del usuario después de mostrar la información del curso.
"""

import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import aiohttp

from config.settings import settings
from core.services.supabase_service import get_course_detail, get_courses, get_promotions
from core.utils.memory import LeadMemory
# NUEVO: importar CourseService
from core.services.courseService import CourseService

logger = logging.getLogger(__name__)

class ConversationProcessor:
    """
    Procesador inteligente de conversaciones que analiza intenciones del usuario
    y responde con información real de la base de datos manteniendo el objetivo de venta.
    """
    
    def __init__(self, course_service: Optional[CourseService] = None):
        self.openai_headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Intenciones principales que puede detectar
        self.intentions = {
            "price_question": "Pregunta sobre precio, costo, inversión, pago",
            "schedule_question": "Pregunta sobre horarios, fechas, cuándo empieza",
            "content_question": "Pregunta sobre temario, contenido, qué aprenderá",
            "instructor_question": "Pregunta sobre instructor, profesor, quién enseña",
            "certificate_question": "Pregunta sobre certificado, validez, reconocimiento",
            "modality_question": "Pregunta sobre modalidad, online, presencial",
            "level_question": "Pregunta sobre nivel, dificultad, requisitos",
            "duration_question": "Pregunta sobre duración, tiempo, horas",
            "comparison_question": "Comparación con otros cursos o competencia",
            "objection": "Objeción, duda, preocupación, 'es caro', 'no tengo tiempo'",
            "ready_to_buy": "Listo para comprar, inscribirse, registrarse",
            "more_info": "Pide más información general",
            "testimonials": "Pide testimonios, reseñas, opiniones",
            "support_question": "Pregunta sobre soporte, ayuda durante el curso",
            "technical_question": "Pregunta técnica sobre herramientas, software",
            "career_question": "Pregunta sobre beneficios profesionales, carrera",
            "group_question": "Pregunta sobre grupo, compañeros, tamaño de clase",
            "payment_methods": "Pregunta sobre formas de pago, financiamiento",
            "refund_policy": "Pregunta sobre política de reembolso, garantías",
            "other": "Otra intención no clasificada"
        }
        # NUEVO: guardar referencia a course_service
        self.course_service = course_service
    
    async def process_message(self, message: str, user_memory: LeadMemory) -> Tuple[str, Optional[Dict]]:
        """
        Procesa un mensaje del usuario y genera una respuesta inteligente.
        
        Args:
            message: Mensaje del usuario
            user_memory: Memoria del usuario con contexto
            
        Returns:
            Tupla con (respuesta, datos_adicionales)
        """
        try:
            # 1. Analizar intención del usuario
            intention_analysis = await self._analyze_intention(message, user_memory)
            
            # 2. Obtener información del curso si es necesario
            course_info = None
            if user_memory.selected_course:
                # Por ahora, no usamos get_course_detail aquí ya que no tenemos acceso a db_service
                # course_info = await get_course_detail(user_memory.selected_course)
                pass
            
            # 3. Extraer información profesional del usuario si es posible
            user_profession = self._extract_profession_info(message, user_memory)
            if user_profession:
                user_memory.role = user_profession
            
            # 4. Generar respuesta basada en la intención
            response = await self._generate_response(
                intention_analysis, 
                message, 
                user_memory, 
                course_info
            )
            
            # 5. Actualizar memoria del usuario
            self._update_user_memory(user_memory, message, intention_analysis)
            
            return response, None
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}", exc_info=True)
            return f"Disculpa {user_memory.name}, hubo un problema procesando tu mensaje. ¿Podrías repetir tu pregunta?", None
    
    async def _analyze_intention(self, message: str, user_memory: LeadMemory) -> Dict:
        """
        Analiza la intención del usuario usando OpenAI con contexto completo y herramientas avanzadas.
        """
        try:
            # Construir contexto completo del usuario
            user_context = await self._build_user_context(user_memory)
            
            # Prompt avanzado para OpenAI
            prompt = f"""
            Eres un agente de ventas de élite con IA avanzada. Tu misión es convertir leads en ventas actuando como un amigo genuinamente interesado, pero siempre orientado a vender.

            🎯 **TU OBJETIVO PRINCIPAL**: Vender el curso usando toda la información disponible y herramientas inteligentes.

            📊 **HERRAMIENTAS AVANZADAS DISPONIBLES**:
            1. **analizar_comportamiento_usuario** - Analiza patrones completos del usuario
            2. **generar_oferta_dinamica** - Crea ofertas personalizadas con descuentos inteligentes
            3. **mostrar_social_proof_inteligente** - Muestra testimonios de personas similares
            4. **activar_seguimiento_predictivo** - Programa mensajes en momentos óptimos
            5. **mostrar_comparativa_competidores** - Destaca ventajas vs competencia
            6. **implementar_gamificacion** - Crea progreso y recompensas
            7. **generar_urgencia_dinamica** - Urgencia basada en datos reales
            8. **personalizar_oferta_por_budget** - Adapta precios al presupuesto
            9. **mostrar_casos_exito_similares** - Casos de éxito relevantes
            10. **enviar_preview_curso** - Video preview personalizado
            11. **mostrar_syllabus_interactivo** - Contenido detallado
            12. **presentar_oferta_limitada** - Ofertas con tiempo límite
            13. **mostrar_bonos_exclusivos** - Bonos con urgencia
            14. **agendar_demo_personalizada** - Sesiones 1:1
            15. **enviar_recursos_gratuitos** - Contenido de valor
            16. **mostrar_comparativa_precios** - Análisis de ROI

            📋 **CONTEXTO ACTUAL DEL USUARIO**:
            {user_context}

            💬 **MENSAJE ACTUAL DEL USUARIO**:
            "{message}"

            🧠 **INSTRUCCIONES DE ANÁLISIS**:
            1. **Actualiza el resumen del usuario** con cualquier información nueva detectada
            2. **Analiza la intención principal** y secundarias del mensaje
            3. **Determina el nivel de interés** y señales de compra
            4. **Identifica objeciones** o preocupaciones
            5. **Recomienda herramientas específicas** para usar en la respuesta
            6. **Define la estrategia de respuesta** (educar, persuadir, cerrar, etc.)
            7. **Establece el timing** para follow-ups o acciones adicionales

            🎭 **PERSONALIDAD**:
            - Actúa como un amigo experto y entusiasta
            - Haz preguntas inteligentes para conocer mejor al usuario
            - Usa información previa para personalizar cada respuesta
            - Sé curioso sobre su profesión, retos y metas
            - Mantén el foco en vender sin ser hostigoso

            🚀 **ESTRATEGIAS DINÁMICAS**:
            - Si detectas alta intención de compra → usa herramientas de cierre
            - Si hay objeciones de precio → personalizar_oferta_por_budget
            - Si necesita más confianza → mostrar_social_proof_inteligente
            - Si está evaluando → mostrar_comparativa_competidores
            - Si es primera interacción → implementar_gamificacion
            - Si muestra urgencia → generar_urgencia_dinamica

            RESPONDE EN JSON CON ESTA ESTRUCTURA:
            {{
                "user_summary_update": {{
                    "new_info_detected": "información nueva del usuario",
                    "updated_profile": "resumen actualizado completo",
                    "key_insights": ["insight1", "insight2"]
                }},
                "intention_analysis": {{
                    "primary_intention": "intención principal",
                    "secondary_intentions": ["int1", "int2"],
                    "interest_level": "bajo/medio/alto/muy_alto",
                    "buying_signals": ["señal1", "señal2"],
                    "objections": ["objeción1", "objeción2"],
                    "urgency": "baja/media/alta/muy_alta",
                    "emotional_tone": "positivo/neutro/negativo",
                    "decision_stage": "awareness/consideration/decision"
                }},
                "recommended_tools": [
                    {{
                        "tool_name": "nombre_herramienta",
                        "priority": "alta/media/baja",
                        "reason": "por qué usar esta herramienta"
                    }}
                ],
                "response_strategy": {{
                    "approach": "educativo/persuasivo/cierre/nurturing",
                    "tone": "casual/formal/entusiasta",
                    "key_points": ["punto1", "punto2"],
                    "questions_to_ask": ["pregunta1", "pregunta2"],
                    "timing_for_followup": "inmediato/6h/24h/3d"
                }},
                "confidence": 0.95
            }}
            """
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "gpt-4.1-mini",
                    "messages": [
                        {"role": "system", "content": "Eres un agente de ventas de élite con IA avanzada. Responde solo en JSON válido."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.4,
                    "max_tokens": 1000
                }
                
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=self.openai_headers,
                    json=payload
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        content = result["choices"][0]["message"]["content"]
                        # Limpiar el contenido para asegurar JSON válido
                        content = content.strip()
                        if content.startswith("```json"):
                            content = content[7:-3]
                        elif content.startswith("```"):
                            content = content[3:-3]
                        
                        return json.loads(content)
                    else:
                        logger.error(f"Error en OpenAI: {result}")
                        return self._fallback_intention_analysis(message)
                        
        except Exception as e:
            logger.error(f"Error analizando intención: {e}", exc_info=True)
            return self._fallback_intention_analysis(message)

    async def _build_user_context(self, user_memory: LeadMemory) -> str:
        """
        Construye un contexto completo del usuario para el LLM.
        """
        context = f"""
        **INFORMACIÓN DEL USUARIO:**
        - Nombre: {user_memory.name}
        - Curso de interés: {user_memory.selected_course or 'No especificado'}
        - Puntuación de interés: {user_memory.lead_score}/100
        - Interacciones previas: {len(user_memory.message_history) if user_memory.message_history else 0}
        - Última interacción: {user_memory.last_interaction}
        
        **HISTORIAL RECIENTE:**
        """
        
        if user_memory.message_history:
            for msg in user_memory.message_history[-5:]:  # Últimos 5 mensajes
                timestamp = msg.get('timestamp', 'N/A')
                message_text = msg.get('message', 'N/A')
                intention = msg.get('intention', 'N/A')
                context += f"- [{timestamp}] Usuario: {message_text} (Intención: {intention})\n"
        else:
            context += "- Sin historial previo\n"
        
        context += f"""
        
        **PERFIL DETECTADO:**
        - Profesión: {getattr(user_memory, 'role', 'No detectada')}
        - Nivel de experiencia: {getattr(user_memory, 'experience_level', 'No especificado')}
        - Intereses: {getattr(user_memory, 'interests', 'No especificados')}
        - Objetivos de aprendizaje: {getattr(user_memory, 'learning_goals', 'No especificados')}
        
        **SEÑALES DE COMPRA:**
        - Nivel de engagement: {'Alto' if user_memory.lead_score > 70 else 'Medio' if user_memory.lead_score > 40 else 'Bajo'}
        - Tiempo desde primer contacto: {user_memory.created_at if hasattr(user_memory, 'created_at') else 'N/A'}
        """
        
        return context
    
    def _fallback_intention_analysis(self, message: str) -> Dict:
        """
        Análisis de intención de respaldo usando reglas simples.
        """
        message_lower = message.lower()
        
        # Detectar intenciones básicas con palabras clave
        if any(word in message_lower for word in ["precio", "costo", "cuesta", "pago", "dinero"]):
            primary = "price_question"
        elif any(word in message_lower for word in ["horario", "cuando", "fecha", "empieza"]):
            primary = "schedule_question"
        elif any(word in message_lower for word in ["temario", "contenido", "aprende", "incluye"]):
            primary = "content_question"
        elif any(word in message_lower for word in ["comprar", "inscribir", "registrar", "quiero"]):
            primary = "ready_to_buy"
        elif any(word in message_lower for word in ["caro", "costoso", "tiempo", "ocupado"]):
            primary = "objection"
        else:
            primary = "more_info"
        
        return {
            "primary_intention": primary,
            "secondary_intentions": [],
            "interest_level": "medium",
            "buying_signals": [],
            "objections": [],
            "urgency": "medium",
            "emotional_tone": "neutral",
            "specific_questions": [],
            "confidence": 0.7
        }
    
    async def _generate_response(
        self, 
        intention_analysis: Dict, 
        original_message: str, 
        user_memory: LeadMemory, 
        course_info: Optional[Dict]
    ) -> str:
        """
        Genera una respuesta basada en la intención analizada.
        """
        primary_intention = intention_analysis.get("primary_intention", "other")
        user_name = user_memory.name or "Usuario"
        
        # Mapear intenciones a métodos de respuesta
        response_methods = {
            "price_question": self._handle_price_question,
            "schedule_question": self._handle_schedule_question,
            "content_question": self._handle_content_question,
            "instructor_question": self._handle_instructor_question,
            "certificate_question": self._handle_certificate_question,
            "modality_question": self._handle_modality_question,
            "level_question": self._handle_level_question,
            "duration_question": self._handle_duration_question,
            "comparison_question": self._handle_comparison_question,
            "objection": self._handle_objection,
            "ready_to_buy": self._handle_ready_to_buy,
            "more_info": self._handle_more_info,
            "testimonials": self._handle_testimonials,
            "support_question": self._handle_support_question,
            "technical_question": self._handle_technical_question,
            "career_question": self._handle_career_question,
            "group_question": self._handle_group_question,
            "payment_methods": self._handle_payment_methods,
            "refund_policy": self._handle_refund_policy,
            "other": self._handle_other
        }
        
        # Obtener el método de respuesta
        response_method = response_methods.get(primary_intention, self._handle_other)
        
        # Generar respuesta
        response = await response_method(
            intention_analysis, 
            original_message, 
            user_name, 
            course_info
        )
        
        return response
    
    async def _handle_price_question(self, analysis: Dict, message: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja preguntas sobre precio - CONVERSACIONAL"""
        if not course_info:
            return f"Disculpa {user_name}, no tengo la información del curso disponible en este momento."
        
        price = course_info.get('price_usd', 'No disponible')
        original_price = course_info.get('original_price_usd')
        discount = course_info.get('discount_percentage')
        
        response = f"¡Excelente pregunta, {user_name}! 💰\n\n"
        
        # Mostrar precio con descuento si aplica
        if original_price and discount and original_price > price:
            response += f"🎉 **¡Tienes suerte!** Hay una promoción activa:\n"
            response += f"• Precio regular: ${original_price} USD\n"
            response += f"• **Tu precio HOY**: ${price} USD (${original_price - float(price)} de descuento)\n\n"
        else:
            response += f"La inversión para este curso es de **${price} USD**.\n\n"
        
        response += "✨ **¿Por qué es la mejor inversión que puedes hacer?**\n"
        response += "• Conocimiento que aplicarás desde el primer día\n"
        response += "• ROI promedio: recuperas la inversión en 2-4 semanas\n"
        response += "• Acceso de por vida al material y actualizaciones\n"
        response += "• Certificación que aumenta tu valor profesional\n\n"
        
        # Detectar si hay objeción de precio
        if any(word in message.lower() for word in ["caro", "costoso", "mucho", "barato", "dinero"]):
            response += "💡 **Pongámoslo en perspectiva:**\n"
            response += f"• Es menos de ${float(price)/30:.0f} USD por día durante un mes\n"
            response += "• Menos que 2 cenas en restaurante, pero los beneficios duran toda la vida\n"
            response += "• El aumento salarial promedio de nuestros alumnos es 40% en 6 meses\n\n"
        
        response += "🤔 **Cuéntame:** ¿Cuál es tu presupuesto ideal para invertir en tu crecimiento profesional? "
        response += "Tenemos opciones de pago flexibles que pueden ajustarse a ti. 😊"
        
        return response
    
    async def _handle_schedule_question(self, analysis: Dict, message: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja preguntas sobre horarios - CONVERSACIONAL"""
        if not course_info:
            return f"Disculpa {user_name}, no tengo la información del curso disponible en este momento."
        
        schedule = course_info.get('schedule', 'A consultar')
        duration = course_info.get('total_duration', '12:00:00')
        hours = duration.split(':')[0] if ':' in str(duration) else duration
        online = course_info.get('online', True)
        
        response = f"¡Perfecto {user_name}! 📅\n\n"
        response += f"**Horario:** {schedule}\n"
        response += f"**Duración total:** {hours} horas\n"
        response += f"**Modalidad:** {'100% Online en vivo' if online else 'Presencial'}\n\n"
        
        response += "✅ **Ventajas de este horario:**\n"
        response += "• Clases en vivo con interacción directa con el instructor\n"
        response += "• Horario diseñado especialmente para profesionales ocupados\n"
        response += "• Si no puedes asistir a alguna clase, tienes la grabación\n"
        response += "• Flexibilidad total para hacer preguntas en tiempo real\n"
        response += "• Networking con otros profesionales en tu mismo horario\n\n"
        
        response += "🤔 **Cuéntame:** ¿Este horario se ajusta bien a tu rutina actual? "
        response += "¿Trabajas en horario tradicional o tienes flexibilidad? "
        response += "Quiero asegurarme de que puedas aprovechar al máximo las clases. 😊"
        
        return response
    
    async def _handle_content_question(self, analysis: Dict, message: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja preguntas sobre contenido - CONVERSACIONAL"""
        response = f"¡Excelente pregunta, {user_name}! 📚\n\n"
        
        if course_info:
            tools_used = course_info.get('tools_used', [])
            if isinstance(tools_used, str):
                # Si tools_used es string, convertirlo a lista
                import json
                try:
                    tools_used = json.loads(tools_used.replace('{', '[').replace('}', ']').replace('"', '"'))
                except:
                    tools_used = []
            
            duration = course_info.get('total_duration', '12:00:00')
            hours = duration.split(':')[0] if ':' in str(duration) else duration
            
            response += f"Este curso de **{hours} horas** está diseñado para llevarte de cero a experto:\n\n"
            
            if tools_used:
                response += "🛠 **Herramientas que dominarás:**\n"
                for tool in tools_used[:4]:  # Mostrar máximo 4 herramientas
                    response += f"• {tool}\n"
                response += "\n"
        
        response += "🎯 **Módulos principales:**\n"
        response += "• Fundamentos de IA y ChatGPT (desde cero)\n"
        response += "• Prompts efectivos para resultados profesionales\n"
        response += "• Automatización de tareas diarias\n"
        response += "• Creación de contenido con IA\n"
        response += "• Casos de uso específicos por industria\n"
        response += "• Proyectos prácticos que van a tu portafolio\n\n"
        
        response += "💡 **Lo mejor:** Cada módulo incluye ejercicios que puedes aplicar INMEDIATAMENTE en tu trabajo.\n\n"
        response += "🤔 **Cuéntame:** ¿Hay algún tema específico que te emociona más? "
        response += "¿O alguna tarea en tu trabajo que te gustaría automatizar? "
        response += "Quiero asegurarme de que el curso cubra exactamente lo que necesitas. 😊"
        
        return response
    
    async def _handle_objection(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        """Maneja objeciones del usuario."""
        message_lower = message.lower()
        
        response = f"Te entiendo perfectamente, {user_name}. "
        
        if "caro" in message_lower or "costoso" in message_lower:
            response += "💭 Entiendo tu preocupación sobre la inversión.\n\n"
            response += "Déjame ponerte en perspectiva:\n"
            response += "• El promedio de aumento salarial tras dominar IA es del 40%\n"
            response += "• Solo necesitas aplicar 2-3 técnicas para recuperar la inversión\n"
            response += "• Es menos que una cena para dos, pero los beneficios duran toda la vida\n\n"
            response += "¿Qué tal si hablamos de opciones de pago flexibles? 💳"
            
        elif "tiempo" in message_lower or "ocupado" in message_lower:
            response += "⏰ Entiendo que el tiempo es valioso.\n\n"
            response += "Por eso diseñamos el curso pensando en profesionales ocupados:\n"
            response += "• Solo 2 horas por semana\n"
            response += "• Clases grabadas si no puedes asistir\n"
            response += "• Material para estudiar a tu ritmo\n"
            response += "• Ejercicios de 15 minutos que puedes hacer en el trabajo\n\n"
            response += "¿No crees que 2 horas semanales valen la pena para transformar tu carrera? 🚀"
            
        else:
            response += "🤔 Cuéntame más sobre tu preocupación. "
            response += "Estoy aquí para resolver todas tus dudas y asegurarme de que tomes la mejor decisión para ti."
        
        return response
    
    async def _handle_ready_to_buy(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        """Maneja cuando el usuario está listo para comprar."""
        response = f"¡Excelente decisión, {user_name}! 🎉\n\n"
        response += "Me emociona saber que estás listo para dar este paso hacia tu crecimiento profesional.\n\n"
        response += "📝 *Próximos pasos:*\n"
        response += "1. Te voy a conectar con nuestro asesor especializado\n"
        response += "2. Él te guiará en el proceso de inscripción\n"
        response += "3. Recibirás acceso inmediato al material preparatorio\n"
        response += "4. Te llegará el calendario con todas las fechas\n\n"
        response += "🚀 *¡Bienvenido a tu nueva etapa profesional!*\n\n"
        response += "Un asesor te contactará en los próximos 15 minutos para completar tu inscripción. "
        response += "¿Tienes alguna pregunta de último momento?"
        
        return response
    
    async def _handle_instructor_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Excelente pregunta, {user_name}! 👨‍🏫\n\n"
        response += "Nuestros instructores son expertos certificados con:\n"
        response += "• Más de 5 años de experiencia en IA\n"
        response += "• Certificaciones internacionales\n"
        response += "• Experiencia práctica en empresas Fortune 500\n"
        response += "• Metodología probada con miles de estudiantes\n\n"
        response += "¿Te gustaría conocer más sobre su metodología de enseñanza? 🎓"
        return response
    
    async def _handle_certificate_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Por supuesto, {user_name}! 🏆\n\n"
        response += "Al completar el curso recibirás:\n"
        response += "• Certificado oficial de Aprende y Aplica IA\n"
        response += "• Reconocimiento internacional\n"
        response += "• Validación en LinkedIn\n"
        response += "• Badge digital para tu perfil profesional\n\n"
        response += "Este certificado te abrirá puertas en el mundo laboral. ¿Hay alguna empresa específica donde te gustaría aplicar estas habilidades? 💼"
        return response
    
    async def _handle_payment_methods(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Perfecto, {user_name}! 💳\n\n"
        response += "Tenemos varias opciones de pago flexibles:\n"
        response += "• Pago único con descuento\n"
        response += "• Pago en 2 cuotas sin intereses\n"
        response += "• Pago en 3 cuotas (pequeño interés)\n"
        response += "• Tarjeta de crédito o débito\n"
        response += "• Transferencia bancaria\n\n"
        response += "¿Cuál opción te resulta más conveniente? 🤔"
        return response
    
    async def _handle_modality_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Excelente pregunta, {user_name}! 🌐\n\n"
        if course_info and course_info.get('online'):
            response += "El curso es *100% online en vivo*:\n"
            response += "• Clases interactivas por videoconferencia\n"
            response += "• Participación en tiempo real\n"
            response += "• Grabaciones disponibles si faltas\n"
            response += "• Acceso desde cualquier lugar\n\n"
        else:
            response += "El curso es *presencial*:\n"
            response += "• Interacción cara a cara\n"
            response += "• Ambiente de aprendizaje colaborativo\n"
            response += "• Networking directo con compañeros\n\n"
        response += "¿Prefieres esta modalidad o tienes alguna preferencia específica? 🤔"
        return response
    
    async def _handle_level_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Buena pregunta, {user_name}! 🎯\n\n"
        if course_info:
            level = course_info.get('level', 'Principiante a Avanzado')
            response += f"*Nivel del curso:* {level}\n\n"
        response += "📈 *Estructura progresiva:*\n"
        response += "• Empezamos desde cero (no necesitas experiencia previa)\n"
        response += "• Avanzamos gradualmente con ejercicios prácticos\n"
        response += "• Llegamos a técnicas avanzadas profesionales\n"
        response += "• Cada estudiante avanza a su ritmo\n\n"
        response += "¿Tienes alguna experiencia previa con IA o sería tu primer acercamiento? 🤓"
        return response
    
    async def _handle_duration_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Perfecto, {user_name}! ⏱\n\n"
        if course_info:
            duration = course_info.get('total_duration', 'N/A')
            response += f"*Duración total:* {duration} horas\n\n"
        response += "📅 *Distribución del tiempo:*\n"
        response += "• Clases semanales de 2 horas\n"
        response += "• Ejercicios prácticos (30 min por semana)\n"
        response += "• Proyecto final (2 horas)\n"
        response += "• Acceso de por vida al material\n\n"
        response += "Es perfecto para profesionales ocupados. ¿Te parece manejable este tiempo de dedicación? 🚀"
        return response
    
    async def _handle_comparison_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Excelente que compares opciones, {user_name}! 🔍\n\n"
        response += "🏆 *Lo que nos diferencia:*\n"
        response += "• Instructores con experiencia real en empresas\n"
        response += "• Metodología práctica (no solo teoría)\n"
        response += "• Grupos pequeños para atención personalizada\n"
        response += "• Soporte continuo durante y después del curso\n"
        response += "• Casos de uso reales de la industria\n"
        response += "• Comunidad activa de ex-alumnos\n\n"
        response += "💡 *Garantía:* Si en las primeras 2 clases no estás satisfecho, te devolvemos el 100% del dinero.\n\n"
        response += "¿Hay algún aspecto específico que te gustaría comparar? 🤔"
        return response
    
    async def _handle_more_info(self, analysis: Dict, message: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja solicitudes de más información - CONVERSACIONAL"""
        
        # Detectar si pide demo específicamente
        if any(word in message.lower() for word in ["demo", "prueba", "muestra", "ejemplo", "preview", "ver"]):
            return await self._handle_demo_request(user_name, course_info)
        
        response = f"¡Por supuesto, {user_name}! Me encanta que quieras conocer más detalles 📋\n\n"
        response += "Antes de bombardearte con información, quiero asegurarme de darte exactamente lo que necesitas.\n\n"
        response += "🎯 **Cuéntame un poco más sobre ti:**\n"
        response += "• ¿A qué te dedicas profesionalmente?\n"
        response += "• ¿Qué te motivó a buscar un curso de IA?\n"
        response += "• ¿Hay algo específico que quieres lograr o automatizar?\n\n"
        response += "📚 **Mientras tanto, aquí tienes lo más importante:**\n"
        response += "• Contenido 100% práctico (nada de teoría aburrida)\n"
        response += "• Ejercicios que puedes aplicar desde el día 1\n"
        response += "• Soporte personalizado durante todo el curso\n"
        response += "• Comunidad activa de profesionales como tú\n\n"
        response += "¿Qué aspecto te interesa más conocer primero? 😊"
        
        return response
    
    async def _handle_demo_request(self, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja solicitudes específicas de demo"""
        response = f"¡Por supuesto, {user_name}! 📱\n\n"
        
        if course_info and course_info.get('demo_request_link'):
            demo_link = course_info['demo_request_link']
            response += f"Aquí tienes acceso directo a la **demo interactiva**:\n"
            response += f"👉 {demo_link}\n\n"
            response += "🎯 **En la demo vas a ver:**\n"
            response += "• Ejercicios reales del curso\n"
            response += "• Metodología paso a paso\n"
            response += "• Resultados que puedes esperar\n"
            response += "• Interface de la plataforma\n\n"
            response += "💡 **Tip**: Tómate 10-15 minutos para explorarla completa. "
            response += "Después me cuentas qué te pareció y resuelvo cualquier duda que tengas.\n\n"
        else:
            response += "Te voy a conectar con nuestro asesor especializado para que te muestre una demo personalizada.\n\n"
            response += "📅 **La demo incluye:**\n"
            response += "• Recorrido completo del curso\n"
            response += "• Ejercicios en vivo\n"
            response += "• Sesión de preguntas y respuestas\n"
            response += "• Plan personalizado para tu caso\n\n"
        
        response += "Mientras tanto, ¿hay algún aspecto específico del curso que te gustaría que enfoque en la demo? 🤔"
        
        return response
    
    async def _handle_testimonials(self, analysis: Dict, message: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja solicitudes de testimonios - CONVERSACIONAL"""
        response = f"¡Me encanta que preguntes eso, {user_name}! 🌟\n\n"
        response += "Los resultados de nuestros estudiantes son lo que más me emociona compartir:\n\n"
        
        response += "💼 **Casos de éxito reales:**\n"
        response += "• **María (Marketing)**: Automatizó reportes y aumentó productividad 300%\n"
        response += "• **Carlos (Ventas)**: Implementó IA en su proceso y aumentó cierre 60%\n"
        response += "• **Ana (Emprendedora)**: Creó su consultora de IA y factura $5K/mes\n"
        response += "• **Luis (Gerente)**: Redujo 15 horas semanales de trabajo repetitivo\n"
        response += "• **Sofia (Estudiante)**: Consiguió pasantía en Google por sus habilidades IA\n\n"
        
        response += "📊 **Estadísticas que nos enorgullecen:**\n"
        response += "• 94% consigue mejor empleo o aumento en 6 meses\n"
        response += "• 87% inicia proyecto propio exitoso relacionado con IA\n"
        response += "• 100% recomienda el curso a colegas\n"
        response += "• Aumento salarial promedio: 40%\n\n"
        
        response += "🤝 **¿Te gustaría hablar directamente con algún ex-alumno?**\n"
        response += "Puedo conectarte con alguien de tu área profesional para que te cuente su experiencia personal.\n\n"
        
        response += "🤔 **Cuéntame:** ¿A qué te dedicas? Así te conecto con alguien que tenga un perfil similar al tuyo. 😊"
        
        return response
    
    async def _handle_support_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Excelente pregunta, {user_name}! 🤝\n\n"
        response += "Nuestro soporte es integral:\n\n"
        response += "📞 *Durante el curso:*\n"
        response += "• Sesiones de Q&A semanales\n"
        response += "• WhatsApp grupal para dudas rápidas\n"
        response += "• Revisión personalizada de proyectos\n"
        response += "• Mentorías individuales (2 por estudiante)\n\n"
        response += "🚀 *Después del curso:*\n"
        response += "• Acceso a comunidad de ex-alumnos\n"
        response += "• Actualizaciones del material sin costo\n"
        response += "• Sesiones de refuerzo mensuales\n"
        response += "• Bolsa de trabajo exclusiva\n\n"
        response += "¿Hay algún tipo de soporte específico que te preocupe? 🤔"
        return response
    
    async def _handle_technical_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Perfecto, {user_name}! 💻\n\n"
        response += "Requisitos técnicos súper simples:\n\n"
        response += "✅ *Lo que necesitas:*\n"
        response += "• Computadora o laptop (Windows/Mac/Linux)\n"
        response += "• Conexión a internet estable\n"
        response += "• Navegador web actualizado\n"
        response += "• ¡Eso es todo!\n\n"
        response += "🛠 *Herramientas que usaremos:*\n"
        response += "• ChatGPT (te enseñamos a configurarlo)\n"
        response += "• Herramientas gratuitas de IA\n"
        response += "• Plataformas web (sin instalaciones)\n\n"
        response += "💡 *Incluido:* Te damos acceso a herramientas premium durante el curso.\n\n"
        response += "¿Tienes alguna limitación técnica específica que te preocupe? 🤖"
        return response
    
    async def _handle_career_question(self, analysis: Dict, message: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Maneja preguntas sobre aplicabilidad profesional - MUY CONVERSACIONAL"""
        message_lower = message.lower()
        
        # Detectar profesión mencionada en el mensaje
        detected_profession = self._extract_profession_from_message(message_lower)
        
        if detected_profession:
            return await self._generate_profession_specific_response(detected_profession, user_name, course_info)
        else:
            # Si no detectamos profesión, ser conversacional y preguntar
            response = f"¡Me encanta esa pregunta, {user_name}! 🚀\n\n"
            response += "La IA está transformando literalmente TODAS las profesiones, y quiero darte ejemplos súper específicos para tu área.\n\n"
            response += "Cuéntame un poco más sobre ti:\n"
            response += "• ¿A qué te dedicas actualmente?\n"
            response += "• ¿Cuál es tu rol principal en tu trabajo?\n"
            response += "• ¿Qué tipo de tareas haces día a día?\n\n"
            response += "Con esa info te voy a dar ejemplos EXACTOS de cómo la IA puede revolucionar tu trabajo específico. 💪\n\n"
            response += "¡Estoy súper curioso de conocer más sobre tu profesión! 😊"
            
            return response
    
    def _extract_profession_from_message(self, message_lower: str) -> Optional[str]:
        """Extrae profesión específica mencionada en el mensaje"""
        profession_keywords = {
            "marketing": ["marketing", "mercadeo", "publicidad", "brand", "redes sociales", "social media"],
            "ventas": ["ventas", "vendedor", "comercial", "sales", "cliente"],
            "gerente": ["gerente", "manager", "jefe", "supervisor", "líder", "coordinador"],
            "estudiante": ["estudiante", "estudio", "universidad", "carrera", "graduado"],
            "emprendedor": ["emprendedor", "startup", "negocio", "empresa propia", "freelance"],
            "desarrollador": ["desarrollador", "programador", "developer", "software", "código"],
            "diseñador": ["diseñador", "diseño", "creative", "gráfico", "ui", "ux"],
            "hr": ["recursos humanos", "rrhh", "hr", "talento", "personal"],
            "finanzas": ["finanzas", "contador", "contabilidad", "financiero", "presupuesto"],
            "educacion": ["profesor", "maestro", "docente", "educador", "instructor"],
            "salud": ["médico", "doctor", "enfermera", "salud", "hospital", "clínica"],
            "abogado": ["abogado", "legal", "derecho", "jurídico", "ley"]
        }
        
        for profession, keywords in profession_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return profession
        return None
    
    async def _generate_profession_specific_response(self, profession: str, user_name: str, course_info: Optional[Dict]) -> str:
        """Genera respuesta específica y conversacional por profesión, SOLO usando información real del curso y ejercicios prácticos."""
        if not course_info:
            return f"No tengo información suficiente sobre el contenido del curso para darte ejemplos específicos para tu profesión, {user_name}. ¿Quieres que te muestre el temario real para que evalúes si se ajusta a tus necesidades?"

        modules = course_info.get('modules', [])
        if isinstance(modules, str):
            import json
            try:
                modules = json.loads(modules.replace("'", '"'))
            except Exception:
                modules = []
        tools_used = course_info.get('tools_used', [])
        if isinstance(tools_used, str):
            import json
            try:
                tools_used = json.loads(tools_used.replace("'", '"'))
            except Exception:
                tools_used = []

        aplicaciones = []
        # NUEVO: consultar ejercicios prácticos relevantes
        if modules and self.course_service:
            for mod in modules:
                mod_name = mod['name'] if isinstance(mod, dict) and 'name' in mod else str(mod)
                mod_desc = mod['description'] if isinstance(mod, dict) and 'description' in mod else ''
                mod_id = mod['id'] if isinstance(mod, dict) and 'id' in mod else None
                mod_lower = mod_name.lower() + ' ' + mod_desc.lower()
                # Buscar ejercicios prácticos del módulo
                ejercicios = []
                if mod_id:
                    try:
                        ejercicios = await self.course_service.getModuleExercises(mod_id)
                    except Exception:
                        ejercicios = []
                # Personalizar ejemplos según profesión
                if profession == 'finanzas' and any(x in mod_lower for x in ['automatización', 'análisis', 'documentos', 'datos', 'reportes']):
                    if ejercicios:
                        for ej in ejercicios:
                            aplicaciones.append(f"• {ej['description']} (aplicable a reportes o documentos contables)")
                    else:
                        aplicaciones.append(f"• Aplicar IA para automatizar reportes financieros o documentos contables en el módulo '{mod_name}'")
                if profession == 'marketing' and any(x in mod_lower for x in ['contenido', 'copy', 'redes', 'publicidad', 'campañas']):
                    if ejercicios:
                        for ej in ejercicios:
                            aplicaciones.append(f"• {ej['description']} (aplicable a campañas o contenido de marketing)")
                    else:
                        aplicaciones.append(f"• Generar contenido o ideas de campañas con IA en el módulo '{mod_name}'")
                if profession == 'ventas' and any(x in mod_lower for x in ['clientes', 'propuestas', 'seguimiento', 'personalización']):
                    if ejercicios:
                        for ej in ejercicios:
                            aplicaciones.append(f"• {ej['description']} (aplicable a ventas o seguimiento de clientes)")
                    else:
                        aplicaciones.append(f"• Automatizar seguimiento de clientes o personalizar propuestas en el módulo '{mod_name}'")
                if profession == 'gerente' and any(x in mod_lower for x in ['análisis', 'estrategia', 'equipos', 'productividad']):
                    if ejercicios:
                        for ej in ejercicios:
                            aplicaciones.append(f"• {ej['description']} (aplicable a gestión de equipos o análisis estratégico)")
                    else:
                        aplicaciones.append(f"• Analizar datos de desempeño de equipos o automatizar reportes estratégicos en el módulo '{mod_name}'")
                if profession == 'estudiante' and any(x in mod_lower for x in ['presentaciones', 'ensayos', 'investigación', 'proyectos']):
                    if ejercicios:
                        for ej in ejercicios:
                            aplicaciones.append(f"• {ej['description']} (aplicable a tareas escolares o proyectos académicos)")
                    else:
                        aplicaciones.append(f"• Automatizar tareas escolares como presentaciones, ensayos o investigación en el módulo '{mod_name}'")
                if profession == 'emprendedor' and any(x in mod_lower for x in ['automatización', 'negocio', 'clientes', 'costos']):
                    if ejercicios:
                        for ej in ejercicios:
                            aplicaciones.append(f"• {ej['description']} (aplicable a operaciones de negocio o análisis de costos)")
                    else:
                        aplicaciones.append(f"• Automatizar operaciones de negocio, atención al cliente o análisis de costos en el módulo '{mod_name}'")
        # Herramientas
        if tools_used:
            for tool in tools_used:
                tool_lower = tool.lower() if isinstance(tool, str) else str(tool).lower()
                if profession == 'finanzas' and any(x in tool_lower for x in ['excel', 'chatgpt', 'canva']):
                    aplicaciones.append('• Usar herramientas como ChatGPT o Excel para crear plantillas automáticas de informes')
                if profession == 'marketing' and any(x in tool_lower for x in ['chatgpt', 'dall', 'canva']):
                    aplicaciones.append('• Crear imágenes, copies o presentaciones para campañas usando IA')
                if profession == 'ventas' and any(x in tool_lower for x in ['chatgpt']):
                    aplicaciones.append('• Generar respuestas automáticas a clientes o scripts de ventas')
        aplicaciones = list(dict.fromkeys(aplicaciones))

        if aplicaciones:
            response = f"¡{user_name}, según el temario real del curso y sus ejercicios prácticos, podrías aplicar lo aprendido así en tu área profesional:\n\n"
            response += '\n'.join(aplicaciones)
            response += "\n\n¿Te gustaría que te comparta más detalles sobre los módulos o ejercicios específicos? 😊"
            return response
        else:
            return f"No tengo información específica en mis datos sobre aplicaciones concretas para tu profesión en este curso, {user_name}. ¿Quieres que te comparta el temario real para que evalúes si se ajusta a tus necesidades?"
    
    async def _handle_group_question(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Buena pregunta, {user_name}! 👥\n\n"
        response += "Mantenemos grupos pequeños para maximizar el aprendizaje:\n\n"
        response += "🎯 *Características del grupo:*\n"
        response += "• Máximo 15 estudiantes por clase\n"
        response += "• Profesionales de diferentes industrias\n"
        response += "• Ambiente colaborativo y de apoyo\n"
        response += "• Networking valioso para tu carrera\n\n"
        response += "🤝 *Beneficios del grupo reducido:*\n"
        response += "• Atención personalizada del instructor\n"
        response += "• Más tiempo para resolver tus dudas\n"
        response += "• Proyectos en equipo enriquecedores\n"
        response += "• Conexiones profesionales duraderas\n\n"
        response += "¿Prefieres grupos pequeños o tienes alguna preferencia específica? 🤔"
        return response
    
    async def _handle_refund_policy(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        response = f"¡Excelente que preguntes, {user_name}! 🛡️\n\n"
        response += "Tenemos una política de satisfacción garantizada:\n\n"
        response += "✅ *Garantía de 14 días:*\n"
        response += "• Si no estás satisfecho en las primeras 2 clases\n"
        response += "• Te devolvemos el 100% de tu dinero\n"
        response += "• Sin preguntas, sin complicaciones\n"
        response += "• Proceso simple y rápido\n\n"
        response += "🎯 *¿Por qué ofrecemos esta garantía?*\n"
        response += "• Confiamos 100% en la calidad del curso\n"
        response += "• Queremos que te sientas seguro al invertir\n"
        response += "• Nuestro éxito depende de tu satisfacción\n\n"
        response += "💡 *Dato:* Menos del 2% de estudiantes pide reembolso.\n\n"
        response += "¿Esta garantía te da más confianza para dar el paso? 😊"
        return response
    
    async def _handle_other(self, analysis: Dict, message: str, user_name: str, course_info: Dict) -> str:
        """Maneja intenciones no clasificadas."""
        response = f"Gracias por tu mensaje, {user_name}. "
        response += "Quiero asegurarme de darte la información más precisa. "
        response += "¿Podrías ser más específico sobre qué te gustaría saber del curso? "
        response += "Por ejemplo:\n\n"
        response += "• Detalles sobre el contenido\n"
        response += "• Información sobre precios\n"
        response += "• Horarios y fechas\n"
        response += "• Proceso de inscripción\n\n"
        response += "¡Estoy aquí para ayudarte! 😊"
        
        return response
    
    def _update_user_memory(self, user_memory: LeadMemory, message: str, analysis: Dict):
        """Actualiza la memoria del usuario con la nueva interacción."""
        if not user_memory.message_history:
            user_memory.message_history = []
        
        user_memory.message_history.append({
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'intention': analysis.get('primary_intention'),
            'interest_level': analysis.get('interest_level'),
            'buying_signals': analysis.get('buying_signals', []),
            'objections': analysis.get('objections', [])
        })
        
        # Actualizar puntuación basada en intención
        if analysis.get('primary_intention') == 'ready_to_buy':
            user_memory.lead_score = min(100, user_memory.lead_score + 20)
        elif analysis.get('interest_level') == 'high':
            user_memory.lead_score = min(100, user_memory.lead_score + 10)
        elif analysis.get('primary_intention') == 'objection':
            user_memory.lead_score = max(0, user_memory.lead_score - 5)
        
        user_memory.last_interaction = datetime.now() 

    def _extract_profession_info(self, message: str, user_memory: LeadMemory) -> Optional[str]:
        """
        Extrae información sobre la profesión del usuario del mensaje.
        """
        message_lower = message.lower()
        
        # Detectar profesiones/roles específicos
        professions = {
            "gerente": ["gerente", "manager", "jefe", "supervisor"],
            "marketing": ["marketing", "mercadeo", "publicidad", "brand"],
            "ventas": ["ventas", "vendedor", "comercial", "sales"],
            "estudiante": ["estudiante", "estudio", "universidad", "carrera"],
            "emprendedor": ["emprendedor", "startup", "negocio propio", "empresa propia"],
            "desarrollador": ["desarrollador", "programador", "developer", "coder"],
            "diseñador": ["diseñador", "diseño", "designer", "creativo"],
            "consultor": ["consultor", "asesor", "freelance", "independiente"],
            "director": ["director", "ceo", "presidente", "ejecutivo"],
            "analista": ["analista", "analyst", "datos", "data"],
            "hr": ["recursos humanos", "rrhh", "hr", "talento humano"],
            "finanzas": ["finanzas", "contabilidad", "contador", "financiero"]
        }
        
        for profession, keywords in professions.items():
            if any(keyword in message_lower for keyword in keywords):
                return profession
        
        return None 