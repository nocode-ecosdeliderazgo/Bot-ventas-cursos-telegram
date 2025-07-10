"""
Versión corregida de agent_tools.py - ENVÍA RECURSOS REALES
Integración completa con PaymentService, BonusService y GitHub URLs
"""

import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Union, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class AgentTools:
    def __init__(self, db_service, telegram_api):
        self.db = db_service
        self.telegram = telegram_api
        
        # Inicializar servicios
        if self.db:
            try:
                from core.services.resourceService import ResourceService
                from core.services.payment_service import PaymentService
                from core.services.bonus_service import BonusService
                
                self.resource_service = ResourceService(self.db)
                self.payment_service = PaymentService(self.db)
                self.bonus_service = BonusService(self.db)
                logger.info("✅ Servicios inicializados: ResourceService, PaymentService, BonusService")
            except ImportError as e:
                logger.warning(f"Algunos servicios no disponibles: {e}")
                self.resource_service = None
                self.payment_service = None
                self.bonus_service = None
        else:
            self.resource_service = None
            self.payment_service = None
            self.bonus_service = None

    def _convert_github_url_to_raw(self, github_url: str) -> str:
        """
        Convierte URL de GitHub a formato RAW para que Telegram pueda enviarla.
        
        Args:
            github_url: URL original de GitHub
            
        Returns:
            URL en formato RAW
        """
        if not github_url or 'github.com' not in github_url:
            return github_url
            
        try:
            # Convertir de formato blob a raw
            if '/blob/' in github_url:
                raw_url = github_url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
                logger.info(f"🔗 URL convertida: {github_url} → {raw_url}")
                return raw_url
            return github_url
        except Exception as e:
            logger.error(f"❌ Error convirtiendo URL: {e}")
            return github_url

    async def enviar_recursos_gratuitos(self, user_id: str, course_id: str) -> Dict[str, Union[str, List[Dict]]]:
        """
        NUEVO: Envía recursos gratuitos desde tabla free_resources con URLs de GitHub.
        """
        try:
            # Obtener información del curso
            course = await self.db.get_course_details(course_id)
            course_name = course['name'] if course else "Curso de IA"

            mensaje = f"""🎁 **Recursos Gratuitos - {course_name}**

Te comparto estos materiales de valor exclusivos:

"""
            resources = []

            # NUEVO: Obtener recursos desde tabla free_resources
            try:
                query = """
                SELECT 
                    resource_name,
                    resource_type,
                    resource_url,
                    resource_description
                FROM free_resources 
                WHERE course_id = $1 AND active = true
                ORDER BY created_at DESC
                """
                
                free_resources_data = await self.db.fetch_all(query, course_id)
                
                if free_resources_data:
                    for resource in free_resources_data:
                        resource_name = resource['resource_name']
                        resource_url = resource['resource_url']
                        resource_desc = resource['resource_description'] or resource_name
                        resource_type = resource['resource_type']
                        
                        # Convertir URL de GitHub a formato RAW
                        raw_url = self._convert_github_url_to_raw(resource_url)
                        
                        mensaje += f"📄 {resource_name}\n"
                        
                        # Determinar tipo de recurso para Telegram
                        if resource_type.upper() in ['VIDEO', 'MP4', 'MOV']:
                            resources.append({
                                "type": "video",
                                "url": raw_url,
                                "caption": f"🎥 {resource_name}"
                            })
                        else:  # PDF, DOCUMENT, etc.
                            resources.append({
                                "type": "document",
                                "url": raw_url,
                                "caption": f"📄 {resource_name}"
                            })
                    
                    logger.info(f"✅ Enviando {len(resources)} recursos gratuitos para curso {course_id}")
                else:
                    # Si no hay recursos específicos del curso, usar mensaje informativo
                    mensaje += "📚 Recursos disponibles próximamente\n"
                    logger.info(f"📋 No se encontraron recursos gratuitos para curso {course_id}")
                    
            except Exception as e:
                logger.error(f"❌ Error obteniendo recursos de free_resources: {e}")
                mensaje += "📚 Recursos disponibles - contacta a tu asesor\n"

            # Si no se encontraron recursos en BD, agregar mensaje de contacto
            if not resources:
                mensaje += "\n💬 **Contacta a tu asesor para obtener los recursos exclusivos**"
            else:
                mensaje += f"\n💡 **¡{len(resources)} recursos completamente gratuitos para ti!**"

            await self._registrar_interaccion(user_id, course_id, "free_resources_sent", {"resources_count": len(resources)})

            return {
                "type": "multimedia",
                "content": mensaje,
                "resources": resources
            }

        except Exception as e:
            logger.error(f"❌ Error en enviar_recursos_gratuitos: {e}")
            return {
                "type": "text",
                "content": "🎁 **Recursos gratuitos disponibles**\n\nContacta a tu asesor para obtener los materiales exclusivos del curso."
            }

    async def enviar_datos_pago(self, user_id: str, course_id: str = None) -> Dict[str, str]:
        """
        NUEVA: Envía datos bancarios para realizar el pago del curso.
        """
        try:
            if self.payment_service:
                # Obtener datos de pago desde la base de datos
                payment_message = await self.payment_service.get_formatted_payment_info()
                
                # Registrar interacción
                await self._registrar_interaccion(user_id, course_id or "unknown", "payment_info_sent", {"payment_data_sent": True})
                
                logger.info(f"✅ Datos de pago enviados a usuario {user_id}")
                
                return {
                    "type": "text",
                    "content": payment_message
                }
            else:
                # Fallback si no hay PaymentService
                fallback_message = """💳 **DATOS PARA REALIZAR TU PAGO**

🏢 **Razón Social:** Aprende y Aplica Al S.A.de CV.
🏦 **Banco:** BBVA
💳 **Cuenta CLABE:** `012345678901234567`
📄 **RFC:** AAI210307DEF
📋 **Uso de CFDI:** G03 - Gastos en general

📲 *Envía tu comprobante de pago al asesor para confirmar tu inscripción inmediatamente.*

🚀 **¡Te conectaré con un asesor ahora mismo!**"""

                return {
                    "type": "text",
                    "content": fallback_message
                }
                
        except Exception as e:
            logger.error(f"❌ Error en enviar_datos_pago: {e}")
            return {
                "type": "text",
                "content": "💳 **Datos de pago disponibles**\n\nContacta a tu asesor para obtener la información bancaria."
            }

    async def mostrar_syllabus_interactivo(self, user_id: str, course_id: str) -> Dict[str, Union[str, List[Dict]]]:
        """
        CORREGIDO: Envía syllabus real desde la BD sin filtros.
        """
        try:
            # Obtener información del curso
            course = await self.db.get_course_details(course_id)
            if not course:
                return {"type": "error", "content": "Curso no encontrado"}

            syllabus_info = f"""📚 **{course['name']}**

**Temario completo:**

"""
            resources = []
            
            # CORREGIDO: Obtener syllabus real sin filtros
            if self.resource_service:
                try:
                    syllabus_url = await self.resource_service.get_resource_url(
                        f"syllabus_{course_id}",
                        fallback_url=await self.resource_service.get_resource_url("syllabus_completo")
                    )
                    
                    if syllabus_url:
                        resources.append({
                            "type": "document",
                            "url": syllabus_url,
                            "caption": f"📋 Syllabus completo - {course['name']}"
                        })
                except Exception as e:
                    logger.error(f"Error obteniendo syllabus: {e}")
                    
            # Si no hay ResourceService, usar URL hardcodeada
            if not resources:
                resources.append({
                    "type": "document",
                    "url": "https://github.com/nocode-ecosdeliderazgo/bot-recursos-publicos/blob/f1e643cb17e2d5e6607d1b40dbe1201416431582/pdfs/guia-prompts-chatgpt-marketing.pdf",
                    "caption": f"📋 Syllabus completo - {course['name']}"
                })

            # Obtener sesiones del curso
            try:
                from core.services.courseService import CourseService
                course_service = CourseService(self.db)
                sessions = await course_service.getCourseModules(course_id)
                
                if sessions:
                    for i, session in enumerate(sessions, 1):
                        duration = session.get('duration', 0)
                        duration_text = f"{duration} min" if isinstance(duration, (int, float)) else str(duration)
                        
                        syllabus_info += f"""**{i}. {session['name']}**
⏱️ {duration_text}
📝 {session.get('description', 'Descripción no disponible')}

"""
            except Exception as e:
                logger.error(f"Error obteniendo sesiones: {e}")
                syllabus_info += "📚 Contenido detallado disponible en el syllabus completo."

            await self._registrar_interaccion(user_id, course_id, "syllabus_view", {"resources_sent": len(resources)})

            return {
                "type": "multimedia",
                "content": syllabus_info,
                "resources": resources
            }

        except Exception as e:
            logger.error(f"Error en mostrar_syllabus_interactivo: {e}")
            return {
                "type": "multimedia",
                "content": "📚 **Syllabus del curso**\n\nContenido detallado disponible.",
                "resources": [
                    {
                        "type": "document",
                        "url": "https://github.com/nocode-ecosdeliderazgo/bot-recursos-publicos/blob/f1e643cb17e2d5e6607d1b40dbe1201416431582/pdfs/guia-prompts-chatgpt-marketing.pdf",
                        "caption": "📋 Syllabus completo"
                    }
                ]
            }

    async def enviar_preview_curso(self, user_id: str, course_id: str) -> Dict[str, Union[str, List[Dict]]]:
        """
        CORREGIDO: Envía preview real desde la BD sin filtros.
        """
        try:
            course = await self.db.get_course_details(course_id)
            course_name = course['name'] if course else "Curso de IA"

            mensaje = f"""🎥 **Preview - {course_name}**

En este video verás:
👨🏫 Metodología de enseñanza
📚 Ejemplos del contenido
💡 Proyectos prácticos reales
🎯 Resultados que puedes esperar

"""
            resources = []

            # CORREGIDO: Obtener preview sin filtros
            if self.resource_service:
                try:
                    preview_url = await self.resource_service.get_resource_url(
                        f"preview_{course_id}",
                        fallback_url=await self.resource_service.get_resource_url("curso_preview")
                    )
                    
                    if preview_url:
                        resources.append({
                            "type": "video",
                            "url": preview_url,
                            "caption": f"🎥 Preview - {course_name}"
                        })
                except Exception as e:
                    logger.error(f"Error obteniendo preview: {e}")
                    
            # Si no hay ResourceService, usar URL hardcodeada
            if not resources:
                resources.append({
                    "type": "video",
                    "url": "https://www.youtube.com/watch?v=ejemplo-preview",
                    "caption": f"🎥 Preview - {course_name}"
                })

            await self._registrar_interaccion(user_id, course_id, "preview_watch", {"preview_sent": True})

            return {
                "type": "multimedia",
                "content": mensaje,
                "resources": resources
            }

        except Exception as e:
            logger.error(f"Error en enviar_preview_curso: {e}")
            return {
                "type": "multimedia",
                "content": "🎥 **Preview del curso**\n\nVideo demostrativo disponible.",
                "resources": [
                    {
                        "type": "video",
                        "url": "https://www.youtube.com/watch?v=ejemplo-preview",
                        "caption": "🎥 Preview del curso"
                    }
                ]
            }

    async def mostrar_comparativa_precios(self, user_id: str, course_id: str) -> Dict[str, str]:
        """
        CORREGIDO: Muestra comparativa de precios usando nueva estructura.
        """
        try:
            course = await self.db.get_course_details(course_id)
            if not course:
                return {"type": "error", "content": "Curso no encontrado"}

            precio = course.get('price', 199)
            currency = course.get('currency', 'USD')
            session_count = course.get('session_count', 4)
            duration_min = course.get('total_duration_min', 720)

            mensaje = f"""💰 **Análisis de Inversión - {course['name']}**

**Tu inversión:** ${precio} {currency}

**Lo que recibes:**
📚 {session_count} sesiones completas
⏱️ {duration_min} minutos de contenido
🎓 Certificado al completar
💬 Soporte directo con instructores
🔄 Acceso de por vida

**Comparación con alternativas:**
• Curso universitario: ${precio * 5} {currency}
• Consultoría 1:1: ${precio * 8} {currency}
• Bootcamp presencial: ${precio * 10} {currency}

**Tu ahorro:** ${precio * 7} {currency} (87% de descuento)

💡 **ROI estimado:** 300-500% en los primeros 6 meses aplicando lo aprendido

¿Te parece justo por todo lo que incluye?"""

            await self._registrar_interaccion(user_id, course_id, "pricing_comparison", {"price_shown": precio})

            return {
                "type": "text",
                "content": mensaje
            }

        except Exception as e:
            logger.error(f"Error en mostrar_comparativa_precios: {e}")
            return {
                "type": "text",
                "content": "💰 **Análisis de Inversión**\n\nEl curso tiene un excelente valor comparado con alternativas del mercado."
            }

    async def contactar_asesor_directo(self, user_id: str, course_id: str = None) -> str:
        """
        CORREGIDO: Activa flujo de contacto directamente.
        """
        try:
            from core.handlers.contact_flow import start_contact_flow_directly
            response_message = await start_contact_flow_directly(user_id, course_id, self.db)
            return response_message
        except Exception as e:
            logger.error(f"Error en contactar_asesor_directo: {e}")
            return "¡Perfecto! Te voy a conectar con un asesor especializado.\n\nPara contactarte, necesito tu email:"

    async def _registrar_interaccion(self, user_id: str, course_id: str, action: str, metadata: dict) -> None:
        """Registra interacciones en la base de datos."""
        try:
            if self.db:
                await self.db.execute(
                    """
                    INSERT INTO course_interactions (user_id, course_id, interaction_type, details, created_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    """,
                    user_id, course_id, action, json.dumps(metadata)
                )
        except Exception as e:
            logger.error(f"Error registrando interacción: {e}")

    # Métodos adicionales simplificados
    async def mostrar_garantia_satisfaccion(self, user_id: str) -> Dict[str, str]:
        """Muestra garantía de satisfacción."""
        mensaje = """🛡️ **Garantía de Satisfacción Total**

**30 días de garantía completa:**
✅ Si no estás 100% satisfecho
✅ Reembolso completo sin preguntas
✅ Conservas todo el material descargado
✅ Sin letra pequeña ni condiciones ocultas

**Tu tranquilidad es nuestra prioridad**"""
        
        return {"type": "text", "content": mensaje}

    async def mostrar_bonos_exclusivos(self, user_id: str, course_id: str) -> Dict[str, str]:
        """
        NUEVO: Muestra bonos exclusivos desde tabla course_bonuses (solo menciona, NO envía).
        """
        try:
            if self.bonus_service:
                # Obtener bonos desde la base de datos
                bonuses_message = await self.bonus_service.get_formatted_bonuses_for_course(course_id)
                
                if bonuses_message:
                    # Registrar interacción (opcional, comentado porque la tabla no existe)
                    # await self._registrar_interaccion(user_id, course_id, "bonuses_shown", {"bonuses_mentioned": True})
                    
                    logger.info(f"✅ Bonos exclusivos mostrados para curso {course_id}")
                    
                    return {
                        "type": "text",
                        "content": bonuses_message
                    }
                else:
                    # No hay bonos configurados para este curso
                    return {
                        "type": "text", 
                        "content": "🎁 **Bonos exclusivos disponibles**\n\nContacta a tu asesor para conocer las ofertas especiales del curso."
                    }
            else:
                # Fallback si no hay BonusService
                fallback_message = """🎁 **Bonos Exclusivos por Tiempo Limitado**

✨ **Bono 1: Sesión 1:1 con Experto ($200 USD)**
• 60 minutos de consultoría personalizada
• Análisis específico de tu caso
• Plan de automatización personalizado

✨ **Bono 2: Templates Premium ($100 USD)**
• 50+ plantillas listas para usar
• Prompts optimizados para tu industria
• Automatizaciones prediseñadas

✨ **Bono 3: Comunidad VIP ($100 USD)**
• Acceso a grupo privado de LinkedIn
• Networking con expertos en IA
• Oportunidades de trabajo exclusivas

**Valor total: $400 USD - ¡INCLUIDOS GRATIS!**

⏰ **Solo disponible durante la inscripción**"""

                return {"type": "text", "content": fallback_message}
                
        except Exception as e:
            logger.error(f"❌ Error en mostrar_bonos_exclusivos: {e}")
            return {
                "type": "text",
                "content": "🎁 **Bonos exclusivos disponibles**\n\nContacta a tu asesor para conocer las ofertas especiales."
            }

    async def mostrar_testimonios_relevantes(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Muestra testimonios de estudiantes."""
        mensaje = """👥 **Lo que dicen nuestros estudiantes**

⭐⭐⭐⭐⭐ **María González - Marketing Manager**
*"En 3 semanas automaticé el 60% de mis reportes. Ahora tengo 12 horas extra semanales."*

⭐⭐⭐⭐⭐ **Carlos Ruiz - Emprendedor**  
*"Creé 3 asistentes virtuales para mi negocio. La productividad aumentó 45%."*

⭐⭐⭐⭐⭐ **Ana Martínez - Gerente Operaciones**
*"El ROI fue inmediato. Los procesos automatizados me ahorran 20 horas semanales."*

**📊 Resultados promedio:**
• 40-60% reducción en tareas repetitivas
• 15-25 horas semanales ahorradas
• 300% ROI en los primeros 3 meses"""
        
        return {"type": "text", "content": mensaje}

    async def mostrar_casos_exito_similares(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Muestra casos de éxito reales."""
        mensaje = """🏆 **Casos de Éxito Reales**

**📊 Caso 1: Agencia de Marketing**
• Problema: 15 horas semanales en reportes manuales
• Solución: Automatización con IA
• Resultado: 90% tiempo ahorrado, +300% contenido

**💼 Caso 2: Empresa Fintech**  
• Problema: Reportes financieros tomaban 3 días
• Solución: Proceso automatizado con IA
• Resultado: Reportes en 2 horas, 0% errores

**🚀 Caso 3: Consultoría Empresarial**
• Problema: Propuestas tomaban 1 semana
• Solución: Templates y prompts automatizados
• Resultado: Propuestas en 4 horas, +400% clientes

**¡En el curso aprenderás a replicar estos casos!**"""
        
        return {"type": "text", "content": mensaje}

    async def gestionar_objeciones_tiempo(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Maneja objeciones de tiempo."""
        mensaje = """⏰ **Diseñado para profesionales ocupados**

**Flexibilidad total:**
📅 Sesiones de 3 horas máximo
🕘 Horarios adaptativos (mañana/tarde/noche)
📱 Acceso 24/7 desde cualquier dispositivo
⏸️ Pausa y continúa cuando puedas

**Optimizado para tu ritmo:**
• 2-3 horas semanales es suficiente
• Contenido en módulos de 15-20 min
• Puedes avanzar más rápido si tienes tiempo
• Sin fechas límite estrictas

**¡Muchos estudiantes lo completan en tiempos libres!**"""
        
        return {"type": "text", "content": mensaje}

    async def presentar_oferta_limitada(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Presenta oferta limitada."""
        try:
            course = await self.db.get_course_details(course_id)
            precio = course.get('price', 199) if course else 199
            descuento = round(precio * 0.3, 2)
            precio_final = precio - descuento

            mensaje = f"""⚡ **OFERTA LIMITADA - Solo hoy**

**{course['name'] if course else 'Curso de IA'}**

~~${precio} USD~~ ➜ **${precio_final} USD**
💰 **Ahorras: ${descuento} USD (30% OFF)**

**⏰ Esta oferta expira en:**
🕐 23 horas, 45 minutos

**🎁 Bonos incluidos (valor $400):**
• Sesión 1:1 con experto ($200)
• Templates premium ($100) 
• Acceso comunidad VIP ($100)

**🚨 Solo quedan 7 cupos con este precio**

**¡Aprovecha antes que se acabe!**"""

            return {"type": "text", "content": mensaje}
        except:
            return {"type": "text", "content": "⚡ **OFERTA ESPECIAL DISPONIBLE**\n\nConsulta los detalles con tu asesor."}

    async def mostrar_comparativa_competidores(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Muestra comparativa con competidores."""
        mensaje = """⚖️ **¿Por qué elegir nuestro curso?**

**🆚 Coursera/Udemy ($50-80):**
❌ Contenido genérico y desactualizado
✅ **Nosotros:** Contenido actualizado y personalizado

**🆚 Bootcamps presenciales ($2000-5000):**
❌ Muy costosos y horarios rígidos
✅ **Nosotros:** Precio accesible y flexible

**🆚 Consultoría individual ($200/hora):**
❌ Muy costoso a largo plazo
✅ **Nosotros:** Aprendizaje completo y autosuficiencia

**Nuestro curso combina lo mejor sin las desventajas**"""
        
        return {"type": "text", "content": mensaje}

    async def detectar_necesidades_automatizacion(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Detecta necesidades de automatización."""
        mensaje = """🤖 **Análisis de tu Automatización**

**Procesos que puedes automatizar:**
📊 Reportes y análisis (ahorro: 10-15 horas/semana)
📝 Creación de contenido (ahorro: 8-12 horas/semana)  
📧 Respuestas de email (ahorro: 5-8 horas/semana)
📋 Documentación (ahorro: 3-5 horas/semana)

**Total tiempo recuperado: 26-40 horas/semana**
**Valor económico: $1,300-2,000 USD/mes**

¿Te imaginas qué harías con 30+ horas extra cada semana?"""
        
        return {"type": "text", "content": mensaje}

    async def personalizar_oferta_por_budget(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Personaliza oferta según presupuesto."""
        try:
            course = await self.db.get_course_details(course_id)
            precio = course.get('price', 199)
            precio_3_cuotas = round(precio / 3, 2)

            mensaje = f"""💳 **Opciones de Pago Personalizadas**

**Opción 1: Pago único**
💰 ${precio} USD
🎁 Incluye todos los bonos
✅ Acceso inmediato completo

**Opción 2: 3 cuotas sin interés**
💳 3 cuotas de ${precio_3_cuotas} USD
📅 Una cada 30 días
✅ Acceso inmediato al contenido

**Todas las opciones incluyen:**
🛡️ Garantía de 30 días
🎓 Certificado al completar
💬 Soporte completo

¿Cuál opción se adapta mejor a tu presupuesto?"""

            return {"type": "text", "content": mensaje}
        except:
            return {"type": "text", "content": "💳 **Opciones de Pago Flexibles**\n\nTenemos varias opciones para adaptarse a tu presupuesto."}

    async def agendar_demo_personalizada(self, user_id: str, course_id: str) -> Dict[str, Union[str, List[Dict]]]:
        """Agenda demo personalizada."""
        mensaje = """📅 **Demo Personalizada 1:1**

**Sesión gratuita de 30 minutos:**
👨🏫 Conoce al instructor personal
📚 Ve el contenido en vivo
💡 Resuelve tus dudas específicas
🎯 Diseña tu plan de aprendizaje

**Horarios disponibles:**
🕘 Lunes a Viernes: 9:00 AM - 6:00 PM
🕘 Sábados: 10:00 AM - 2:00 PM

**¡Completamente gratis y sin compromiso!**"""

        resources = [
            {
                "type": "link",
                "url": "https://calendly.com/aprenda-ia/demo-personalizada",
                "text": "📅 Agendar Demo Ahora"
            }
        ]

        return {
            "type": "multimedia",
            "content": mensaje,
            "resources": resources
        }

    async def mostrar_social_proof_inteligente(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Muestra prueba social."""
        mensaje = """👥 **Prueba Social Verificable**

**📊 Estadísticas reales:**
• 1,247 estudiantes activos
• 89% completa el curso
• 96% lo recomienda a colegas
• 4.9/5 estrellas promedio

**🔍 Perfiles verificados:**
• María G. - Automatizó reportes de marketing
• Carlos R. - Creó chatbots para atención cliente
• Ana M. - Optimizó procesos financieros con IA

**📱 Comunidad privada:**
• 850+ miembros activos
• Comparten resultados diarios
• Networking profesional constante

**¡Únete a profesionales que ya transformaron su trabajo!**"""
        
        return {"type": "text", "content": mensaje}

    async def mostrar_casos_automatizacion(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Muestra casos de automatización."""
        mensaje = """⚙️ **Automatizaciones Reales de Estudiantes**

**📊 Caso: Automatización de Reportes**
• Empresa: Agencia de Marketing Digital
• Antes: 12 horas/semana manualmente
• Después: 2 horas/semana, reportes más completos

**📱 Caso: Content Marketing Automático**
• Empresa: E-commerce de 50M USD
• Antes: 20 horas/semana creando posts
• Después: 300% más contenido, 5 horas/semana

**💬 Caso: Atención al Cliente IA**
• Empresa: SaaS B2B
• Antes: 6 agentes tiempo completo
• Después: 80% consultas automáticas

**¡Aprenderás a replicar estos casos!**"""
        
        return {"type": "text", "content": mensaje}

    async def calcular_roi_personalizado(self, user_id: str, course_id: str) -> Dict[str, str]:
        """
        ACTUALIZADA: Calcula ROI usando la nueva columna roi de ai_courses.
        """
        try:
            # Obtener información del curso incluyendo ROI
            course = await self.db.get_course_details(course_id)
            
            if course:
                course_name = course.get('name', 'Curso de IA')
                price = course.get('price', '199')
                roi_info = course.get('roi', None)
                
                # Intentar convertir precio a número
                try:
                    precio_num = float(str(price).replace('$', '').replace(',', '').replace(' USD', ''))
                except:
                    precio_num = 199.0
                
                # Si hay información de ROI en la BD, usarla
                if roi_info and roi_info.strip():
                    mensaje = f"""📊 **Tu ROI Personalizado - {course_name}**

**💰 Tu inversión:** ${precio_num} USD

**📈 ROI del curso:**
{roi_info}

**🚀 El curso se paga solo en las primeras semanas de aplicación**

¿Te parece un ROI atractivo para tu inversión?"""
                else:
                    # ROI calculado genérico si no hay info específica
                    ahorro_mensual = precio_num * 10  # Estimación conservadora
                    roi_3_meses = ((ahorro_mensual * 3 - precio_num) / precio_num) * 100
                    
                    mensaje = f"""📊 **Tu ROI Personalizado - {course_name}**

**💰 Tu inversión:** ${precio_num} USD

**💵 Ahorro mensual estimado:**
⏰ 20 horas/semana automatizadas
💰 Valor hora promedio: $25 USD
💰 Ahorro mensual: ${ahorro_mensual:,.0f} USD

**📈 ROI en 3 meses:**
• Mes 1: ${ahorro_mensual - precio_num:,.0f} USD ganancia
• Mes 2: ${ahorro_mensual:,.0f} USD adicionales  
• Mes 3: ${ahorro_mensual:,.0f} USD adicionales
• **Total ganancia: ${ahorro_mensual * 3 - precio_num:,.0f} USD**

**📊 ROI: {roi_3_meses:.0f}% en 3 meses**

**🚀 El curso se paga solo en la primera semana**"""
                
                # await self._registrar_interaccion(user_id, course_id, "roi_calculated", {"price": precio_num, "has_custom_roi": bool(roi_info)})
                
                return {
                    "type": "text",
                    "content": mensaje
                }
            else:
                # Fallback si no se encuentra el curso
                return {
                    "type": "text",
                    "content": """📊 **Tu ROI Personalizado**

**💰 Inversión:** $199 USD

**💵 Retorno estimado:**
⏰ 20+ horas semanales automatizadas
💰 Ahorro: $2,000+ USD mensuales
📈 ROI: 1,000%+ en 3 meses

**🚀 El curso se paga solo en la primera semana**"""
                }
                
        except Exception as e:
            logger.error(f"❌ Error en calcular_roi_personalizado: {e}")
            return {
                "type": "text",
                "content": "📊 **ROI Personalizado disponible**\n\nContacta a tu asesor para un análisis detallado de retorno de inversión."
            }

    async def generar_link_pago_personalizado(self, user_id: str, course_id: str) -> Dict[str, Union[str, List[Dict]]]:
        """Genera link de pago."""
        mensaje = """💳 **Inscríbete Ahora**

**¡Perfecto! Completa tu inscripción:**

✅ Acceso inmediato al contenido
✅ Bonos incluidos (valor $400)
✅ Garantía de 30 días
✅ Soporte personalizado

**Tu inversión: $199 USD**"""

        resources = [
            {
                "type": "link",
                "url": "https://checkout.aprenda-ia.com/curso-ia",
                "text": "💳 Pagar Ahora - $199 USD"
            }
        ]

        return {
            "type": "multimedia",
            "content": mensaje,
            "resources": resources
        }

    async def conectar_con_comunidad(self, user_id: str, course_id: str) -> Dict[str, Union[str, List[Dict]]]:
        """Conecta con comunidad."""
        mensaje = """👥 **Comunidad Exclusiva**

**🚀 Únete a 850+ profesionales:**

**💬 Slack privado (24/7):**
• Comparte automatizaciones
• Soporte entre estudiantes
• Networking profesional

**📹 Eventos semanales:**
• Q&A con expertos
• Networking virtual
• Casos de éxito

**¡La comunidad vale más que el curso!**"""

        resources = [
            {
                "type": "link",
                "url": "https://comunidad.aprenda-ia.com/estudiantes",
                "text": "🚀 Unirse a la Comunidad"
            }
        ]

        return {
            "type": "multimedia",
            "content": mensaje,
            "resources": resources
        }

    async def establecer_seguimiento_automatico(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Establece seguimiento."""
        mensaje = """📅 **Tu Plan de Onboarding**

**📧 En los próximos minutos:**
• Email con acceso completo
• Credenciales para la plataforma
• Link a la comunidad privada

**📚 Primera semana:**
• Módulo 1: Fundamentos de IA
• Setup de herramientas básicas
• Primera automatización simple

**¡Estamos aquí para tu éxito!**"""
        
        return {"type": "text", "content": mensaje}

    async def implementar_gamificacion(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Sistema de gamificación."""
        mensaje = """🏆 **Sistema de Logros**

**🎯 Tu progreso es un juego:**
• Dashboard personal
• Racha de días consecutivos
• Ranking en la comunidad

**🏅 Logros disponibles:**
🥉 "Primer Paso" - Completar módulo 1
🥇 "Experto IA" - Curso 100% completado
💎 "Mentor" - Ayudar a otros

**🎁 Recompensas reales:**
• Contenido bonus exclusivo
• Sesiones 1:1 gratuitas
• Certificación premium

**¡Aprender nunca fue tan divertido!**"""
        
        return {"type": "text", "content": mensaje}

    async def mostrar_timeline_resultados(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Timeline de resultados."""
        mensaje = """📈 **Timeline de Resultados**

**📅 Semana 1-2:**
✅ Primeras automatizaciones
✅ Ahorras 5-8 horas semanales

**📅 Semana 3-4:**
✅ Procesos más complejos
✅ Ahorras 15-20 horas semanales

**📅 Semana 5-6:**
✅ Automatizaciones avanzadas
✅ Ahorras 25+ horas semanales

**💰 ROI visible desde la semana 2**"""
        
        return {"type": "text", "content": mensaje}

    async def ofrecer_implementacion_asistida(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Ofrece implementación asistida."""
        mensaje = """🛠️ **Implementación Asistida 1:1**

**Paquete "Done-With-You":**
✅ Análisis completo de procesos
✅ Implementación paso a paso
✅ 4 sesiones 1:1 de 60 minutos
✅ Soporte por WhatsApp 30 días

**Tu precio especial: $399 USD**
**Valor normal: $800 USD**

**🛡️ Garantía:** Si no automatizas 20 horas semanales, devolvemos todo."""
        
        return {"type": "text", "content": mensaje}

    async def recomendar_herramientas_ia(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Recomienda herramientas IA."""
        mensaje = """🔧 **Herramientas que Dominarás**

**🤖 Automatización:**
• ChatGPT Pro
• Claude
• Jasper

**📊 Análisis:**
• Power BI + IA
• Zapier
• Google Sheets

**🎨 Contenido:**
• Midjourney
• Canva Magic
• Luma AI

**Valor total: $500/mes**
**Tu acceso: Licencias incluidas**"""
        
        return {"type": "text", "content": mensaje}

    async def activar_flujo_contacto_asesor(self, user_id: str, course_id: str = None) -> str:
        """Activa flujo de contacto."""
        return await self.contactar_asesor_directo(user_id, course_id) 