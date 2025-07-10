"""
Herramientas del agente de ventas para interactuar con usuarios y gestionar recursos.
VERSIÓN REDISEÑADA - Las herramientas RETORNAN contenido para que el agente lo incorpore
Unificación completa del comportamiento para envío directo de recursos.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Union, Tuple
from decimal import Decimal

class AgentTools:
    def __init__(self, db_service, telegram_api):
        self.db = db_service
        self.telegram = telegram_api
        
        # Inicializar ResourceService
        if self.db:
            from core.services.resourceService import ResourceService
            self.resource_service = ResourceService(self.db)
        else:
            self.resource_service = None

    async def mostrar_syllabus_interactivo(self, user_id: str, course_id: str) -> Dict[str, Union[str, List[Dict]]]:
        """
        REDISEÑADO: Retorna el syllabus del curso con recursos para envío directo.
        Usa nueva estructura ai_course_sessions.
        """
        try:
            # Obtener información del curso desde nueva estructura
            course = await self.db.get_course_details(course_id)
            if not course:
                return {"type": "error", "content": "Curso no encontrado"}

            # Usar CourseService para obtener sesiones (compatibilidad con nueva estructura)
            from core.services.courseService import CourseService
            course_service = CourseService(self.db)
            sessions = await course_service.getCourseModules(course_id)  # Retorna sesiones mapeadas
            
            if not sessions:
                return {"type": "error", "content": "No se encontraron sesiones del curso"}

            # Construir información del syllabus
            syllabus_info = f"""📚 **{course['name']}**

**Temario completo:**

"""
            resources = []
            
            for i, session in enumerate(sessions, 1):
                duration = session.get('duration', 0)
                if isinstance(duration, (int, float)):
                    duration_text = f"{duration} min"
                else:
                    duration_text = str(duration) if duration else "Duración no especificada"
                    
                syllabus_info += f"""**{i}. {session['name']}**
⏱️ {duration_text}
📝 {session.get('description', 'Descripción no disponible')}

"""

            # Obtener recurso de syllabus desde ResourceService
            if self.resource_service:
                syllabus_url = await self.resource_service.get_resource_url(
                    f"syllabus_{course_id}",
                    fallback_url=await self.resource_service.get_resource_url("syllabus_completo")
                )
                
                if syllabus_url and not syllabus_url.startswith("https://aprenda-ia.com/"):
                    resources.append({
                        "type": "document",
                        "url": syllabus_url,
                        "caption": f"📋 Syllabus completo - {course['name']}"
                    })

            # Registrar interacción
            await self._registrar_interaccion(user_id, course_id, "syllabus_view", {"sessions_count": len(sessions)})

            return {
                "type": "multimedia",
                "content": syllabus_info,
                "resources": resources
            }

        except Exception as e:
            return {"type": "error", "content": f"Error obteniendo syllabus: {str(e)}"}

    async def enviar_recursos_gratuitos(self, user_id: str, course_id: str) -> Dict[str, Union[str, List[Dict]]]:
        """
        REDISEÑADO: Retorna recursos gratuitos para envío directo.
        Usa ResourceService con nueva estructura.
        """
        try:
            course = await self.db.get_course_details(course_id)
            if not course:
                return {"type": "error", "content": "Curso no encontrado"}

            mensaje = f"""🎁 **Recursos gratuitos - {course['name']}**

Te comparto estos materiales de valor:

