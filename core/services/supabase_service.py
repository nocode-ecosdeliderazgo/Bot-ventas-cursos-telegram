# ==============================
# SERVICIOS Y LÓGICA DE NEGOCIO EXTERNA
# ==============================
# Este módulo contiene la integración con Supabase, OpenAI, notificaciones y helpers de negocio.

import requests
import json
import logging
import time
from typing import Optional, Dict, Any, List
from config.settings import settings
from .memory import LeadMemory
logger = logging.getLogger(__name__)

# === Configuración global de endpoints y emails ===
SUPABASE_URL = settings.SUPABASE_URL
ADVISOR_EMAIL = settings.ADVISOR_EMAIL
UMBRAL_PROMO = 20  # Umbral de interés mínimo para mostrar promociones

# === Sistema de caché simple para consultas externas ===
class Cache:
    """Caché simple en memoria con TTL configurable."""
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = ttl_seconds
    def get(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
            else:
                del self.cache[key]
        return None
    def set(self, key, value):
        self.cache[key] = (value, time.time())
    def clear_expired(self):
        current_time = time.time()
        expired_keys = [k for k, (_, t) in self.cache.items() if current_time - t > self.ttl]
        for k in expired_keys:
            del self.cache[k]

cache = Cache()

# === Decorador para manejo de errores en Supabase ===
def handle_supabase_errors(func):
    """Maneja errores de Supabase y los registra en el log."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión Supabase en {func.__name__}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado en {func.__name__}: {e}")
            return None
    return wrapper

# === Request robusto a OpenAI con reintentos ===
def openai_request_with_retry(url, headers, payload, max_retries=3):
    """Hace request a OpenAI con reintentos y manejo de rate limit."""
    for attempt in range(max_retries):
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            if r.status_code == 429:
                wait_time = 60 * (attempt + 1)
                time.sleep(wait_time)
                continue
            elif r.status_code == 200:
                return r
            else:
                r.raise_for_status()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise Exception("Máximo número de reintentos alcanzado")

@handle_supabase_errors
def supabase_query(table, filters=None, limit=None):
    """Simple REST GET to Supabase table with caching."""
    cache_key = f"supabase_{table}_{hash(str(filters))}_{limit}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.debug(f"Cache hit para {table}")
        return cached_result
    
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {"apikey": settings.SUPABASE_KEY, "Authorization": f"Bearer {settings.SUPABASE_KEY}"}
    params = {"select": "*"}
    if filters:
        params.update(filters)
    if limit:
        params["limit"] = limit
    
    logger.debug(f"Consultando Supabase: {table}")
    r = requests.get(url, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    result = r.json()
    
    # Cache solo resultados exitosos
    cache.set(cache_key, result)
    return result

def get_interest_score(user_id: str) -> Optional[int]:
    """Obtiene el interest score actual del usuario desde Supabase."""
    try:
        url_score = f"{SUPABASE_URL}/rest/v1/interest_score?user_id=eq.{user_id}"
        headers_score = {
            "apikey": settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_KEY}"
        }
        r_score = requests.get(url_score, headers=headers_score, timeout=10)
        if r_score.status_code == 200 and r_score.json():
            return r_score.json()[0].get("score", 0)
    except Exception as e:
        logger.warning(f"No se pudo obtener interest_score: {e}")
    return None

@handle_supabase_errors
def save_lead(lead_memory: LeadMemory):
    """Insert or update user lead with better error handling."""
    if not lead_memory.user_id or not lead_memory.email:
        logger.warning(f"Intento de guardar lead sin user_id o email: {lead_memory.user_id}")
        return False
    
    url = f"{SUPABASE_URL}/rest/v1/user_leads"
    headers = {
        "apikey": settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    # El id es el user_id de Telegram (string)
    data = {
        "id": str(lead_memory.user_id),
        "email": lead_memory.email,
        "stage": lead_memory.stage
    }
    if lead_memory.phone:
        data["phone"] = lead_memory.phone
    if lead_memory.selected_course:
        data["selected_course"] = lead_memory.selected_course
    if lead_memory.name:
        data["name"] = lead_memory.name
    if lead_memory.role:
        data["role"] = lead_memory.role
    if lead_memory.interests:
        data["interests"] = ", ".join(lead_memory.interests)
    
    try:
        logger.debug(f"Intentando guardar lead: {data}")
        r = requests.post(url, headers=headers, data=json.dumps(data), timeout=15)
        
        if r.status_code == 409:
            # Already exists, so PATCH
            patch_url = f"{url}?id=eq.{lead_memory.user_id}"
            r = requests.patch(patch_url, headers=headers, data=json.dumps(data), timeout=15)
        
        if r.status_code == 200 or r.status_code == 201:
            logger.info(f"Lead guardado exitosamente para usuario {lead_memory.user_id}")
            return True
        else:
            logger.error(f"Error HTTP guardando lead {lead_memory.user_id}: Status {r.status_code} - Response: {r.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error inesperado guardando lead {lead_memory.user_id}: {e}")
        return False

def get_courses(category=None):
    """Get courses with caching and error handling."""
    try:
        filters = {}
        if category:
            filters["category"] = f"eq.{category}"
        courses = supabase_query("courses", filters)
        if courses is None:
            logger.warning("No se pudieron obtener cursos de Supabase")
            return []
        # Only published
        published_courses = [c for c in courses if c.get("published")]
        logger.info(f"Obtenidos {len(published_courses)} cursos publicados")
        return published_courses
    except Exception as e:
        logger.error(f"Error obteniendo cursos: {e}")
        return []

def get_course_detail(course_id):
    """Get course detail with caching."""
    if not course_id:
        return None
    
    cache_key = f"course_detail_{course_id}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    try:
        filters = {"id": f"eq.{course_id}"}
        res = supabase_query("courses", filters)
        if res and len(res) > 0:
            cache.set(cache_key, res[0])
            return res[0]
        return None
    except Exception as e:
        logger.error(f"Error obteniendo detalle del curso {course_id}: {e}")
        return None

def get_modules(course_id):
    """Get modules with caching."""
    if not course_id:
        return []
    
    cache_key = f"modules_{course_id}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    try:
        filters = {"course_id": f"eq.{course_id}"}
        modules = supabase_query("course_modules", filters)
        if modules:
            cache.set(cache_key, modules)
        return modules or []
    except Exception as e:
        logger.error(f"Error obteniendo módulos del curso {course_id}: {e}")
        return []

def get_course_by_name(course_name: str):
    """Get course by name with fuzzy matching."""
    if not course_name:
        return None
    
    try:
        courses = get_courses()
        course_name_lower = course_name.lower()
        
        # Exact match first
        for course in courses:
            if course['name'].lower() == course_name_lower:
                return course
        
        # Partial match
        for course in courses:
            if course_name_lower in course['name'].lower():
                return course
        
        return None
    except Exception as e:
        logger.error(f"Error buscando curso por nombre '{course_name}': {e}")
        return None

def get_promotions():
    """Get active promotions with caching."""
    cache_key = "active_promotions"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    try:
        filters = {"active": "eq.TRUE"}
        promotions = supabase_query("promotions", filters)
        if promotions:
            cache.set(cache_key, promotions)
        return promotions or []
    except Exception as e:
        logger.error(f"Error obteniendo promociones: {e}")
        return []

# ==============================
# SISTEMA DE NOTIFICACIÓN PARA ASESORES
# ==============================
def send_advisor_notification(subject: str, message: str, user_data: Optional[dict] = None):
    """Envía notificación por email al asesor."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = settings.smtp_username
        msg['To'] = ADVISOR_EMAIL
        msg['Subject'] = f"[BOT TELEGRAM] {subject}"
        
        # Construir cuerpo del mensaje
        body = f"""
        <html>
        <body>
        <h2>Notificación del Bot de Telegram</h2>
        <p><strong>Asunto:</strong> {subject}</p>
        <p><strong>Mensaje:</strong></p>
        <p>{message}</p>
        """
        
        if user_data:
            body += f"""
            <h3>Datos del Usuario:</h3>
            <ul>
                <li><strong>ID:</strong> {user_data.get('user_id', 'N/A')}</li>
                <li><strong>Nombre:</strong> {user_data.get('name', 'N/A')}</li>
                <li><strong>Email:</strong> {user_data.get('email', 'N/A')}</li>
                <li><strong>Teléfono:</strong> {user_data.get('phone', 'N/A')}</li>
                <li><strong>Curso seleccionado:</strong> {user_data.get('selected_course', 'N/A')}</li>
                <li><strong>Etapa:</strong> {user_data.get('stage', 'N/A')}</li>
            </ul>
            """
        
        body += """
        <p><em>Este mensaje fue generado automáticamente por el bot de Telegram.</em></p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Enviar email
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        text = msg.as_string()
        server.sendmail(settings.smtp_username, ADVISOR_EMAIL, text)
        server.quit()
        
        logger.info(f"Notificación enviada al asesor: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando notificación al asesor: {e}")
        return False

def notify_advisor_contact_request(user_data: dict):
    """Notifica al asesor cuando un usuario solicita contacto."""
    subject = "Solicitud de Contacto - Usuario Interesado"
    message = f"""
    Un usuario ha solicitado que un asesor se ponga en contacto con él/ella.
    
    El usuario mostró interés en los cursos de IA y quiere recibir atención personalizada.
    """
    
    return send_advisor_notification(subject, message, user_data)

def notify_advisor_reservation_request(user_data: dict):
    """Notifica al asesor cuando un usuario quiere reservar su lugar."""
    subject = "Solicitud de Reserva - Usuario Interesado"
    message = f"""
    Un usuario quiere reservar su lugar en el curso.
    
    El usuario está listo para proceder con la inscripción y necesita asistencia.
    """
    
    return send_advisor_notification(subject, message, user_data)

def notify_advisor_lead_qualified(user_data: dict):
    """Notifica al asesor cuando se califica un lead."""
    subject = "Lead Calificado - Nuevo Prospecto"
    message = f"""
    Se ha calificado un nuevo lead con alto potencial de conversión.
    
    El usuario ha mostrado interés activo y está en etapa de decisión.
    """
    
    return send_advisor_notification(subject, message, user_data)



# ==============================
# UTILS: OPENAI API (LLM decision helper)
# ==============================

def openai_intent_and_response(user_input: str, context: str) -> dict:
    """
    Llama a OpenAI para obtener en una sola llamada:
    - La intención del usuario
    - El nombre del curso (si aplica)
    - La respuesta persuasiva y contextual
    Devuelve un dict: {"intent": ..., "course_name": ..., "response": ...}
    """
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json"
        }
        system_prompt = (
            "Eres un asistente de ventas de cursos de Inteligencia Artificial experto en copywriting persuasivo. "
            "Dado el mensaje del usuario y el contexto, responde SOLO con un JSON con los siguientes campos: "
            "'intent', 'course_name' (si aplica), y 'response' (respuesta persuasiva y contextual). "
            "Las intenciones posibles son: 'GREETING', 'LIST_COURSES', 'GET_COURSE_INFO', 'ASK_PRICE', 'ASK_MODULES', 'ASK_DURATION', 'ASK_ENROLLMENT', 'ASK_PROMOTIONS', 'BUY_COURSE', 'EXIT', 'OUT_OF_DOMAIN', 'UNKNOWN'. "
            "La respuesta debe ser natural, entusiasta, conversacional y persuasiva, usando solo la información del contexto. "
            "NO inventes datos. Si no tienes la información, sé honesto y ofrece ayuda adicional. "
            "Siempre termina con una pregunta o sugerencia que invite a la acción. "
            "Ejemplo de respuesta: {\"intent\": \"ASK_PRICE\", \"course_name\": \"Curso de IA para Marketing\", \"response\": \"El precio es... ¿Te gustaría inscribirte ahora?\"}"
        )
        user_prompt = f"CONTEXT:\n{context}\n\nMENSAJE DEL USUARIO:\n{user_input}\n\nJSON:"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        payload = {
            "model": "gpt-4",
            "messages": messages,
            "max_tokens": 900,
            "temperature": 0.7,
        }
        logger.debug(f"Llamando a OpenAI para intención y respuesta: '{user_input[:50]}...'")
        
        # Usar la función robusta con retry
        r = openai_request_with_retry(url, headers, payload)
        
        # Validar respuesta
        if not r or r.status_code != 200:
            logger.error(f"Error en respuesta de OpenAI: status_code={getattr(r, 'status_code', 'N/A')}")
            return {
                "intent": "UNKNOWN", 
                "course_name": None, 
                "response": "Lo siento, hubo un problema técnico al procesar tu mensaje. ¿Te gustaría que un asesor humano te contacte?"
            }
        
        # Parsear respuesta JSON
        try:
            response_data = r.json()
            if not response_data or "choices" not in response_data or not response_data["choices"]:
                logger.error("Respuesta de OpenAI sin choices válidos")
                return {
                    "intent": "UNKNOWN", 
                    "course_name": None, 
                    "response": "Lo siento, hubo un problema técnico. ¿Te gustaría que un asesor humano te contacte?"
                }
            
            content = response_data["choices"][0]["message"]["content"].strip()
            if not content:
                logger.warning("Respuesta de OpenAI vacía")
                return {
                    "intent": "UNKNOWN", 
                    "course_name": None, 
                    "response": "Lo siento, no pude generar una respuesta. ¿Te gustaría que un asesor humano te contacte?"
                }
            
            # Parsear JSON de la respuesta
            import json as _json
            try:
                result = _json.loads(content)
                logger.debug(f"Respuesta OpenAI JSON: {result}")
                
                # Validar estructura del resultado
                if not isinstance(result, dict):
                    logger.warning(f"Respuesta de OpenAI no es un diccionario: {type(result)}")
                    return {
                        "intent": "UNKNOWN", 
                        "course_name": None, 
                        "response": content if isinstance(content, str) else "Lo siento, hubo un problema técnico. ¿Te gustaría que un asesor humano te contacte?"
                    }
                
                # Asegurar que tenga los campos requeridos
                result.setdefault("intent", "UNKNOWN")
                result.setdefault("course_name", None)
                result.setdefault("response", "Lo siento, no pude generar una respuesta. ¿Te gustaría que un asesor humano te contacte?")
                
                return result
                
            except _json.JSONDecodeError as e:
                logger.warning(f"Error parseando JSON de OpenAI: {e} - Content: {content}")
                # Si no es JSON válido, usar el contenido como respuesta
                return {
                    "intent": "UNKNOWN", 
                    "course_name": None, 
                    "response": content if isinstance(content, str) else "Lo siento, hubo un problema técnico. ¿Te gustaría que un asesor humano te contacte?"
                }
                
        except Exception as e:
            logger.error(f"Error parseando respuesta de OpenAI: {e}", exc_info=True)
            return {
                "intent": "UNKNOWN", 
                "course_name": None, 
                "response": "Lo siento, hubo un problema técnico al procesar la respuesta. ¿Te gustaría que un asesor humano te contacte?"
            }
            
    except Exception as e:
        logger.error(f"Error inesperado en openai_intent_and_response: {e}", exc_info=True)
        return {
            "intent": "UNKNOWN", 
            "course_name": None, 
            "response": "Lo siento, hubo un problema técnico. ¿Te gustaría que un asesor humano te contacte o prefieres intentar de nuevo?"
        }