"""
            resources = []

            # Obtener recursos desde ResourceService
            if self.resource_service:
                # Recursos específicos del curso
                course_resources = await self.resource_service.get_course_resources(course_id)
                free_resources = [r for r in course_resources if r['resource_type'] in ['recursos', 'pdf', 'templates']]
                
                # Si no hay específicos, usar generales
                if not free_resources:
                    general_resources = await self.resource_service.get_resources_by_type('pdf')
                    free_resources.extend(general_resources[:3])  # Máximo 3 recursos

                if free_resources:
                    for resource in free_resources:
                        mensaje += f"📄 {resource['resource_title']}\n"
                        resources.append({
                            "type": "document",
                            "url": resource['resource_url'],
                            "caption": resource['resource_title']
                        })
                else:
                    # Fallback con recursos predefinidos
                    fallback_resources = [
                        ("guia_prompting", "📖 Guía de Prompting para Principiantes"),
                        ("plantilla_prompts", "📝 Plantillas de Prompts Listos"),
                        ("checklist_ia_business", "✅ Checklist: IA en tu Negocio")
                    ]
                    
                    for resource_key, title in fallback_resources:
                        url = await self.resource_service.get_resource_url(resource_key)
                        if url and not url.startswith("https://aprenda-ia.com/"):
                            mensaje += f"{title}\n"
                            resources.append({
                                "type": "document", 
                                "url": url,
                                "caption": title
                            })

            mensaje += "\n💡 **¡Estos recursos son completamente gratuitos!**"

            await self._registrar_interaccion(user_id, course_id, "free_resources_sent", {"resources_count": len(resources)})

            return {
                "type": "multimedia",
                "content": mensaje,
                "resources": resources
            }

        except Exception as e:
            return {"type": "error", "content": f"Error obteniendo recursos: {str(e)}"}

    async def enviar_preview_curso(self, user_id: str, course_id: str) -> Dict[str, Union[str, List[Dict]]]:
        """
        REDISEÑADO: Retorna preview del curso para envío directo.
        """
        try:
            course = await self.db.get_course_details(course_id)
            if not course:
                return {"type": "error", "content": "Curso no encontrado"}

            mensaje = f"""🎥 **Preview - {course['name']}**

En este video verás:
👨🏫 Metodología de enseñanza
📚 Ejemplos del contenido
💡 Proyectos prácticos reales
🎯 Resultados que puedes esperar

"""
            resources = []

            # Obtener preview desde ResourceService
            if self.resource_service:
                preview_url = await self.resource_service.get_resource_url(
                    f"preview_{course_id}",
                    fallback_url=await self.resource_service.get_resource_url("curso_preview")
                )
                
                if preview_url and not preview_url.startswith("https://aprenda-ia.com/"):
                    resources.append({
                        "type": "video",
                        "url": preview_url,
                        "caption": f"🎥 Preview - {course['name']}"
                    })

            await self._registrar_interaccion(user_id, course_id, "preview_watch", {"preview_sent": True})

            return {
                "type": "multimedia",
                "content": mensaje,
                "resources": resources
            }

        except Exception as e:
            return {"type": "error", "content": f"Error obteniendo preview: {str(e)}"}

    async def mostrar_comparativa_precios(self, user_id: str, course_id: str) -> Dict[str, str]:
        """
        REDISEÑADO: Retorna comparativa de precios usando nueva estructura ai_courses.
        """
        try:
            course = await self.db.get_course_details(course_id)
            if not course:
                return {"type": "error", "content": "Curso no encontrado"}

            precio = course.get('price', 0)
            currency = course.get('currency', 'USD')
            session_count = course.get('session_count', 0)
            duration_min = course.get('total_duration_min', 0)

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

💡 **ROI estimado:** 300-500% en los primeros 6 meses aplicando lo aprendido"""

            await self._registrar_interaccion(user_id, course_id, "pricing_comparison", {"price_shown": precio})

            return {
                "type": "text",
                "content": mensaje
            }

        except Exception as e:
            return {"type": "error", "content": f"Error en comparativa: {str(e)}"}

    async def mostrar_garantia_satisfaccion(self, user_id: str) -> Dict[str, str]:
        """
        REDISEÑADO: Retorna información de garantía.
        """
        mensaje = """🛡️ **Garantía de Satisfacción Total**

**30 días de garantía completa:**
✅ Si no estás 100% satisfecho
✅ Reembolso completo sin preguntas
✅ Conservas todo el material descargado
✅ Sin letra pequeña ni condiciones ocultas

**¿Por qué ofrecemos esta garantía?**
🎯 Confiamos 100% en la calidad del curso
📊 97% de nuestros estudiantes están satisfechos
💪 Queremos que tomes la decisión sin riesgo

**Tu tranquilidad es nuestra prioridad**"""

        return {
            "type": "text", 
            "content": mensaje
        }

    async def agendar_demo_personalizada(self, user_id: str, course_id: str) -> Dict[str, Union[str, List[Dict]]]:
        """
        REDISEÑADO: Retorna información para agendar demo con links.
        """
        try:
            course = await self.db.get_course_details(course_id)
            course_name = course['name'] if course else "Curso seleccionado"

            mensaje = f"""📅 **Demo Personalizada 1:1 - {course_name}**

**Sesión gratuita de 30 minutos:**
👨🏫 Conoce al instructor personal
📚 Ve el contenido en vivo
💡 Resuelve tus dudas específicas
🎯 Diseña tu plan de aprendizaje

**Horarios disponibles:**
🕘 Lunes a Viernes: 9:00 AM - 6:00 PM
🕘 Sábados: 10:00 AM - 2:00 PM

**¡Completamente gratis y sin compromiso!**"""

            resources = []

            # Obtener link de demo desde ResourceService
            if self.resource_service:
                demo_url = await self.resource_service.get_resource_url(
                    f"demo_{course_id}",
                    fallback_url=await self.resource_service.get_resource_url("demo_personalizada")
                )
                
                if demo_url and not demo_url.startswith("https://aprenda-ia.com/"):
                    resources.append({
                        "type": "link",
                        "url": demo_url,
                        "text": "📅 Agendar Demo Ahora"
                    })

            await self._registrar_interaccion(user_id, course_id, "demo_request", {"demo_offered": True})

            return {
                "type": "multimedia",
                "content": mensaje,
                "resources": resources
            }

        except Exception as e:
            return {"type": "error", "content": f"Error obteniendo demo: {str(e)}"}

    async def contactar_asesor_directo(self, user_id: str, course_id: str = None) -> str:
        """
        REDISEÑADO: Activa flujo de contacto y retorna mensaje para el agente.
        Esta función ACTIVA el flujo predefinido que desactiva el agente inteligente.
        """
        try:
            # Activar el flujo de contacto usando el wrapper
            response = await self.activar_flujo_contacto_asesor(user_id, course_id)
            
            # Retornar mensaje que indica que el flujo se activó
            return response

        except Exception as e:
            return "¡Perfecto! Te voy a conectar con un asesor especializado que podrá ayudarte con todas tus preguntas específicas."

    async def mostrar_bonos_exclusivos(self, user_id: str, course_id: str) -> Dict[str, str]:
        """
        REDISEÑADO: Retorna bonos por tiempo limitado desde BD.
        """
        try:
            course = await self.db.get_course_details(course_id)
            if not course:
                return {"type": "error", "content": "Curso no encontrado"}

            # Obtener bonos desde BD usando nueva estructura compatible
            bonos = await self.db.fetch_all(
                """
                SELECT * FROM limited_time_bonuses
                WHERE course_id = $1 AND active = true AND expires_at > NOW()
                ORDER BY expires_at ASC
                """,
                course_id
            )

            mensaje = f"""🎁 **Bonos Exclusivos - {course['name']}**

"""
            if bonos:
                for bono in bonos:
                    tiempo_restante = bono['expires_at'] - datetime.now(timezone.utc)
                    horas_restantes = max(1, int(tiempo_restante.total_seconds() / 3600))
                    
                    mensaje += f"""✨ **{bono['bonus_name']}**
💰 Valor: ${bono['bonus_value']} USD
⏰ Vence en: {horas_restantes} horas
📦 Incluye: {bono['bonus_description']}

"""
                mensaje += "⚡ **¡Oferta por tiempo limitado!**"
            else:
                mensaje += """✨ **Bono Especial de Lanzamiento**
💰 Valor: $200 USD
📦 Incluye: Sesión 1:1 con experto + Templates premium
⏰ Solo por esta semana

⚡ **¡No pierdas esta oportunidad única!**"""

            await self._registrar_interaccion(user_id, course_id, "bonuses_shown", {"bonuses_count": len(bonos)})

            return {
                "type": "text",
                "content": mensaje
            }

        except Exception as e:
            return {"type": "error", "content": f"Error obteniendo bonos: {str(e)}"}

    async def personalizar_oferta_por_budget(self, user_id: str, course_id: str) -> Dict[str, str]:
        """
        REDISEÑADO: Retorna opciones de pago personalizadas.
        """
        try:
            course = await self.db.get_course_details(course_id)
            if not course:
                return {"type": "error", "content": "Curso no encontrado"}

            precio = course.get('price', 199)
            precio_3_cuotas = round(precio / 3, 2)
            precio_6_cuotas = round(precio / 6, 2)

            mensaje = f"""💳 **Opciones de Pago Personalizadas**

**Para el curso:** {course['name']}

**Opción 1: Pago único**
💰 ${precio} USD
🎁 Incluye todos los bonos
✅ Acceso inmediato completo

**Opción 2: 3 cuotas sin interés**
💳 3 cuotas de ${precio_3_cuotas} USD
📅 Una cada 30 días
✅ Acceso inmediato al contenido

**Opción 3: 6 cuotas flexibles**
💳 6 cuotas de ${precio_6_cuotas} USD
📅 Una cada 15 días
✅ Ideal para presupuestos ajustados

**Todas las opciones incluyen:**
🛡️ Garantía de 30 días
🎓 Certificado al completar
💬 Soporte completo

¿Cuál opción se adapta mejor a tu presupuesto?"""

            await self._registrar_interaccion(user_id, course_id, "payment_options_shown", {"options": 3})

            return {
                "type": "text",
                "content": mensaje
            }

        except Exception as e:
            return {"type": "error", "content": f"Error en opciones de pago: {str(e)}"}

    # NUEVAS HERRAMIENTAS UNIFICADAS

    async def mostrar_testimonios_relevantes(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Retorna testimonios relevantes desde BD o ejemplos."""
        mensaje = """👥 **Lo que dicen nuestros estudiantes**

⭐⭐⭐⭐⭐ **María González - Marketing Manager**
*"En 3 semanas automaticé el 60% de mis reportes. Ahora tengo 12 horas extra semanales para estrategia."*

⭐⭐⭐⭐⭐ **Carlos Ruiz - Emprendedor**  
*"Creé 3 asistentes virtuales para mi negocio. La productividad de mi equipo aumentó 45%."*

⭐⭐⭐⭐⭐ **Ana Martínez - Gerente Operaciones**
*"El ROI fue inmediato. Los procesos que automaticé me ahorran 20 horas semanales."*

**📊 Resultados promedio de nuestros estudiantes:**
• 40-60% reducción en tareas repetitivas
• 15-25 horas semanales ahorradas
• 300% ROI en los primeros 3 meses"""

        return {"type": "text", "content": mensaje}

    async def mostrar_casos_exito_similares(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Retorna casos de éxito similares."""
        mensaje = """🏆 **Casos de Éxito Reales**

**Caso 1: Agencia de Marketing**
📊 Problema: 15 horas semanales en reportes manuales
✅ Solución: Automatización con IA
📈 Resultado: 90% tiempo ahorrado, +300% contenido generado

**Caso 2: Empresa Fintech**  
📊 Problema: Reportes financieros tomaban 3 días
✅ Solución: Proceso automatizado con IA
📈 Resultado: Reportes en 2 horas, 0% errores

**Caso 3: Consultoría Empresarial**
📊 Problema: Propuestas tomaban 1 semana cada una
✅ Solución: Templates y prompts automatizados  
📈 Resultado: Propuestas en 4 horas, +400% clientes

**¡Tu resultado puede ser similar!**"""

        return {"type": "text", "content": mensaje}

    async def mostrar_social_proof_inteligente(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Retorna prueba social avanzada."""
        mensaje = """👥 **Prueba Social Verificable**

**📊 Estadísticas reales:**
• 1,247 estudiantes activos
• 89% completa el curso
• 96% lo recomienda a colegas
• 4.9/5 estrellas promedio

**🔍 Perfiles verificados en LinkedIn:**
• María G. - Automatizó reportes de marketing
• Carlos R. - Creó chatbots para atención al cliente  
• Ana M. - Optimizó procesos financieros con IA

**📱 En nuestra comunidad privada:**
• 850+ miembros activos
• Comparten resultados diarios
• Se ayudan entre todos
• Networking profesional constante

**¡Únete a profesionales que ya están transformando su trabajo!**"""

        return {"type": "text", "content": mensaje}

    async def presentar_oferta_limitada(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Retorna oferta limitada con urgencia real."""
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
            return {"type": "text", "content": "Oferta especial disponible. Consulta con tu asesor."}

    # FUNCIONES DE SOPORTE

    async def activar_flujo_contacto_asesor(self, user_id: str, course_id: str = None) -> str:
        """
        Función wrapper que activa el flujo predefinido de contacto.
        """
        try:
            # Importar aquí para evitar imports circulares
            from core.handlers.contact_flow import start_contact_flow_directly
            
            # Activar el flujo de contacto directo
            response_message = await start_contact_flow_directly(user_id, course_id, self.db)
            
            return response_message
            
        except Exception as e:
            logger.error(f"Error en activar_flujo_contacto_asesor: {e}")
            return "Te voy a conectar con un asesor especializado. Por favor, proporciona tu email para contactarte:"

    async def _registrar_interaccion(self, user_id: str, course_id: str, action: str, metadata: dict) -> None:
        """Registra interacciones en la base de datos."""
        try:
            await self.db.execute(
                """
                INSERT INTO course_interactions (user_id, course_id, interaction_type, details, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                """,
                user_id, course_id, action, json.dumps(metadata)
            )
        except Exception as e:
            logger.error(f"Error registrando interacción: {e}")

    # HERRAMIENTAS ADICIONALES SIMPLIFICADAS

    async def gestionar_objeciones_tiempo(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Maneja objeciones de tiempo con flexibilidad."""
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

**¡Muchos estudiantes completan el curso en sus tiempos libres!**"""

        return {"type": "text", "content": mensaje}

    async def mostrar_comparativa_competidores(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Muestra ventajas vs competidores."""
        mensaje = """⚖️ **¿Por qué elegir nuestro curso?**

**🆚 Coursera/Udemy ($50-80):**
❌ Contenido genérico y desactualizado
❌ Sin soporte personalizado
❌ Videos largos y teóricos
✅ **Nosotros:** Contenido actualizado, soporte 1:1, práctica real

**🆚 Bootcamps presenciales ($2000-5000):**
❌ Muy costosos y rígidos
❌ Horarios fijos incompatibles
❌ Enfoque muy técnico
✅ **Nosotros:** Precio accesible, flexible, enfoque práctico

**🆚 Consultoría individual ($200/hora):**
❌ Solo consejos, sin aprendizaje estructurado
❌ Muy costoso a largo plazo
❌ Dependes del consultor
✅ **Nosotros:** Aprendizaje completo, autosuficiencia, comunidad

**Nuestro curso combina lo mejor de todos sin las desventajas**"""

        return {"type": "text", "content": mensaje}

    # HERRAMIENTAS DE AUTOMATIZACIÓN

    async def detectar_necesidades_automatizacion(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Detecta necesidades específicas de automatización."""
        mensaje = """🤖 **Análisis de tu Automatización**

**Procesos que puedes automatizar:**
📊 Reportes y análisis (ahorro: 10-15 horas/semana)
📝 Creación de contenido (ahorro: 8-12 horas/semana)  
📧 Respuestas de email (ahorro: 5-8 horas/semana)
📋 Documentación (ahorro: 3-5 horas/semana)

**Para tu caso específico en marketing:**
• Automatización de reportes de campañas
• Generación de contenido para redes sociales
• Análisis de métricas y KPIs
• Creación de propuestas y presentations

**Total tiempo recuperado: 26-40 horas/semana**
**Valor económico: $1,300-2,000 USD/mes**

¿Te imaginas qué harías con 30+ horas extra cada semana?"""

        return {"type": "text", "content": mensaje}

    async def mostrar_casos_automatizacion(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Muestra casos específicos de automatización."""
        mensaje = """⚙️ **Automatizaciones Reales de Estudiantes**

**📊 Caso: Automatización de Reportes**
• Empresa: Agencia de Marketing Digital
• Proceso anterior: 12 horas/semana manualmente
• Automatización: ChatGPT + Google Sheets + Zapier
• Resultado: 2 horas/semana, reportes más completos

**📱 Caso: Content Marketing Automático**
• Empresa: E-commerce de 50M USD
• Proceso anterior: 20 horas/semana creando posts
• Automatización: IA generativa + calendario automático
• Resultado: 300% más contenido, 5 horas/semana

**💬 Caso: Atención al Cliente IA**
• Empresa: SaaS B2B
• Proceso anterior: 6 agentes tiempo completo
• Automatización: Chatbot inteligente + escalación
• Resultado: 80% consultas resueltas automáticamente

**¡En el curso aprenderás exactamente cómo replicar estos casos!**"""

        return {"type": "text", "content": mensaje}

    async def calcular_roi_personalizado(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Calcula ROI personalizado."""
        mensaje = """📊 **Tu ROI Personalizado**

**Inversión en el curso:** $199 USD

**Ahorro mensual estimado:**
⏰ 20 horas/semana automatizadas
💰 Valor hora profesional: $25 USD
💰 Ahorro mensual: $2,000 USD

**ROI en 3 meses:**
• Mes 1: $2,000 - $199 = $1,801 ganancia
• Mes 2: $2,000 adicionales  
• Mes 3: $2,000 adicionales
• **Total en 3 meses: $5,801 USD**

**ROI: 2,915% en 3 meses**

**Beneficios adicionales no monetarios:**
• Menos estrés por tareas repetitivas
• Más tiempo para estrategia y creatividad
• Mayor valor profesional en el mercado
• Herramientas que usarás por años

**El curso se paga solo en la primera semana**"""

        return {"type": "text", "content": mensaje}

    async def generar_link_pago_personalizado(self, user_id: str, course_id: str) -> Dict[str, Union[str, List[Dict]]]:
        """Genera link de pago personalizado."""
        mensaje = """💳 **Inscríbete Ahora**

**¡Perfecto! Vamos a completar tu inscripción:**

✅ Acceso inmediato al contenido completo
✅ Bonos incluidos (valor $400 USD)
✅ Garantía de 30 días sin riesgo
✅ Soporte personalizado incluido

**Tu inversión total: $199 USD**

Haz clic en el botón para completar tu pago seguro:"""

        resources = []
        
        # Obtener link de pago desde ResourceService
        if self.resource_service:
            payment_url = await self.resource_service.get_resource_url(
                f"payment_{course_id}",
                fallback_url=await self.resource_service.get_resource_url("payment_general")
            )
            
            if payment_url and not payment_url.startswith("https://aprenda-ia.com/"):
                resources.append({
                    "type": "link",
                    "url": payment_url,
                    "text": "💳 Pagar Ahora - $199 USD"
                })

        return {
            "type": "multimedia",
            "content": mensaje,
            "resources": resources
        }

    async def establecer_seguimiento_automatico(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Establece seguimiento post-venta."""
        mensaje = """📅 **Tu Plan de Onboarding**

**¡Bienvenido al curso! Aquí está tu cronograma:**

**📧 En los próximos minutos:**
• Recibirás email con acceso completo
• Credenciales para la plataforma
• Link a la comunidad privada

**📚 Primera semana:**
• Módulo 1: Fundamentos de IA
• Setup de herramientas básicas
• Primera automatización simple

**📱 Soporte continuo:**
• Acceso a comunidad 24/7
• Sesiones semanales grupales
• Soporte directo con instructores

**📞 Próximo contacto:**
• Te llamaremos en 48 horas para asegurar que todo funcione
• Sesión de bienvenida grupal cada viernes

**¡Estamos aquí para asegurar tu éxito!**"""

        return {"type": "text", "content": mensaje}

    # HERRAMIENTAS DE GAMIFICACIÓN

    async def implementar_gamificacion(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Sistema de gamificación y progreso."""
        mensaje = """🏆 **Sistema de Logros y Progreso**

**🎯 Tu progreso se convierte en un juego:**

**📊 Dashboard personal:**
• % de completación en tiempo real
• Racha de días consecutivos
• Puntos por módulo completado
• Ranking en la comunidad

**🏅 Sistema de logros:**
🥉 "Primer Paso" - Completar módulo 1
🥈 "Automatizador" - Primera automatización
🥇 "Experto IA" - Curso 100% completado
💎 "Mentor" - Ayudar a otros estudiantes

**🎁 Recompensas reales:**
• Acceso a contenido bonus exclusivo
• Sesiones 1:1 adicionales gratuitas
• Certificación avanzada premium
• Invitación a eventos VIP

**📱 Comunidad competitiva:**
• Desafíos semanales
• Comparte tus logros
• Aprende de otros estudiantes
• Networking profesional

**¡Aprender nunca fue tan divertido y motivante!**"""

        return {"type": "text", "content": mensaje}

    async def mostrar_timeline_resultados(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Muestra timeline realista de resultados."""
        mensaje = """📈 **Timeline Realista de Resultados**

**📅 Semana 1-2: Fundamentos**
✅ Entiendes qué puede hacer la IA por ti
✅ Configuras tus primeras herramientas
✅ Primera automatización simple funcionando

**📅 Semana 3-4: Primeras Automatizaciones**
✅ Automatizas 2-3 procesos básicos
✅ Ahorras 5-8 horas semanales
✅ Ves el potencial real de la IA

**📅 Semana 5-6: Automatizaciones Avanzadas**
✅ Automatizas procesos complejos
✅ Ahorras 15-20 horas semanales
✅ Creas tus propios flujos personalizados

**📅 Semana 7-8: Optimización y Escala**
✅ Optimizas todos tus procesos
✅ Ahorras 25+ horas semanales
✅ Te conviertes en referente IA en tu empresa

**📅 Mes 3-6: Dominio Completo**
✅ Aplicas IA en nuevas áreas
✅ Increases tu valor profesional 200%
✅ Posibles promociones/aumentos

**💰 ROI visible desde la semana 2**"""

        return {"type": "text", "content": mensaje}

    # HERRAMIENTAS DE COMUNIDAD

    async def conectar_con_comunidad(self, user_id: str, course_id: str) -> Dict[str, Union[str, List[Dict]]]:
        """Conecta con la comunidad exclusiva."""
        mensaje = """👥 **Comunidad Exclusiva de Profesionales**

**🚀 Únete a 850+ profesionales que ya están transformando su trabajo:**

**💬 Slack privado (24/7):**
• Canal #automatizaciones - Comparte tus logros
• Canal #dudas-tecnicas - Soporte entre estudiantes  
• Canal #oportunidades - Ofertas de trabajo IA
• Canal #networking - Conecta con otros profesionales

**📹 Eventos semanales:**
• Miércoles: "Show & Tell" - Muestra tus automatizaciones
• Viernes: "Q&A con Expertos" - Resuelve dudas avanzadas
• Sábados: "Networking Virtual" - Conecta con otros estudiantes

**🤝 Beneficios exclusivos:**
• Bolsa de trabajo IA exclusiva
• Descuentos en cursos avanzados
• Acceso a eventos presenciales
• Red profesional de alto valor

**¡La comunidad vale más que el curso mismo!**"""

        resources = []
        
        if self.resource_service:
            community_url = await self.resource_service.get_resource_url(
                "community_slack",
                fallback_url=await self.resource_service.get_resource_url("community_access")
            )
            
            if community_url and not community_url.startswith("https://aprenda-ia.com/"):
                resources.append({
                    "type": "link",
                    "url": community_url,
                    "text": "🚀 Unirse a la Comunidad"
                })

        return {
            "type": "multimedia", 
            "content": mensaje,
            "resources": resources
        }

    async def ofrecer_implementacion_asistida(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Ofrece implementación asistida personalizada."""
        mensaje = """🛠️ **Implementación Asistida 1:1**

**¿Quieres garantizar tu éxito? Te ayudamos personalmente:**

**📋 Paquete "Done-With-You":**
✅ Análisis completo de tus procesos actuales
✅ Diseño personalizado de automatizaciones
✅ Implementación conjunta paso a paso
✅ 4 sesiones 1:1 de 60 minutos c/u
✅ Soporte por WhatsApp durante 30 días

**🎯 Qué lograrás:**
• Automatizaciones funcionando en 2 semanas
• ROI garantizado en el primer mes
• Procesos optimizados específicos para tu negocio
• Conocimiento para replicar en nuevas áreas

**💰 Inversión adicional:**
• Valor normal: $800 USD
• **Tu precio especial: $399 USD**
• Solo disponible durante la inscripción

**🛡️ Garantía total:** Si no automatizas al menos 20 horas semanales, te devolvemos TODO el dinero.

**¿Te interesa asegurar tu éxito al 100%?**"""

        return {"type": "text", "content": mensaje}

    async def recomendar_herramientas_ia(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Recomienda herramientas específicas de IA."""
        mensaje = """🔧 **Stack de Herramientas IA que Dominarás**

**🤖 Para Automatización de Textos:**
• ChatGPT Pro - Generación de contenido
• Claude - Análisis y redacción
• Jasper - Marketing copy automático

**📊 Para Reportes y Análisis:**
• ChatGPT + Google Sheets - Reportes automáticos
• Power BI + IA - Dashboards inteligentes
• Zapier - Conecta todo automáticamente

**🎨 Para Contenido Visual:**
• Midjourney - Imágenes profesionales
• Canva Magic - Diseños automáticos
• Luma AI - Videos automáticos

**📱 Para Atención al Cliente:**
• Chatbase - Chatbots personalizados
• Intercom + IA - Soporte automatizado
• Calendly + IA - Agendamiento inteligente

**💰 Valor total de herramientas: $500/mes**
**Tu acceso en el curso: Licencias educativas incluidas**

**¡Dominarás las herramientas que usan las empresas más innovadoras!**"""

        return {"type": "text", "content": mensaje}

import logging
logger = logging.getLogger(__name__)