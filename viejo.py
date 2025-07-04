# -*- coding: utf-8 -*-
import requests
import uuid
import sys
import time
import json
import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, PollAnswerHandler
import asyncio
import nest_asyncio
from functools import wraps
import httpx
import threading
nest_asyncio.apply()

# ==============================
# CURSOS MAP (CÓDIGO → ID SUPABASE)
# ==============================
CURSOS_MAP = {
    "CURSO_IA_CHATGPT": "a392bf83-4908-4807-89a9-95d0acc807c9"
}

# ==============================
# RATE LIMITING FOR OPENAI
# ==============================
class RateLimiter:
    def __init__(self, max_requests_per_minute=60):
        self.max_requests = max_requests_per_minute
        self.requests = []
    
    def can_make_request(self):
        now = time.time()
        # Limpiar requests antiguos (más de 1 minuto)
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        return len(self.requests) < self.max_requests
    
    def record_request(self):
        self.requests.append(time.time())
    
    def wait_if_needed(self):
        if not self.can_make_request():
            wait_time = 60 - (time.time() - self.requests[0])
            if wait_time > 0:
                logger.warning(f"Rate limit alcanzado, esperando {wait_time:.1f} segundos")
                time.sleep(wait_time)

# Global rate limiter
openai_rate_limiter = RateLimiter(max_requests_per_minute=20)  # Más conservador para evitar 429

# ==============================
# COLA ASÍNCRONA GLOBAL PARA OPENAI
# ==============================
openai_queue = None
openai_queue_worker_task = None
openai_queue_lock = threading.Lock()
OPENAI_MAX_REQUESTS_PER_MINUTE = 15  # Ajusta según tu límite real
OPENAI_MIN_INTERVAL = 60 / OPENAI_MAX_REQUESTS_PER_MINUTE

class OpenAIRequest:
    def __init__(self, url, headers, payload, future):
        self.url = url
        self.headers = headers
        self.payload = payload
        self.future = future

# Reemplazar el acceso directo a openai_queue por get_openai_queue()
def get_openai_queue():
    global openai_queue, openai_queue_worker_task, openai_queue_lock
    with openai_queue_lock:
        if openai_queue is None:
            openai_queue = asyncio.Queue()
            loop = asyncio.get_event_loop()
            openai_queue_worker_task = loop.create_task(openai_queue_worker())
    return openai_queue

async def openai_queue_worker():
    while True:
        queue = get_openai_queue()
        req = await queue.get()
        try:
            # Esperar el intervalo mínimo entre requests
            await asyncio.sleep(OPENAI_MIN_INTERVAL)
            loop = asyncio.get_event_loop()
            # Ejecutar la request en un hilo para no bloquear
            def do_request():
                try:
                    r = requests.post(req.url, headers=req.headers, data=json.dumps(req.payload), timeout=30)
                    return r
                except Exception as e:
                    return e
            r = await loop.run_in_executor(None, do_request)
            req.future.set_result(r)
        except Exception as e:
            req.future.set_result(e)
        finally:
            queue.task_done()

async def openai_request_async(url, headers, payload):
    queue = get_openai_queue()
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    req = OpenAIRequest(url, headers, payload, future)
    await queue.put(req)
    r = await future
    if isinstance(r, Exception):
        raise r
    return r

def openai_request_with_retry(url, headers, payload, max_retries=3):
    """Hace request a OpenAI con retry y rate limiting usando la cola asíncrona"""
    # Si estamos en un hilo de asyncio, usar la cola
    try:
        loop = asyncio.get_running_loop()
        # Si hay un loop, usar la versión async
        async def _do():
            for attempt in range(max_retries):
                try:
                    r = await openai_request_async(url, headers, payload)
                    if r.status_code == 429:
                        wait_time = 60 * (attempt + 1)
                        await asyncio.sleep(wait_time)
                        continue
                    elif r.status_code == 200:
                        return r
                    else:
                        r.raise_for_status()
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
            raise Exception("Máximo número de reintentos alcanzado")
        return loop.run_until_complete(_do())
    except RuntimeError:
        # No hay loop, usar la versión sync (para compatibilidad)
        for attempt in range(max_retries):
            try:
                # Espaciar manualmente
                time.sleep(OPENAI_MIN_INTERVAL)
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

# ==============================
# LOGGING CONFIGURATION
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==============================
# CONFIG
# ==============================
SUPABASE_URL = "https://dzlvezeeuuarjnoheoyq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR6bHZlemVldXVhcmpub2hlb3lxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk4NzQ4MDMsImV4cCI6MjA2NTQ1MDgwM30.J4U_W1nDVGHXLTPa9GKqIBBoej6TvrRwF4q7vzwVymc"
OPENAI_API_KEY = "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"
MEMORY_FILE = "memory.json"
TELEGRAM_API_TOKEN = "8159423249:AAE_ezICc_EjrgOIxABQJq0gdGx7U0TizFk" # Tu API Token de Telegram

# Configuración para notificaciones de asesores
ADVISOR_EMAIL = "nocode@ecosdeliderazgo.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "safurldefender@gmail.com"
SMTP_PASSWORD = "ixiw tqxx qhnc roxc"  # Contraseña de aplicación

UMBRAL_PROMO = 20

# ==============================
# CACHE SYSTEM
# ==============================
class Cache:
    def __init__(self, ttl_seconds=300):  # 5 minutes default
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

# Global cache instance
cache = Cache()

# ==============================
# ERROR HANDLING DECORATORS
# ==============================
def handle_telegram_errors(func):
    """Decorator para manejar errores de Telegram con reintentos"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except httpx.ReadError as e:
                logger.warning(f"Error de conexión Telegram (intento {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Error fatal de conexión Telegram después de {max_retries} intentos")
                    # Enviar mensaje de error al usuario
                    update = args[0] if args else None
                    if update and hasattr(update, 'message') and update.message:
                        try:
                            await update.message.reply_text("⚠️ Error de conexión. Por favor, intenta de nuevo en unos momentos.")
                        except Exception:
                            pass
                    raise
                await asyncio.sleep(1 * (attempt + 1))  # Backoff exponencial
            except Exception as e:
                logger.error(f"Error inesperado en {func.__name__}: {e}", exc_info=True)
                # Enviar mensaje de error al usuario
                update = args[0] if args else None
                if update and hasattr(update, 'message') and update.message:
                    try:
                        await update.message.reply_text("⚠️ Ocurrió un error inesperado. Por favor, intenta de nuevo más tarde.")
                    except Exception:
                        pass
                raise
    return wrapper

def handle_supabase_errors(func):
    """Decorator para manejar errores de Supabase"""
    @wraps(func)
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

# ==============================
# FUTURE INTEGRATIONS (just markers for now)
# ==============================
# DONE: Integrate with python-telegram-bot for Telegram interface
# TODO: Integrate with Stripe API for payments and mark purchase as "paid"
# TODO: Add LLM-powered personalized sales flows (already partially done below)
# TODO: Store conversations/user state in DB for multidevice/multi-session memory

# ==============================
# LEAD MEMORY (per user)
# ==============================
class LeadMemory:
    """Clase para almacenar datos del lead."""
    def __init__(self):
        self.user_id: str = ""
        self.name: str = ""
        self.email: str = ""
        self.phone: str = ""
        self.selected_course: Optional[str] = None
        self.interests: List[str] = []
        self.stage: str = "inicio"
        self.privacy_accepted: bool = False  # Nuevo atributo para privacidad
        self.courses_seen: set = set()
        self.escalation_pending: bool = False
        self.role: Optional[str] = None
        self.lead_score: int = 0
        self.awaiting_ack: bool = False
        self.last_ack_time: Optional[float] = None

class Memory:
    def __init__(self):
        self.lead_data: LeadMemory = LeadMemory()
        self.history: List[Dict[str, Any]] = []  # Stores {user_input, bot_reply, timestamp}
        self.last_presented_courses: List[Dict[str, Any]] = [] # Stores list of {id, name} of courses last presented
        self.last_activity: float = time.time()

    def load(self, user_id: str) -> bool:
        """Carga memoria específica para un usuario"""
        try:
            # Crear archivo específico por usuario
            user_memory_file = f"memory_{user_id}.json"
            
            with open(user_memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Verificar si los datos no son muy antiguos (más de 30 días)
            last_activity = data.get("last_activity", 0)
            if time.time() - last_activity > 30 * 24 * 3600:  # 30 días
                logger.info(f"Memoria de usuario {user_id} muy antigua, inicializando nueva")
                self.lead_data.user_id = user_id
                self.lead_data.stage = "inicio"
                return False
                
            if data.get("lead_data"):
                self.lead_data.user_id = data["lead_data"].get("user_id")
                self.lead_data.email = data["lead_data"].get("email")
                self.lead_data.phone = data["lead_data"].get("phone")
                self.lead_data.stage = data["lead_data"].get("stage", "inicio")
                self.lead_data.courses_seen = set(data["lead_data"].get("courses_seen", []))
                self.lead_data.selected_course = data["lead_data"].get("selected_course")
                self.lead_data.escalation_pending = data["lead_data"].get("escalation_pending", False)
                self.lead_data.name = data["lead_data"].get("name")
                self.lead_data.role = data["lead_data"].get("role")
                self.lead_data.interests = data["lead_data"].get("interests", [])
                self.lead_data.lead_score = data["lead_data"].get("lead_score", 0)
                self.lead_data.awaiting_ack = data["lead_data"].get("awaiting_ack", False)
                self.lead_data.last_ack_time = data["lead_data"].get("last_ack_time")
                self.lead_data.privacy_accepted = data["lead_data"].get("privacy_accepted", False)
                
            self.history = data.get("history", [])
            self.last_presented_courses = data.get("last_presented_courses", [])
            self.last_activity = data.get("last_activity", time.time())
            
            logger.info(f"Memoria cargada para usuario {user_id}")
            return True
            
        except FileNotFoundError:
            logger.info(f"Archivo de memoria no encontrado para usuario {user_id}, inicializando nueva")
            self.lead_data.user_id = user_id
            self.lead_data.stage = "inicio"
            return False
        except Exception as e:
            logger.error(f"Error cargando memoria para usuario {user_id}: {e}")
            self.lead_data.user_id = user_id
            self.lead_data.stage = "inicio"
            return False

    def save(self):
        """Guarda memoria específica para el usuario actual"""
        try:
            user_memory_file = f"memory_{self.lead_data.user_id}.json"
            self.last_activity = time.time()
            
            data = {
                "lead_data": {
                    "user_id": self.lead_data.user_id,
                    "email": self.lead_data.email,
                    "phone": self.lead_data.phone,
                    "stage": self.lead_data.stage,
                    "courses_seen": list(self.lead_data.courses_seen),
                    "selected_course": self.lead_data.selected_course,
                    "escalation_pending": self.lead_data.escalation_pending,
                    "name": self.lead_data.name,
                    "role": self.lead_data.role,
                    "interests": ", ".join(self.lead_data.interests),
                    "lead_score": self.lead_data.lead_score,
                    "awaiting_ack": self.lead_data.awaiting_ack,
                    "last_ack_time": self.lead_data.last_ack_time,
                    "privacy_accepted": self.lead_data.privacy_accepted
                },
                "history": self.history[-50:],  # Mantener solo los últimos 50 mensajes
                "last_presented_courses": self.last_presented_courses,
                "last_activity": self.last_activity
            }
            
            with open(user_memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
                
            logger.debug(f"Memoria guardada para usuario {self.lead_data.user_id}")
            
        except Exception as e:
            logger.error(f"Error guardando memoria para usuario {self.lead_data.user_id}: {e}")

    @staticmethod
    def cleanup_old_memories():
        """Limpia archivos de memoria antiguos"""
        try:
            current_time = time.time()
            memory_dir = os.path.dirname(os.path.abspath(__file__))
            
            for filename in os.listdir(memory_dir):
                if filename.startswith("memory_") and filename.endswith(".json"):
                    filepath = os.path.join(memory_dir, filename)
                    file_time = os.path.getmtime(filepath)
                    
                    # Eliminar archivos más antiguos de 30 días
                    if current_time - file_time > 30 * 24 * 3600:
                        os.remove(filepath)
                        logger.info(f"Archivo de memoria eliminado: {filename}")
                        
        except Exception as e:
            logger.error(f"Error limpiando memorias antiguas: {e}")

# ==============================
# UTILS: SUPABASE API
# ==============================
@handle_supabase_errors
def supabase_query(table, filters=None, limit=None):
    """Simple REST GET to Supabase table with caching."""
    cache_key = f"supabase_{table}_{hash(str(filters))}_{limit}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.debug(f"Cache hit para {table}")
        return cached_result
    
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
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

@handle_supabase_errors
def save_lead(lead_memory: LeadMemory):
    """Insert or update user lead with better error handling."""
    if not lead_memory.user_id or not lead_memory.email:
        logger.warning(f"Intento de guardar lead sin user_id o email: {lead_memory.user_id}")
        return False
    
    url = f"{SUPABASE_URL}/rest/v1/user_leads"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
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
# TELEGRAM INTERACTIVE BUTTONS
# ==============================
def create_main_keyboard():
    """Crea teclado principal con opciones básicas"""
    keyboard = [
        ["📚 Ver Cursos", "💰 Promociones"],
        ["❓ Preguntas Frecuentes", "📞 Contactar Asesor"],
        ["🔄 Reiniciar Conversación"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def create_course_keyboard(course_id: str):
    """Crea teclado específico para un curso"""
    keyboard = [
        [InlineKeyboardButton("💳 Comprar Ahora", callback_data=f"buy_{course_id}")],
        [InlineKeyboardButton("📋 Ver Módulos", callback_data=f"modules_{course_id}")],
        [InlineKeyboardButton("💰 Aplicar Promoción", callback_data=f"promo_{course_id}")],
        [InlineKeyboardButton("❓ Más Información", callback_data=f"info_{course_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_courses_list_keyboard(courses: List[Dict]):
    """Crea teclado con lista de cursos disponibles"""
    keyboard = []
    for i, course in enumerate(courses[:5]):  # Máximo 5 cursos
        keyboard.append([InlineKeyboardButton(
            f"{i+1}. {course['name']}", 
            callback_data=f"course_{course['id']}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def create_cta_keyboard(context_type="default", user_id=None):
    score = get_interest_score(user_id) if user_id is not None else None
    cta_buttons = get_cta_buttons(context_type)
    # Si el score es bajo, filtra los botones de promociones
    if score is None or score < UMBRAL_PROMO:
        cta_buttons = [b for b in cta_buttons if 'promo' not in b['callback_data'] and 'descuento' not in b['callback_data']]
    keyboard = []
    for button in cta_buttons:
        keyboard.append([InlineKeyboardButton(
            button["text"], 
            callback_data=button["callback_data"]
        )])
    return InlineKeyboardMarkup(keyboard) if keyboard else None

def create_contextual_cta_keyboard(context_type: str, user_id: Optional[str] = None) -> InlineKeyboardMarkup:
    """
    Crea teclado de CTAs según el contexto y el interés del usuario.
    
    Args:
        context_type: Tipo de contexto (privacy_pending, default, course_selected, etc.)
        user_id: ID del usuario para verificar interest_score
    """
    buttons = []
    if context_type == "privacy_pending":
        buttons = [
            [InlineKeyboardButton("✅ Acepto y continúo", callback_data="privacy_accept")],
            [InlineKeyboardButton("🔒 Ver Aviso Completo", callback_data="privacy_view")]
        ]
    elif context_type == "default":
        buttons = [
            [InlineKeyboardButton("📚 Ver Cursos", callback_data="cta_ver_cursos")],
            [InlineKeyboardButton("👨‍💼 Hablar con Asesor", callback_data="cta_asesor")],
            [InlineKeyboardButton("💰 Ver Promociones", callback_data="cta_promociones")]
        ]
    elif context_type == "course_selected":
        buttons = [
            [InlineKeyboardButton("💳 Comprar Curso", callback_data="cta_comprar_curso")],
            [InlineKeyboardButton("📋 Ver Módulos", callback_data="cta_ver_modulos")],
            [InlineKeyboardButton("🎯 Aplicar Descuento", callback_data="cta_descuento")]
        ]
    elif context_type == "pricing_inquiry":
        buttons = [
            [InlineKeyboardButton("💳 Comprar Ahora", callback_data="cta_comprar_ahora")],
            [InlineKeyboardButton("📅 Plan de Pagos", callback_data="cta_plan_pagos")],
            [InlineKeyboardButton("🎫 Usar Cupón", callback_data="cta_cupon")]
        ]
    elif context_type == "purchase_intent":
        buttons = [
            [InlineKeyboardButton("✅ Finalizar Compra", callback_data="cta_finalizar_compra")],
            [InlineKeyboardButton("🤝 Negociar Precio", callback_data="cta_negociar")],
            [InlineKeyboardButton("👨‍💼 Asesor Especializado", callback_data="cta_asesor_curso")]
        ]
    elif context_type == "high_interest":
        buttons = [
            [InlineKeyboardButton("🎯 Reservar Lugar", callback_data="cta_reservar")],
            [InlineKeyboardButton("📞 Llamada Inmediata", callback_data="cta_llamar")]
        ]
    # Verificar interest_score para high_interest
    if context_type == "high_interest" and user_id:
        score = get_interest_score(user_id)
        if score is None or score < 30:
            buttons = [
                [InlineKeyboardButton("✅ Finalizar Compra", callback_data="cta_finalizar_compra")],
                [InlineKeyboardButton("🤝 Negociar Precio", callback_data="cta_negociar")],
                [InlineKeyboardButton("👨‍💼 Asesor Especializado", callback_data="cta_asesor_curso")]
            ]
    return InlineKeyboardMarkup(buttons) if buttons else InlineKeyboardMarkup([])

def create_promotion_keyboard(promotion_id: str, user_id=None):
    score = get_interest_score(user_id) if user_id is not None else None
    if score is None or score < UMBRAL_PROMO:
        return None
    keyboard = [
        [InlineKeyboardButton("✅ Aplicar Promoción", callback_data=f"apply_promo_{promotion_id}")],
        [InlineKeyboardButton("🔙 Ver Otras Promociones", callback_data="promotions_list")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==============================
# BOTONES CTA DINÁMICOS DESDE SUPABASE
# ==============================
def get_cta_buttons(context_type="default"):
    cache_key = f"cta_buttons_{context_type}"
    cached_result = cache.get(cache_key)
    if cached_result:
        cta_buttons = cached_result
    else:
        try:
            filters = {"active": "eq.TRUE", "context_type": f"eq.{context_type}"}
            cta_buttons = supabase_query("cta_buttons", filters)
            if not cta_buttons:
                filters = {"active": "eq.TRUE", "context_type": "eq.default"}
                cta_buttons = supabase_query("cta_buttons", filters)
            if cta_buttons:
                cta_buttons.sort(key=lambda x: x.get('priority', 999))
                cache.set(cache_key, cta_buttons)
            else:
                cta_buttons = [
                    {"text": "✅ Reservar mi lugar", "callback_data": "cta_reservar", "priority": 1},
                    {"text": "📄 Quiero la info completa", "callback_data": "cta_info_completa", "priority": 2},
                    {"text": "🤝 Que me contacte un asesor", "callback_data": "cta_asesor", "priority": 3},
                    {"text": "📚 Ver más cursos", "callback_data": "cta_ver_cursos", "priority": 4},
                    {"text": "🏠 Volver al inicio", "callback_data": "cta_inicio", "priority": 5}
                ]
        except Exception as e:
            logger.error(f"Error obteniendo botones CTA: {e}")
            cta_buttons = [
                {"text": "✅ Reservar mi lugar", "callback_data": "cta_reservar", "priority": 1},
                {"text": "📄 Quiero la info completa", "callback_data": "cta_info_completa", "priority": 2},
                {"text": "🤝 Que me contacte un asesor", "callback_data": "cta_asesor", "priority": 3},
                {"text": "📚 Ver más cursos", "callback_data": "cta_ver_cursos", "priority": 4},
                {"text": "🏠 Volver al inicio", "callback_data": "cta_inicio", "priority": 5}
            ]
    # Filtrar botones de promociones
    cta_buttons = [b for b in cta_buttons if 'promo' not in b['callback_data'] and 'descuento' not in b['callback_data']]
    # Asegurar que los botones clave estén presentes
    has_inicio = any(b["callback_data"] == "cta_inicio" for b in cta_buttons)
    has_ver_cursos = any(b["callback_data"] == "cta_ver_cursos" for b in cta_buttons)
    if not has_ver_cursos:
        cta_buttons.append({"text": "📚 Ver más cursos", "callback_data": "cta_ver_cursos", "priority": 98})
    if not has_inicio:
        cta_buttons.append({"text": "🏠 Volver al inicio", "callback_data": "cta_inicio", "priority": 99})
    cta_buttons.sort(key=lambda x: x.get('priority', 999))
    return cta_buttons

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
        msg['From'] = SMTP_USERNAME
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
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_USERNAME, ADVISOR_EMAIL, text)
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
# CARGA DE PLANTILLAS FAQ
# ==============================
PLANTILLAS_FAQ = []
try:
    with open(os.path.join(os.path.dirname(__file__), "plantillas.json"), "r", encoding="utf-8") as f:
        PLANTILLAS_FAQ = json.load(f)
except Exception as e:
    print(f"[Error] No se pudo cargar plantillas.json: {e}")

def generar_faq_contexto(course, modules=None):
    """Genera contexto few-shot FAQ usando datos reales del curso y módulos."""
    ejemplos = []
    for plantilla in PLANTILLAS_FAQ:
        respuesta = plantilla["respuesta"]
        # Reemplaza campos de la plantilla por datos reales
        if course:
            for campo in plantilla["campos"]:
                if campo == "modules_list" and modules:
                    mod_list = "\n".join([f"Módulo {m['module_index']}: {m['name']}" for m in modules])
                    respuesta = respuesta.replace("[modules_list]", mod_list)
                elif campo in course:
                    respuesta = respuesta.replace(f"[{campo}]", str(course.get(campo, "N/A")))
                else:
                    respuesta = respuesta.replace(f"[{campo}]", "N/A")
        ejemplos.append(f"Usuario: {plantilla['pregunta']}\nAsistente: {respuesta}")
    return "\n\n".join(ejemplos)

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
            "Authorization": f"Bearer {OPENAI_API_KEY}",
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

def detect_vague_reference(user_input: str, mem: Memory) -> bool:
    """Detecta si el usuario hace referencia vaga a un curso mostrado y actualiza selected_course si corresponde."""
    user_input_lower = user_input.lower().strip()
    if not mem.last_presented_courses:
        return False
    idx = None
    if "el primero" in user_input_lower or "el 1" in user_input_lower:
        idx = 0
    elif "el segundo" in user_input_lower or "el 2" in user_input_lower:
        idx = 1
    elif "el tercero" in user_input_lower or "el 3" in user_input_lower:
        idx = 2
    elif "el cuarto" in user_input_lower or "el 4" in user_input_lower:
        idx = 3
    elif "el anterior" in user_input_lower or "ese" in user_input_lower or "ese curso" in user_input_lower or "ese mismo" in user_input_lower or user_input_lower.strip() in ["sí", "si", "ok", "vale", "perfecto"]:
        idx = 0
    if idx is not None and idx < len(mem.last_presented_courses):
        curso = mem.last_presented_courses[idx]
        mem.lead_data.selected_course = curso['id']
        return True
    return False

def update_user_profile(user_input: str, mem: Memory):
    """Detecta y guarda nombre, rol, sector o intereses del usuario si los menciona."""
    user_input_lower = user_input.lower()
    # Nombre (si dice "me llamo X" o "soy X")
    nombre_match = re.search(r"me llamo ([a-záéíóúüñ ]+)", user_input_lower)
    if nombre_match:
        mem.lead_data.name = nombre_match.group(1).strip().title()
    elif user_input_lower.startswith("soy "):
        posible_nombre = user_input[4:].split()[0]
        if posible_nombre and len(posible_nombre) > 2:
            mem.lead_data.name = posible_nombre.title()
    # Rol/sector/intereses
    roles = ["gerente", "marketing", "ventas", "educación", "desarrollador", "diseñador", "empresario", "profesor", "estudiante", "recursos humanos", "tecnología", "innovación"]
    for rol in roles:
        if rol in user_input_lower:
            mem.lead_data.role = rol
    intereses = []
    if "automatizar" in user_input_lower:
        intereses.append("automatización")
    if "imágenes" in user_input_lower or "imagenes" in user_input_lower:
        intereses.append("imágenes")
    if "chatgpt" in user_input_lower:
        intereses.append("ChatGPT")
    if "proyectos" in user_input_lower:
        intereses.append("proyectos")
    if intereses:
        mem.lead_data.interests = list(set(getattr(mem.lead_data, 'interests', [])) | set(intereses))

def detect_objecion(user_input: str) -> str:
    user_input_lower = user_input.lower()
    if any(x in user_input_lower for x in ["caro", "carísimo", "costoso", "no tengo dinero", "no puedo pagar"]):
        return "precio"
    if any(x in user_input_lower for x in ["no tengo tiempo", "muy largo", "no puedo ahora", "ocupado"]):
        return "tiempo"
    if any(x in user_input_lower for x in ["no estoy seguro", "dudo", "no sé si", "no se si", "no sé", "no se"]):
        return "duda"
    return ""

def get_active_promos_text():
    promos = get_promotions()
    if promos:
        txt = "\n\n¡Promoción especial! "
        for p in promos:
            txt += f"{p['name']}: {p['description']} "
            if p.get('code'):
                txt += f"(Código: {p['code']}) "
        txt += "\nAprovecha antes de que termine."
        return txt
    return ""

def should_offer_purchase(mem: Memory) -> bool:
    # Si el usuario preguntó por precio, módulos, info, pero no ha comprado ni pedido el link
    if mem.lead_data.selected_course and mem.lead_data.stage != "pagado":
        last_bot = mem.history[-1]["bot_reply"].lower() if mem.history else ""
        if any(x in last_bot for x in ["precio", "módulos", "temario", "información", "detalles"]):
            return True
    return False

def get_relevant_course(user_input: str, mem: Memory) -> dict:
    """Devuelve el curso relevante según el contexto, referencias vagas o último curso mencionado."""
    # 1. Si hay referencia vaga, usar el seleccionado
    if mem.lead_data.selected_course:
        detail = get_course_detail(mem.lead_data.selected_course)
        if detail:
            return detail
    # 2. Si el usuario menciona un nombre de curso explícito
    cursos = get_courses()
    for course in cursos:
        if course['name'].lower() in user_input.lower():
            mem.lead_data.selected_course = course['id']
            return course
    # 3. Si hay cursos presentados, usar el último mostrado
    if mem.last_presented_courses:
        last = mem.last_presented_courses[-1]
        detail = get_course_detail(last['id'])
        if detail:
            mem.lead_data.selected_course = detail['id']
            return detail
    return {}  # Nunca None, siempre dict vacío si no hay curso relevante

def build_context_for_llm(intent_data: dict, mem: Memory, user_input: str) -> str:
    update_user_profile(user_input, mem)
    intent = intent_data.get("intent", "UNKNOWN")
    course_name = intent_data.get("course_name")
    context = ""
    # Historial breve
    if mem.history:
        context += "Historial reciente:\n"
        for h in mem.history[-3:]:
            context += f"Usuario: {h['user_input']}\nBot: {h['bot_reply']}\n"
    # Perfil/intereses
    if hasattr(mem.lead_data, 'name') and mem.lead_data.name:
        context += f"\nNombre del usuario: {mem.lead_data.name}\n"
    if hasattr(mem.lead_data, 'role') and mem.lead_data.role:
        context += f"Rol/sector: {mem.lead_data.role}\n"
    if hasattr(mem.lead_data, 'interests') and mem.lead_data.interests:
        context += f"Intereses: {', '.join(mem.lead_data.interests)}\n"
    if mem.lead_data.email:
        context += f"Correo: {mem.lead_data.email}\n"
    if mem.lead_data.phone:
        context += f"Teléfono: {mem.lead_data.phone}\n"
    # Cursos presentados
    if mem.last_presented_courses:
        context += "\nCursos presentados recientemente:\n"
        for i, c in enumerate(mem.last_presented_courses):
            context += f"{i+1}. {c['name']} (id: {c['id']})\n"
    # Curso seleccionado
    if mem.lead_data.selected_course:
        sel = get_course_detail(mem.lead_data.selected_course)
        if sel:
            context += f"\nCurso actualmente seleccionado:\nNombre: {sel['name']}\nDescripción: {sel.get('short_description','')}\nDuración: {sel.get('total_duration','N/A')} horas\nPrecio: {sel['price_usd']} {sel['currency']}\nNivel: {sel.get('level','N/A')}\n"
            modules = get_modules(sel["id"])
            if modules:
                context += "Módulos:\n"
                for m in modules:
                    context += f"  - {m['name']} ({m.get('duration','N/A')}h)\n"
            if sel.get("purchase_link"):
                context += f"Enlace de compra: {sel['purchase_link']}\n"
    # Intención y datos de la base
    context += "\n---\n"
    context += build_context_for_llm_base(intent_data, mem)
    # Copy vendedor y recomendación proactiva
    if intent in ["BUY_COURSE", "ASK_ENROLLMENT"] or should_offer_purchase(mem):
        context += "\nCopy vendedor: ¡Aprovecha ahora! Los cupos son limitados y podrás acceder al contenido inmediatamente después del pago. Si tienes alguna duda, ¡estoy aquí para ayudarte!\n"
    # Promociones dinámicas SOLO si la intención es relevante
    mostrar_promos = False
    if intent in ["ASK_PRICE", "BUY_COURSE", "ASK_PROMOTIONS"]:
        mostrar_promos = True
    # Detectar objeción o indecisión
    obj = detect_objecion(user_input)
    if obj in ["precio", "duda"]:
        mostrar_promos = True
    if mostrar_promos:
        context += get_active_promos_text()
    # Objeciones
    if obj == "precio":
        context += "\nRespuesta a objeción de precio: Muchos alumnos consideran que la inversión se recupera rápidamente gracias a las oportunidades laborales y de negocio que se abren tras el curso. Además, ofrecemos promociones y facilidades de pago.\n"
    elif obj == "tiempo":
        context += "\nRespuesta a objeción de tiempo: El curso está diseñado para que puedas avanzar a tu ritmo y aprovechar cada módulo según tu disponibilidad.\n"
    elif obj == "duda":
        context += "\nRespuesta a objeción de duda: Si tienes preguntas, puedo ponerte en contacto con un asesor o enviarte testimonios de alumnos que estaban en tu misma situación.\n"
    # Sugerencia de próximos pasos
    context += "\nAl final de tu respuesta, sugiere siempre un próximo paso útil o una pregunta relacionada, como: '¿Te gustaría que te recomiende otro curso?', '¿Quieres saber el temario?', '¿Te gustaría inscribirte ahora?', etc.\n"
    # Empatía y entusiasmo
    context += "\nRecuerda mostrar empatía, entusiasmo y disposición para ayudar en todo momento.\n"
    return context

def build_context_for_llm_base(intent_data: dict, mem: Memory) -> str:
    intent = intent_data.get("intent", "UNKNOWN")
    course_name = intent_data.get("course_name")
    context = ""
    if intent == "LIST_COURSES":
        cursos = get_courses()
        if cursos:
            context += "Estos son los cursos disponibles:\n"
            mem.last_presented_courses = [{"id": c["id"], "name": c["name"]} for c in cursos]
            for c in cursos:
                context += f"- {c['name']}: {c.get('short_description','Sin descripción')}\n"
        else:
            context += "No hay cursos disponibles en este momento."
    elif intent in ["GET_COURSE_INFO", "ASK_PRICE", "ASK_MODULES", "ASK_DURATION", "ASK_ENROLLMENT", "BUY_COURSE"]:
        # Buscar el curso relevante
        curso = get_relevant_course(course_name or "", mem)
        if curso:
            context += f"Datos del curso:\nNombre: {curso['name']}\nDescripción: {curso.get('short_description','')}\nDuración: {curso.get('total_duration','N/A')} horas\nPrecio: {curso['price_usd']} {curso['currency']}\nNivel: {curso.get('level','N/A')}\n"
            modules = get_modules(curso["id"])
            if modules:
                context += "Módulos:\n"
                for m in modules:
                    context += f"  - {m['name']} ({m.get('duration','N/A')}h)\n"
            if intent == "BUY_COURSE" and curso.get("purchase_link"):
                context += f"Enlace de compra: {curso['purchase_link']}\n"
            # Actualizar memoria de curso seleccionado
            mem.lead_data.selected_course = curso["id"]
        else:
            # Si no hay curso relevante, sugerir el último mostrado o preguntar proactivamente
            if mem.last_presented_courses:
                last = mem.last_presented_courses[-1]
                context += f"No se encontró el curso solicitado. ¿Te refieres a '{last['name']}'? Si es así, dime 'sí' o 'ese'.\n"
            else:
                context += "No se encontró el curso solicitado. Por favor, dime el nombre exacto del curso que te interesa.\n"
    elif intent == "ASK_PROMOTIONS":
        promos = get_promotions()
        if promos:
            context += "Promociones activas:\n"
            for p in promos:
                context += f"- {p['name']}: {p['description']}\n"
        else:
            context += "No hay promociones activas."
    else:
        context += "No se requiere información de la base de datos para esta intención."
    return context

def process_user_input(user_input: str, memory: Memory) -> str:
    """Procesa el input del usuario usando OpenAI con prompt mejorado."""
    try:
        # Preparar el contexto para el prompt
        name = memory.lead_data.name or "amigo"
        selected_course = memory.lead_data.selected_course or "ninguno"
        interests = ", ".join(memory.lead_data.interests) if memory.lead_data.interests else "no especificados"
        stage = memory.lead_data.stage or "inicio"
        
        # Preparar historial de conversación
        history_text = ""
        if memory.history:
            recent_history = memory.history[-5:]  # Últimas 5 interacciones
            for entry in recent_history:
                history_text += f"Usuario: {entry.get('user_input', '')}\n"
                history_text += f"Brenda: {entry.get('bot_reply', '')}\n\n"
        
        # Obtener información de cursos disponibles
        courses = get_courses()
        available_courses = ""
        if courses:
            for course in courses:
                available_courses += f"- {course['name']}: {course.get('short_description', 'Sin descripción')}\n"
        else:
            available_courses = "No hay cursos disponibles en este momento."
        
        # Usar el prompt mejorado
        system_prompt = get_enhanced_system_prompt().format(
            name=name,
            selected_course=selected_course,
            interests=interests,
            stage=stage,
            history=history_text,
            available_courses=available_courses
        )
        
        # Crear el mensaje para OpenAI
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        # Llamar a OpenAI usando la función existente
        result = openai_intent_and_response(user_input, system_prompt)
        bot_reply = result.get("response", "")
        
        # Validar y mejorar la respuesta si es necesario
        if not bot_reply or len(bot_reply) < 10:
            bot_reply = "¡Gracias por tu mensaje! 😊 ¿En qué puedo ayudarte específicamente con nuestros cursos de IA?"
        
        # Asegurar que la respuesta termine con una pregunta o CTA
        if not any(char in bot_reply[-1] for char in "?!"):
            bot_reply += " ¿Te gustaría que te ayude con algo más específico?"
        
        return bot_reply
        
    except Exception as e:
        logger.error(f"Error procesando input: {e}")
        return "¡Hola! 😊 ¿En qué puedo ayudarte con nuestros cursos de Inteligencia Artificial?"

# ==============================
# I/O (Telegram Integration)
# ==============================
# Global memory instance for Telegram handlers
global_mem = Memory()
global_user_id = None # This will be set per user in real Telegram scenario

def create_nav_keyboard(show_back=True, show_home=True, show_next=True):
    buttons = []
    row = []
    if show_back:
        row.append(InlineKeyboardButton("⬅️ Atrás", callback_data="nav_back"))
    if show_home:
        row.append(InlineKeyboardButton("🏠 Inicio", callback_data="nav_home"))
    if show_next:
        row.append(InlineKeyboardButton("➡️ Siguiente", callback_data="nav_next"))
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons) if buttons else InlineKeyboardMarkup([])

def combine_keyboards(kb1, kb2):
    # Combina dos InlineKeyboardMarkup en uno solo
    if kb1 is None and kb2 is None:
        return None
    rows = []
    if kb1 is not None and hasattr(kb1, 'inline_keyboard'):
        rows.extend(kb1.inline_keyboard)
    if kb2 is not None and hasattr(kb2, 'inline_keyboard'):
        rows.extend(kb2.inline_keyboard)
    return InlineKeyboardMarkup(rows) if rows else None

@handle_telegram_errors
async def send_agent_telegram(update: Update, msg: str, keyboard=None, msg_critico=False) -> None:
    """Sends a message to the user via Telegram. Si msg_critico=True, muestra el teclado pasado; si False, no muestra teclado."""
    if not update.effective_chat:
        logger.error("No se pudo enviar el mensaje, effective_chat es None")
        return
    try:
        if msg_critico:
            await update.effective_chat.send_message(msg, reply_markup=keyboard)
        else:
            await update.effective_chat.send_message(msg)
        logger.debug(f"Mensaje enviado exitosamente a usuario {update.effective_user.id if update.effective_user else 'unknown'}")
    except Exception as e:
        logger.error(f"Error enviando mensaje a Telegram: {e}")
        raise

@handle_telegram_errors
async def send_processing_message(update: Update) -> None:
    """Envía un mensaje de 'procesando' mientras se genera la respuesta."""
    if not update.effective_chat:
        return
    
    try:
        await update.effective_chat.send_message("🤔 Procesando tu solicitud...")
    except Exception as e:
        logger.warning(f"No se pudo enviar mensaje de procesamiento: {e}")

@handle_telegram_errors
async def edit_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, new_text: str, keyboard=None) -> None:
    """Edita un mensaje existente usando el contexto. Si no se pasa teclado, agrega el de navegación persistente."""
    try:
        if keyboard is None:
            keyboard = create_nav_keyboard()
        await context.bot.edit_message_text(new_text, chat_id=chat_id, message_id=message_id, reply_markup=keyboard)
    except Exception as e:
        logger.warning(f"No se pudo editar mensaje: {e}")

@handle_telegram_errors
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las respuestas a botones interactivos con nuevos CTAs y privacidad."""
    global global_mem, global_user_id
    
    query = update.callback_query
    if not query:
        logger.warning("Callback query es None")
        return
    
    await query.answer()  # Acknowledge the callback
    
    if not query.data:
        return
    
    user_id_str = str(query.from_user.id)
    logger.info(f"Callback recibido de usuario {user_id_str}: {query.data}")
    
    # Ensure memory is loaded
    if global_user_id != user_id_str or not global_mem.lead_data.user_id:
        global_user_id = user_id_str
        global_mem = Memory()
        global_mem.load(global_user_id)
        global_mem.lead_data.user_id = user_id_str
        if not global_mem.lead_data.user_id:
            global_mem.lead_data.user_id = user_id_str
            global_mem.lead_data.stage = "inicio"
            global_mem.save()
    
    try:
        # --- FLUJO DE PRIVACIDAD ---
        if query.data == "privacy_accept":
            global_mem.lead_data.privacy_accepted = True
            global_mem.save()
            logger.info(f"Usuario {user_id_str} aceptó la privacidad")
            # Enviar nuevo mensaje de bienvenida con botones, sin editar el aviso
            if not global_mem.lead_data.name:
                welcome_text = "¡Perfecto! 👋 Ahora puedo ayudarte mejor.\n\n¿Cómo te llamas?"
                keyboard = create_contextual_cta_keyboard("default", user_id_str)
                await send_agent_telegram(update, welcome_text, keyboard, msg_critico=True)
                global_mem.lead_data.stage = "awaiting_name"
                global_mem.save()
            else:
                welcome_msg = (
                    f"¡Hola {global_mem.lead_data.name}! 👋\n\n"
                    "¿Qué te gustaría aprender sobre Inteligencia Artificial? "
                    "Tenemos cursos de IA práctica, prompts, generación de imágenes y más."
                )
                keyboard = create_contextual_cta_keyboard("default", user_id_str)
                await send_agent_telegram(update, welcome_msg, keyboard, msg_critico=True)
            return
            
        elif query.data == "privacy_view":
            # Re-enviar el aviso de privacidad
            privacy_text = (
                "🔒 **Aviso de Privacidad Completo**\n\n"
                "**Información que recopilamos:**\n"
                "• Nombre completo\n"
                "• Dirección de correo electrónico\n"
                "• Número de teléfono\n"
                "• Información sobre tus intereses en cursos\n\n"
                "**Cómo utilizamos tu información:**\n"
                "• Para brindarte información sobre nuestros cursos\n"
                "• Para enviarte materiales educativos relevantes\n"
                "• Para contactarte sobre promociones especiales\n"
                "• Para mejorar nuestros servicios\n\n"
                "**Protección de datos:**\n"
                "• Tus datos están seguros y protegidos\n"
                "• No compartimos tu información con terceros\n"
                "• Puedes solicitar la eliminación en cualquier momento\n\n"
                "¿Aceptas que procesemos tus datos según este aviso?"
            )
            privacy_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Acepto y continúo", callback_data="privacy_accept")],
                [InlineKeyboardButton("🔒 Ver Aviso Completo", callback_data="privacy_view")]
            ])
            await query.edit_message_text(privacy_text, reply_markup=privacy_keyboard, parse_mode='Markdown')
            return
        
        # --- FLUJO DE BOTONES CTA EXISTENTES ---
        elif query.data in ["cta_reservar"]:
            await query.edit_message_text("¡Perfecto! 🎉 Hemos registrado tu interés en reservar tu lugar. Un asesor se pondrá en contacto contigo para finalizar el proceso. ¿Te gustaría dejar tu número de WhatsApp o prefieres que te contactemos por aquí?", reply_markup=None)
            user_data = {
                'user_id': global_mem.lead_data.user_id,
                'name': global_mem.lead_data.name,
                'email': global_mem.lead_data.email,
                'phone': global_mem.lead_data.phone,
                'selected_course': global_mem.lead_data.selected_course,
                'stage': global_mem.lead_data.stage
            }
            notify_advisor_reservation_request(user_data)
            return
            
        elif query.data in ["cta_info_completa"]:
            # Disparador de evento: MORE_INFO
            update_interest_score(user_id_str, "MORE_INFO", {"source": "cta_info_completa"})
            await query.edit_message_text("Aquí tienes la información completa del curso. Si tienes alguna pregunta, ¡estoy para ayudarte!", reply_markup=None)
            try:
                # Chequeo robusto de chat_id
                chat_id = None
                if query.message is not None and hasattr(query.message, "chat") and query.message.chat is not None:
                    chat_id = query.message.chat.id  # type: ignore
                if chat_id:
                    with open('pdf_prueba.pdf', 'rb') as pdf_file:
                        await context.bot.send_document(chat_id=chat_id, document=pdf_file)
                    # Chequeo de umbral para sugerir llamada
                    score = get_interest_score(user_id_str)
                    if score is not None and score >= 20:
                        await context.bot.send_message(chat_id=chat_id, text="¡Veo que estás muy interesado! ¿Te gustaría agendar una llamada con un asesor humano?")
            except Exception as e:
                logger.warning(f"No se pudo enviar PDF info completa o checar interest_score: {e}")
            return
            
        elif query.data in ["cta_asesor", "cta_asesor_curso", "cta_asistencia", "cta_llamar"]:
            # Siempre permitir contactar asesor, sin importar score ni curso
            await send_agent_telegram(update, "¡Listo! Un asesor de Aprende y Aplica IA te contactará muy pronto para resolver todas tus dudas y apoyarte en tu inscripción. 😊", create_nav_keyboard(), msg_critico=True)
            user_data = {
                'user_id': global_mem.lead_data.user_id,
                'name': global_mem.lead_data.name,
                'email': global_mem.lead_data.email,
                'phone': global_mem.lead_data.phone,
                'selected_course': global_mem.lead_data.selected_course,
                'stage': global_mem.lead_data.stage
            }
            notify_advisor_contact_request(user_data)
            return
            
        elif query.data in ["cta_ver_cursos", "cta_otros_cursos"]:
            await query.edit_message_text("Te muestro otros cursos disponibles:", reply_markup=None)
            cursos = get_courses()
            if cursos and query.message and query.message.chat:
                keyboard = create_courses_list_keyboard(cursos)
                await context.bot.send_message(chat_id=query.message.chat.id, text="Selecciona un curso para más información:", reply_markup=keyboard)
            elif query.message and query.message.chat:
                await context.bot.send_message(chat_id=query.message.chat.id, text="Por el momento no hay otros cursos disponibles.")
            return
            
        elif query.data in ["cta_inicio"]:
            await query.edit_message_text("Has vuelto al inicio. ¿En qué puedo ayudarte hoy?", reply_markup=None)
            keyboard = create_main_keyboard()
            if query.message and query.message.chat:
                await context.bot.send_message(chat_id=query.message.chat.id, text="Menú principal:", reply_markup=keyboard)
            return
            
        # --- NUEVOS CTAs CONTEXTUALES ---
        elif query.data in ["cta_comprar_curso", "cta_comprar_ahora", "cta_finalizar_compra", "cta_inscribirse"]:
            course_id = global_mem.lead_data.selected_course
            if course_id:
                course = get_course_detail(course_id)
                # Simular siempre un enlace de compra aunque no exista en la base
                purchase_link = course.get("purchase_link") if course else None
                if not purchase_link:
                    purchase_link = "https://www.ejemplo.com/compra-curso"
                buy_msg = (
                    f"💳 <b>Comprar: {course['name'] if course else 'Curso seleccionado'}</b>\n\n"
                    f"Precio: ${course['price_usd'] if course else 'N/A'} {course['currency'] if course else ''}\n\n"
                    f"<a href='{purchase_link}'>Haz clic aquí para comprar</a>\n\n"
                    f"Después de la compra, recibirás acceso inmediato al curso. "
                    f"¿Necesitas ayuda con algo más?"
                )
                await query.edit_message_text(buy_msg, reply_markup=None, parse_mode='HTML')
                # No notifiques ni muestres error técnico si el enlace es ficticio
            else:
                await query.edit_message_text("Primero necesitas seleccionar un curso. ¿Cuál te interesa?", reply_markup=create_contextual_cta_keyboard("default", user_id_str))
            return
            
        elif query.data in ["cta_ver_modulos"]:
            course_id = global_mem.lead_data.selected_course
            if course_id:
                modules = get_modules(course_id)
                if modules:
                    modules_text = "📋 **Módulos del curso:**\n\n"
                    for i, module in enumerate(modules, 1):
                        modules_text += f"{i}. **{module['name']}**\n"
                        modules_text += f"   Duración: {module.get('duration', 'N/A')} horas\n"
                        modules_text += f"   {module.get('description', '')}\n\n"
                    
                    keyboard = create_contextual_cta_keyboard("course_selected", user_id_str)
                    await query.edit_message_text(modules_text, reply_markup=keyboard, parse_mode='Markdown')
                else:
                    await query.edit_message_text("No se encontraron módulos para este curso. Un asesor te contactará con más información.", reply_markup=None)
            else:
                await query.edit_message_text("Primero necesitas seleccionar un curso. ¿Cuál te interesa?", reply_markup=create_contextual_cta_keyboard("default", user_id_str))
            return
            
        elif query.data in ["cta_descuento", "cta_cupon"]:
            promos = get_promotions()
            if promos:
                promo_text = "🎯 **Promociones disponibles:**\n\n"
                for promo in promos:
                    promo_text += f"• **{promo['name']}**: {promo['description']}\n"
                    if promo.get('code'):
                        promo_text += f"  Código: `{promo['code']}`\n"
                    promo_text += "\n"
                
                keyboard = create_contextual_cta_keyboard("pricing_inquiry", user_id_str)
                await query.edit_message_text(promo_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await query.edit_message_text("Por el momento no hay promociones activas, pero puedes contactar a un asesor para consultar descuentos especiales.", reply_markup=create_contextual_cta_keyboard("default", user_id_str))
            return
            
        elif query.data in ["cta_plan_pagos", "cta_negociar"]:
            await query.edit_message_text("¡Perfecto! Un asesor especializado en planes de pago te contactará para ofrecerte las mejores opciones. ¿Te parece bien?", reply_markup=None)
            user_data = {
                'user_id': global_mem.lead_data.user_id,
                'name': global_mem.lead_data.name,
                'email': global_mem.lead_data.email,
                'phone': global_mem.lead_data.phone,
                'selected_course': global_mem.lead_data.selected_course,
                'stage': global_mem.lead_data.stage
            }
            notify_advisor_contact_request(user_data)
            return
            
        elif query.data in ["cta_promociones"]:
            promos = get_promotions()
            if promos:
                promo_text = "💰 **Promociones especiales:**\n\n"
                for promo in promos:
                    promo_text += f"🎁 **{promo['name']}**\n"
                    promo_text += f"{promo['description']}\n"
                    if promo.get('code'):
                        promo_text += f"Código: `{promo['code']}`\n"
                    promo_text += "\n"
                
                keyboard = create_contextual_cta_keyboard("pricing_inquiry", user_id_str)
                await query.edit_message_text(promo_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await query.edit_message_text("Por el momento no hay promociones activas, pero puedes contactar a un asesor para consultar descuentos especiales.", reply_markup=create_contextual_cta_keyboard("default", user_id_str))
            return
            
        # --- FLUJO DE NAVEGACIÓN ---
        elif query.data in ["nav_back", "nav_home", "nav_next"]:
            # Navegación básica
            if query.data == "nav_home":
                await query.edit_message_text("🏠 Has vuelto al inicio. ¿En qué puedo ayudarte?", reply_markup=None)
                keyboard = create_main_keyboard()
                if query.message and query.message.chat:
                    await context.bot.send_message(chat_id=query.message.chat.id, text="Menú principal:", reply_markup=keyboard)
            elif query.data == "nav_back":
                await query.edit_message_text("Has regresado al paso anterior. ¿Qué te gustaría hacer ahora?", reply_markup=None)
                keyboard = create_main_keyboard()
                if query.message and query.message.chat:
                    await context.bot.send_message(chat_id=query.message.chat.id, text="Opciones disponibles:", reply_markup=keyboard)
            elif query.data == "nav_next":
                await query.edit_message_text("Avanzaste al siguiente paso. ¿Qué te gustaría hacer ahora?", reply_markup=None)
                keyboard = create_main_keyboard()
                if query.message and query.message.chat:
                    await context.bot.send_message(chat_id=query.message.chat.id, text="Opciones disponibles:", reply_markup=keyboard)
            return
            
        # --- FLUJO DE CURSOS ESPECÍFICOS ---
        elif query.data.startswith("course_"):
            course_id = query.data.replace("course_", "")
            course = get_course_detail(course_id)
            if course:
                global_mem.lead_data.selected_course = course_id
                global_mem.save()
                
                course_text = (
                    f"📚 **{course['name']}**\n\n"
                    f"{course.get('short_description', '')}\n\n"
                    f"**Detalles:**\n"
                    f"• Duración: {course.get('total_duration', 'N/A')} horas\n"
                    f"• Nivel: {course.get('level', 'N/A')}\n"
                    f"• Precio: ${course['price_usd']} {course['currency']}\n"
                    f"• Modalidad: {course.get('modality', 'N/A')}\n\n"
                    f"¿Te gustaría más información sobre este curso?"
                )
                
                keyboard = create_contextual_cta_keyboard("course_selected", user_id_str)
                await query.edit_message_text(course_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await query.edit_message_text("No se encontró información del curso. ¿Te gustaría ver otros cursos disponibles?", reply_markup=create_contextual_cta_keyboard("default", user_id_str))
            return
            
        else:
            # Callback no reconocido
            logger.warning(f"Callback no reconocido: {query.data}")
            await query.edit_message_text("Opción no disponible. ¿En qué puedo ayudarte?", reply_markup=create_contextual_cta_keyboard("default", user_id_str))
            return
            
    except Exception as e:
        logger.error(f"Error en handle_callback_query: {e}", exc_info=True)
        await query.edit_message_text("Lo siento, hubo un problema técnico. ¿Te gustaría que un asesor humano te contacte?", reply_markup=create_contextual_cta_keyboard("default", user_id_str))

# --- Disparador: QUIZ ---
@handle_telegram_errors
async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja respuestas a encuestas tipo quiz."""
    user_id = str(update.effective_user.id) if update.effective_user else None
    poll_id = getattr(getattr(update, 'poll_answer', None), 'poll_id', None)
    if user_id and poll_id:
        update_interest_score(user_id, "QUIZ", {"poll_id": poll_id})
        logger.info(f"PollAnswer recibido de usuario {user_id}")

# --- Disparador: PAYMENT (webhook) ---
def handle_payment_webhook(user_id: str, payment_data: dict) -> None:
    """Llamar cuando se reciba un pago exitoso (webhook externo)."""
    if user_id:
        update_interest_score(user_id, "PAYMENT", {"payment": payment_data})
        logger.info(f"Pago registrado para usuario {user_id}")

# --- Disparador: SESSION_90S ---
def check_session_90s(mem: Memory, user_input_time: float) -> None:
    """Dispara evento si el segundo mensaje ocurre >=90s después del primero."""
    if len(mem.history) == 2:
        t0 = mem.history[0]["timestamp"]
        t1 = mem.history[1]["timestamp"]
        if t1 - t0 >= 90:
            if mem.lead_data.user_id:
                update_interest_score(mem.lead_data.user_id, "SESSION_90S", {})
                logger.info(f"SESSION_90S disparado para usuario {mem.lead_data.user_id}")

# --- Disparador: INACTIVITY_WEEK (cron job) ---
def cron_inactivity_week():
    """Tarea diaria: resta 7 puntos por cada semana sin mensajes."""
    try:
        url = f"{SUPABASE_URL}/rest/v1/interest_score"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            now = time.time()
            for row in r.json():
                user_id = row["user_id"]
                updated_at = row.get("updated_at")
                if updated_at:
                    try:
                        last = datetime.fromisoformat(updated_at.replace("Z", ""))
                        weeks = int((now - last.timestamp()) // (7*24*3600))
                        if weeks >= 1 and user_id:
                            update_interest_score(user_id, "INACTIVITY_WEEK", {"weeks": weeks})
                            logger.info(f"INACTIVITY_WEEK disparado para usuario {user_id}, semanas: {weeks}")
                    except Exception as e:
                        logger.warning(f"Error parseando fecha de inactividad: {e}")
    except Exception as e:
        logger.error(f"Error en cron_inactivity_week: {e}")

# --- Disparador: UNSUBSCRIBE ---
@handle_telegram_errors
async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Detecta cuando el usuario elimina el bot o es expulsado."""
    user_id = str(update.effective_user.id) if update.effective_user else None
    my_chat_member = getattr(update, 'my_chat_member', None)
    new_chat_member = getattr(my_chat_member, 'new_chat_member', None)
    status = getattr(new_chat_member, 'status', None)
    if user_id and status == "kicked":
        update_interest_score(user_id, "UNSUBSCRIBE", {})
        logger.info(f"UNSUBSCRIBE disparado para usuario {user_id}")

# --- Disparador: /stop ---
@handle_telegram_errors
async def handle_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id) if update.effective_user else None
    if user_id:
        update_interest_score(user_id, "UNSUBSCRIBE", {"source": "/stop"})
        await send_agent_telegram(update, "Has cancelado la suscripción. Si deseas volver, solo escribe /start.")
        logger.info(f"UNSUBSCRIBE (stop) disparado para usuario {user_id}")

# --- Disparador: NEGATIVE ---
def detect_negative_feedback(user_input: str) -> bool:
    """Detecta feedback negativo por keywords."""
    negative_keywords = [
        "no me gustó", "no me gusto", "malo", "pésimo", "pesimo", "no sirve", "no funciona", "molesto", "spam", "demasiado caro", "engaño", "fraude"
    ]
    return any(kw in user_input.lower() for kw in negative_keywords)

# En el handler de mensajes:
    # ... existing code ...
    # --- Lead Score: función para actualizar el nivel de interés ---
    update_lead_score(user_input, global_mem, global_mem.last_activity)
    # --- Interest Score: NEGATIVE ---
    if detect_negative_feedback(user_input):
        update_interest_score(user_id_str, "NEGATIVE", {"text": user_input})
        logger.info(f"NEGATIVE feedback detectado para usuario {user_id_str}")
    # --- Interest Score: READ_VALUE ---
    if hasattr(global_mem.lead_data, 'awaiting_ack') and global_mem.lead_data.awaiting_ack:
        last_ack = getattr(global_mem.lead_data, 'last_ack_time', None)
        if last_ack and (time.time() - last_ack < 600):
            update_interest_score(user_id_str, "READ_VALUE", {})
            logger.info(f"READ_VALUE disparado para usuario {user_id_str}")
        global_mem.lead_data.awaiting_ack = False
        global_mem.save()
    # --- Interest Score: SESSION_90S ---
    check_session_90s(global_mem, time.time())
# ... existing code ...
def prompt_user_console(msg):
    return input(msg + "\nUsuario: ")

def send_agent_console(msg):
    print(f"Bot: {msg}")

def ensure_privacy(update: Update) -> bool:
    # Si el usuario ya aceptó la privacidad previamente, no mostrar aviso
    if hasattr(global_mem.lead_data, 'privacy_accepted') and global_mem.lead_data.privacy_accepted:
        return True
    # Lógica previa (por si acaso)
    if hasattr(global_mem.lead_data, 'privacy_accepted'):
        return global_mem.lead_data.privacy_accepted
    return False

async def send_privacy_notice(update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    """Envía el aviso de privacidad con botones de aceptación."""
    privacy_text = (
        "🔒 **Aviso de Privacidad**\n\n"
        "Para continuar, necesito que aceptes nuestro aviso de privacidad:\n\n"
        "• Recopilamos tu nombre, email y teléfono para brindarte información sobre nuestros cursos\n"
        "• Tus datos se utilizan únicamente para comunicación relacionada con nuestros servicios\n"
        "• No compartimos tu información con terceros sin tu consentimiento\n"
        "• Puedes solicitar la eliminación de tus datos en cualquier momento\n\n"
        "¿Aceptas que procesemos tus datos según este aviso?"
    )
    
    privacy_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Acepto y continúo", callback_data="privacy_accept")],
        [InlineKeyboardButton("🔒 Ver Aviso Completo", callback_data="privacy_view")]
    ])
    
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(privacy_text, reply_markup=privacy_keyboard, parse_mode='Markdown')
    elif hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(privacy_text, reply_markup=privacy_keyboard, parse_mode='Markdown')



# ==============================
# MAIN TELEGRAM BOT LOGIC
# ==============================
@handle_telegram_errors
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start con verificación de privacidad."""
    global global_mem, global_user_id
    if not update.effective_user:
        logger.error("Usuario efectivo es None en start_command")
        return
    user_id_str = str(update.effective_user.id)
    logger.info(f"Comando /start recibido de usuario {user_id_str}")
    # Ensure memory is loaded for this specific user
    if global_user_id != user_id_str or not global_mem.lead_data.user_id:
        global_user_id = user_id_str
        global_mem = Memory()
        global_mem.load(global_user_id)
        global_mem.lead_data.user_id = user_id_str
        if not global_mem.lead_data.user_id:
            global_mem.lead_data.user_id = user_id_str
            global_mem.lead_data.stage = "inicio"
            global_mem.save()
    # Verificar si ya aceptó la privacidad
    if not ensure_privacy(update):
        logger.info(f"Usuario {user_id_str} no ha aceptado privacidad, mostrando aviso")
        await send_privacy_notice(update, context)
        return
    # Si ya aceptó privacidad, continuar con el flujo normal
    if not global_mem.lead_data.name:
        # Si no tiene nombre, pedir nombre
        welcome_text = "¡Hola! 👋 Soy tu asistente virtual para cursos de Inteligencia Artificial.\n\n¿Cómo te llamas?"
        keyboard = create_contextual_cta_keyboard("default", user_id_str)
        await send_agent_telegram(update, welcome_text, keyboard, msg_critico=True)
        global_mem.lead_data.stage = "awaiting_name"
        global_mem.save()
        return
    # Si ya tiene nombre, mostrar menú principal
    welcome_msg = (
        f"¡Hola {global_mem.lead_data.name or 'amigo'}! 👋\n\n"
        "¿Qué te gustaría aprender sobre Inteligencia Artificial? "
        "Tenemos cursos de IA práctica, prompts, generación de imágenes y más."
    )
    keyboard = create_contextual_cta_keyboard("default", user_id_str)
    await send_agent_telegram(update, welcome_msg, keyboard, msg_critico=True)
    global_mem.save()

@handle_telegram_errors
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa mensajes de usuario de forma robusta, con manejo de sesión, validaciones y CTAs contextuales."""
    global global_mem, global_user_id

    # Verificar que el mensaje y el usuario no sean None
    if not update.message or not update.message.text:
        logger.warning("Mensaje o texto del mensaje es None")
        return
    if not update.effective_user:
        logger.error("Usuario efectivo es None")
        return

    user_input = update.message.text
    user_id_str = str(update.effective_user.id)
    logger.info(f"Mensaje recibido de usuario {user_id_str}: '{user_input[:50]}...'")

    # Si el usuario pide ver todos los cursos, resetea el curso seleccionado
    if user_input.strip().lower() == 'ver todos los cursos':
        global_mem.lead_data.selected_course = None
        global_mem.save()

    # --- NUEVO: Mapeo de intenciones a flujos de botones ---
    input_lower = user_input.strip().lower()
    # Frases exactas
    if input_lower in ["ver todos los cursos", "ver cursos", "cursos", "lista de cursos", "quiero ver cursos"]:
        await send_processing_message(update)
        cursos = get_courses()
        if cursos:
            keyboard = create_courses_list_keyboard(cursos)
            await send_agent_telegram(update, "Te muestro todos los cursos disponibles:", keyboard, msg_critico=True)
        else:
            await send_agent_telegram(update, "Por el momento no hay cursos disponibles.")
        return
    elif input_lower in ["hablar con asesor", "asesor", "contactar asesor", "quiero hablar con asesor"]:
        await send_agent_telegram(update, "¡Listo! Un asesor de Aprende y Aplica IA te contactará muy pronto para resolver todas tus dudas y apoyarte en tu inscripción. 😊", create_nav_keyboard(), msg_critico=True)
        user_data = {
            'user_id': global_mem.lead_data.user_id,
            'name': global_mem.lead_data.name,
            'email': global_mem.lead_data.email,
            'phone': global_mem.lead_data.phone,
            'selected_course': global_mem.lead_data.selected_course,
            'stage': global_mem.lead_data.stage
        }
        notify_advisor_contact_request(user_data)
        return
    elif input_lower in ["ver promociones", "promociones", "descuentos", "ver descuentos"]:
        promos = get_promotions()
        if promos:
            promo_text = "💰 **Promociones especiales:**\n\n"
            for promo in promos:
                promo_text += f"🎁 **{promo['name']}**\n"
                promo_text += f"{promo['description']}\n"
                if promo.get('code'):
                    promo_text += f"Código: `{promo['code']}`\n"
                promo_text += "\n"
            keyboard = create_contextual_cta_keyboard("pricing_inquiry", user_id_str)
            await send_agent_telegram(update, promo_text, keyboard, msg_critico=True)
        else:
            await send_agent_telegram(update, "Por el momento no hay promociones activas, pero puedes contactar a un asesor para consultar descuentos especiales.", create_contextual_cta_keyboard("default", user_id_str))
        return
    # --- NUEVO: Clasificación de intención con OpenAI para frases ambiguas o con errores ---
    else:
        # Prompt para clasificación de intención
        intent_prompt = (
            "Clasifica la intención del siguiente mensaje de usuario en una de estas categorías: "
            "'ver_cursos', 'hablar_asesor', 'ver_promociones', 'otra'. "
            "Responde solo con la categoría, sin explicación. Mensaje: " + user_input
        )
        intent_result = openai_intent_and_response(user_input, intent_prompt)
        intent = intent_result.get("response", "otra").strip().lower()
        if "ver_cursos" in intent:
            await send_processing_message(update)
            cursos = get_courses()
            if cursos:
                keyboard = create_courses_list_keyboard(cursos)
                await send_agent_telegram(update, "Te muestro otros cursos disponibles:", keyboard, msg_critico=True)
            else:
                await send_agent_telegram(update, "Por el momento no hay cursos disponibles.")
            return
        elif "asesor" in intent:
            await send_agent_telegram(update, "¡Listo! Un asesor de Aprende y Aplica IA te contactará muy pronto para resolver todas tus dudas y apoyarte en tu inscripción. 😊", create_nav_keyboard(), msg_critico=True)
            user_data = {
                'user_id': global_mem.lead_data.user_id,
                'name': global_mem.lead_data.name,
                'email': global_mem.lead_data.email,
                'phone': global_mem.lead_data.phone,
                'selected_course': global_mem.lead_data.selected_course,
                'stage': global_mem.lead_data.stage
            }
            notify_advisor_contact_request(user_data)
            return
        elif "promocion" in intent or "descuento" in intent:
            promos = get_promotions()
            if promos:
                promo_text = "💰 **Promociones especiales:**\n\n"
                for promo in promos:
                    promo_text += f"🎁 **{promo['name']}**\n"
                    promo_text += f"{promo['description']}\n"
                    if promo.get('code'):
                        promo_text += f"Código: `{promo['code']}`\n"
                    promo_text += "\n"
                keyboard = create_contextual_cta_keyboard("pricing_inquiry", user_id_str)
                await send_agent_telegram(update, promo_text, keyboard, msg_critico=True)
            else:
                await send_agent_telegram(update, "Por el momento no hay promociones activas, pero puedes contactar a un asesor para consultar descuentos especiales.", create_contextual_cta_keyboard("default", user_id_str))
            return
    # Si no se detecta intención clara, sigue el flujo conversacional normal

    # Ensure memory is loaded for this specific user
    if global_user_id != user_id_str or not global_mem.lead_data.user_id:
        global_user_id = user_id_str
        global_mem = Memory()
        global_mem.load(global_user_id)
        global_mem.lead_data.user_id = user_id_str
        if not global_mem.lead_data.user_id:
            global_mem.lead_data.user_id = user_id_str
            global_mem.lead_data.stage = "inicio"
            global_mem.save()

    # Verificar si ya aceptó la privacidad
    if not ensure_privacy(update):
        logger.info(f"Usuario {user_id_str} no ha aceptado privacidad, mostrando aviso")
        await send_privacy_notice(update, context)
        return

    # --- FLUJO ESPECIAL: DETECCIÓN DE HASHTAGS DE ANUNCIO ---
    hashtag_match = re.search(r"#([A-Z0-9_]+).*#([A-Z0-9_]+)", user_input)
    if hashtag_match:
        codigo_curso = hashtag_match.group(1)
        codigo_anuncio = hashtag_match.group(2)
        logger.info(f"Detectado flujo de anuncio: curso={codigo_curso}, anuncio={codigo_anuncio}")
        id_curso = CURSOS_MAP.get(codigo_curso)
        if not id_curso:
            await send_agent_telegram(update, "¡Gracias por tu interés! En breve un asesor te contactará con más información.")
            return
        curso_info = get_course_detail(id_curso)
        if not curso_info:
            await send_agent_telegram(update, "No se encontró información del curso en la base de datos. Un asesor te contactará.")
            return
        global_mem.lead_data.selected_course = id_curso
        global_mem.lead_data.stage = "info"
        nombre_usuario = update.effective_user.first_name if update.effective_user and update.effective_user.first_name else None
        global_mem.lead_data.name = nombre_usuario or "Usuario"
        global_mem.lead_data.interests = [codigo_anuncio]
        save_lead(global_mem.lead_data)
        global_mem.save()
        saludo = f"Hola {nombre_usuario or 'amigo'} 😄 ¿cómo estás? Mi nombre es Brenda. Soy un sistema inteligente, parte del equipo de Aprende y Aplica IA. Recibí tu solicitud de información sobre el curso: *{curso_info['name']}*. ¡Con gusto te ayudo!"
        await send_agent_telegram(update, saludo)
        await send_agent_telegram(update, "Antes de continuar, ¿cómo te gustaría que te llame?")
        global_mem.lead_data.stage = "awaiting_preferred_name"
        global_mem.save()
        return

    # --- FLUJO DE CAPTURA DE DATOS INICIALES ---
    if global_mem.lead_data.stage == "awaiting_email":
        if "@" in user_input and "." in user_input:
            global_mem.lead_data.email = user_input
            global_mem.lead_data.stage = "awaiting_phone"
            global_mem.save()
            await send_agent_telegram(update, "¡Gracias! ¿Y tu número de celular (opcional, para avisos importantes)?")
        else:
            await send_agent_telegram(update, "¿Podés ingresar un correo válido, por favor? Debe contener @ y un dominio.")
        return
    elif global_mem.lead_data.stage == "awaiting_phone":
        if user_input:
            global_mem.lead_data.phone = user_input
        global_mem.lead_data.stage = "info"
        if save_lead(global_mem.lead_data):
            logger.info(f"Lead guardado exitosamente para usuario {user_id_str}")
        else:
            logger.warning(f"No se pudo guardar lead para usuario {user_id_str}")
        global_mem.save()
        welcome_msg = (
            "¡Perfecto! 🎉 Ahora puedo ayudarte mejor.\n\n"
            "¿Qué te gustaría aprender sobre Inteligencia Artificial? "
            "Tenemos cursos de IA práctica, prompts, generación de imágenes y más."
        )
        keyboard = create_main_keyboard()
        await send_agent_telegram(update, welcome_msg, keyboard)
        return

    # --- FLUJO NORMAL: NOMBRE, EMAIL, TELÉFONO, ETC. ---
    if global_mem.lead_data.stage == "awaiting_name":
        nombre = user_input.strip()
        if len(nombre) > 1 and all(x.isalpha() or x.isspace() for x in nombre):
            global_mem.lead_data.name = nombre.title()
            global_mem.lead_data.stage = "info"
            global_mem.save()
            await send_agent_telegram(update, f"¡Gracias, {global_mem.lead_data.name}! ¿En qué puedo ayudarte hoy?", create_nav_keyboard(), msg_critico=True)
        else:
            await send_agent_telegram(update, "Por favor, ingresa un nombre válido (solo letras y espacios).", create_nav_keyboard(), msg_critico=True)
        return

    # --- FLUJO DE NOMBRE PREFERIDO ---
    if global_mem.lead_data.stage == "awaiting_preferred_name":
        nombre_preferido = user_input.strip()
        if len(nombre_preferido) > 1 and not any(x in nombre_preferido.lower() for x in ["no", "igual", "como quieras", "da igual", "me da igual"]):
            global_mem.lead_data.name = nombre_preferido.title()
            global_mem.lead_data.stage = "info"
            global_mem.save()
            await send_agent_telegram(update, f"¡Perfecto, {global_mem.lead_data.name}! A partir de ahora me dirigiré a ti así. 😊")
        else:
            nombre_telegram = update.effective_user.first_name if update.effective_user and update.effective_user.first_name else "amigo"
            global_mem.lead_data.name = nombre_telegram
            global_mem.lead_data.stage = "info"
            global_mem.save()
            await send_agent_telegram(update, f"¡Perfecto! Me dirigiré a ti como {global_mem.lead_data.name}.")
        curso_info = get_course_detail(global_mem.lead_data.selected_course)
        if curso_info:
            messages = []
            try:
                with open('imagen_prueba.jpg', 'rb') as img_file:
                    await update.message.reply_photo(img_file)
            except Exception as e:
                logger.warning(f"No se pudo enviar imagen: {e}")
            try:
                with open('pdf_prueba.pdf', 'rb') as pdf_file:
                    await update.message.reply_document(pdf_file)
            except Exception as e:
                logger.warning(f"No se pudo enviar PDF: {e}")
            messages.append(f"{global_mem.lead_data.name}, aquí tienes toda la información detallada y el temario del curso. Si tienes alguna pregunta, ¡estoy para ayudarte en todo momento!")
            resumen = (
                f"*Modalidad:* {curso_info.get('modality', 'No especificado')}\n"
                f"*Duración:* {curso_info.get('total_duration', 'N/A')} horas\n"
                f"*Horario:* {curso_info.get('schedule', 'A consultar')}\n"
                f"*Precio:* {curso_info.get('price_usd', 'N/A')} {curso_info.get('currency', '')}\n"
                f"*Incluye:* {curso_info.get('includes', 'Material, acceso a grabaciones, soporte')}\n"
            )
            messages.append(resumen)
            keyboard = create_contextual_cta_keyboard("course_selected", user_id_str)
            await send_grouped_messages(update, messages, keyboard, msg_critico=True)
        else:
            await send_agent_telegram(update, "¿Sobre qué curso te gustaría saber más?", create_contextual_cta_keyboard("default", user_id_str))
        return

    # --- MENSAJE DE PROCESANDO SI ES NECESARIO ---
    processing_msg = None
    if len(user_input) > 20 or any(word in user_input.lower() for word in ['curso', 'precio', 'módulos', 'comprar', 'promoción']):
        processing_msg = await send_processing_message(update)

    # --- PROCESAMIENTO PRINCIPAL Y RESPUESTA ---
    try:
        bot_reply = process_user_input(user_input, global_mem)
        if global_mem.lead_data.email:
            global_mem.history.append({
                "user_input": user_input,
                "bot_reply": bot_reply,
                "timestamp": time.time()
            })
        global_mem.save()
        # Determinar el tipo de contexto para los CTAs
        context_type = "default"
        if global_mem.lead_data.selected_course:
            context_type = "course_selected"
        if any(word in user_input.lower() for word in ['precio', 'costo', 'cuánto', 'cuanto', 'pagar']):
            context_type = "pricing_inquiry"
        interest_score = get_interest_score(user_id_str) or 0
        if interest_score >= UMBRAL_PROMO:
            context_type = "purchase_intent"
        if interest_score >= 30:
            context_type = "high_interest"
        keyboard = create_contextual_cta_keyboard(context_type, user_id_str)
        await send_agent_telegram(update, bot_reply, keyboard, msg_critico=True)
    except Exception as e:
        logger.error(f"Error procesando mensaje del usuario {user_id_str}: {e}", exc_info=True)
        error_msg = "Lo siento, hubo un problema técnico. ¿Te gustaría que un asesor humano te contacte?"
        await send_agent_telegram(update, error_msg, create_contextual_cta_keyboard("default", user_id_str))

    # --- Interest Score: NEGATIVE ---
    if detect_negative_feedback(user_input):
        update_interest_score(user_id_str, "NEGATIVE", {"text": user_input})
        logger.info(f"NEGATIVE feedback detectado para usuario {user_id_str}")
    # --- Interest Score: READ_VALUE ---
    if hasattr(global_mem.lead_data, 'awaiting_ack') and global_mem.lead_data.awaiting_ack:
        last_ack = getattr(global_mem.lead_data, 'last_ack_time', None)
        if last_ack and (time.time() - last_ack < 600):
            update_interest_score(user_id_str, "READ_VALUE", {})
            logger.info(f"READ_VALUE disparado para usuario {user_id_str}")
        global_mem.lead_data.awaiting_ack = False
        global_mem.save()
    # --- Interest Score: SESSION_90S ---
    check_session_90s(global_mem, time.time())

# --- Lead Score: función para actualizar el nivel de interés ---
def update_lead_score(user_input: str, mem: Memory, last_activity: float):
    score = mem.lead_data.lead_score
    now = time.time()
    # Si el usuario pregunta por precio, promociones, comprar, inscripción
    if any(word in user_input.lower() for word in ["precio", "costo", "descuento", "promoción", "promo", "pagar", "comprar", "inscribir", "inscripción", "oferta"]):
        score += 1
    # Si el usuario muestra objeción
    if detect_objecion(user_input) in ["precio", "duda"]:
        score += 1
    # Si el usuario responde rápido (< 30s desde el último mensaje)
    if now - last_activity < 30:
        score += 1
    # Si el usuario regresa después de 30 minutos
    if now - last_activity > 1800:
        score += 1
    # Si el usuario hace más de 5 preguntas en menos de 10 minutos
    recent_msgs = [h for h in mem.history[-10:] if now - h["timestamp"] < 600]
    if len(recent_msgs) >= 5:
        score += 1
    # Score máximo 10
    score = min(score, 10)
    mem.lead_data.lead_score = score
    mem.save()
    return score

# ==============================
# INTEREST SCORE SYSTEM
# ==============================
EVENT_MAP = {
    "READ_VALUE": 5,
    "CLICK_COURSE": 8,
    "MORE_INFO": 10,
    "QUIZ": 6,
    "PAYMENT": 30,
    "SESSION_90S": 4,
    "INACTIVITY_WEEK": -7,
    "UNSUBSCRIBE": -20,
    "NEGATIVE": -10,
}

def update_interest_score(user_id: str, event: str, meta: Optional[Dict[str, Any]] = None) -> None:
    """
    Actualiza el interest score del usuario en Supabase.
    Suma los puntos del evento y agrega una entrada al log.
    """
    if event not in EVENT_MAP:
        logger.warning(f"Evento desconocido para interest_score: {event}")
        return
    pts = EVENT_MAP[event]
    meta = meta or {}
    url = f"{SUPABASE_URL}/rest/v1/interest_score?user_id=eq.{user_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200 and r.json():
            row = r.json()[0]
            new_score = row.get("score", 0) + pts
            new_log = row.get("log", []) + [{
                "event": event,
                "pts": pts,
                "meta": meta,
                "ts": datetime.utcnow().isoformat()
            }]
            patch_data = {
                "score": new_score,
                "log": new_log,
                "updated_at": datetime.utcnow().isoformat()
            }
            patch_url = f"{SUPABASE_URL}/rest/v1/interest_score?user_id=eq.{user_id}"
            r_patch = requests.patch(patch_url, headers=headers, data=json.dumps(patch_data), timeout=10)
            if r_patch.status_code not in (200, 204):
                logger.warning(f"No se pudo actualizar interest_score: {r_patch.status_code} - {r_patch.text}")
        else:
            # Crear nuevo registro
            insert_data = {
                "user_id": user_id,
                "score": pts,
                "log": [{
                    "event": event,
                    "pts": pts,
                    "meta": meta,
                    "ts": datetime.utcnow().isoformat()
                }],
                "updated_at": datetime.utcnow().isoformat()
            }
            r_post = requests.post(f"{SUPABASE_URL}/rest/v1/interest_score", headers=headers, data=json.dumps(insert_data), timeout=10)
            if r_post.status_code not in (200, 201):
                logger.warning(f"No se pudo crear interest_score: {r_post.status_code} - {r_post.text}")
    except Exception as e:
        logger.error(f"Error actualizando interest_score: {e}")

def get_interest_score(user_id: str) -> Optional[int]:
    """Obtiene el interest score actual del usuario desde Supabase."""
    try:
        url_score = f"{SUPABASE_URL}/rest/v1/interest_score?user_id=eq.{user_id}"
        headers_score = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        r_score = requests.get(url_score, headers=headers_score, timeout=10)
        if r_score.status_code == 200 and r_score.json():
            return r_score.json()[0].get("score", 0)
    except Exception as e:
        logger.warning(f"No se pudo obtener interest_score: {e}")
    return None
# --- Registrar handlers nuevos en main_telegram_bot ---
def main_telegram_bot():
    """Función principal del bot de Telegram con manejo mejorado de errores."""
    logger.info("Iniciando bot de Telegram...")
    
    try:
        application = Application.builder().token(TELEGRAM_API_TOKEN).build()

        # Agregar handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        application.add_handler(PollAnswerHandler(handle_poll_answer))
        try:
            from telegram.ext import MyChatMemberHandler
            application.add_handler(MyChatMemberHandler(handle_my_chat_member))
        except ImportError:
            logger.warning("MyChatMemberHandler no disponible en esta versión de telegram.ext")
        except Exception as e:
            logger.warning(f"Error al registrar MyChatMemberHandler: {e}")
        application.add_handler(CommandHandler("stop", handle_stop))

        logger.info("Bot de Telegram configurado. Listo para iniciar polling.")
        
        # Limpiar memorias antiguas al inicio
        Memory.cleanup_old_memories()
        logger.info("Limpieza de memorias antiguas completada")
        
        # Configurar limpieza periódica de caché
        def cleanup_cache():
            cache.clear_expired()
            logger.debug("Caché limpiado")
        
        # Ejecutar limpieza cada 10 minutos
        import threading
        def periodic_cleanup():
            while True:
                time.sleep(600)  # 10 minutos
                cleanup_cache()
                Memory.cleanup_old_memories()
        
        cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
        cleanup_thread.start()
        
        # Iniciar polling
        logger.info("Iniciando polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error fatal en main_telegram_bot: {e}", exc_info=True)
        raise
    finally:
        logger.info("Bot de Telegram finalizado")

if __name__ == "__main__":
    import sys

    logger.info("Iniciando aplicación principal")
    
    if sys.platform == "win32":
        logger.info("Configurando WindowsSelectorEventLoopPolicy para Windows")
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        main_telegram_bot()
        logger.info("Bot finalizado normalmente")
    except KeyboardInterrupt:
        logger.info("Bot interrumpido por el usuario (Ctrl+C)")
    except Exception as e:
        logger.error(f"Error fatal en la aplicación principal: {e}", exc_info=True)
        sys.exit(1)

# ==============================
# I/O (console, will be renamed/removed)
# ==============================
 
def validar_email(email: str) -> bool:
    patron = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(patron, email) is not None

def validar_telefono(telefono: str) -> bool:
    solo_digitos = re.sub(r"[^0-9]", "", telefono)
    return 10 <= len(solo_digitos) <= 12

# ==============================
# PRIVACY SYSTEM
# ==============================

# ==============================
# MESSAGE GROUPING SYSTEM
# ==============================
async def send_grouped_messages(update: Update, texts: list[str], keyboard=None, msg_critico=False) -> None:
    """
    Envía múltiples mensajes, mostrando botones solo en el último.
    
    Args:
        update: Update object
        texts: Lista de textos a enviar
        keyboard: Teclado a mostrar en el último mensaje
        msg_critico: Si es True, muestra el teclado en todos los mensajes
    """
    if not texts:
        return
    
    # Enviar todos los mensajes excepto el último sin teclado
    for i, text in enumerate(texts[:-1]):
        await send_agent_telegram(update, text, None, msg_critico=False)
        await asyncio.sleep(0.5)  # Pequeña pausa entre mensajes
    
    # Enviar el último mensaje con el teclado
    await send_agent_telegram(update, texts[-1], keyboard, msg_critico=msg_critico)

# ==============================
# ENHANCED CTA SYSTEM
# ==============================


# ==============================
# ENHANCED PROMPT SYSTEM
# ==============================
def get_enhanced_system_prompt() -> str:
    """Retorna el prompt del sistema mejorado con tono cálido y orientado a conversión."""
    return """Eres Brenda, una asistente virtual entusiasta y cercana especializada en cursos de Inteligencia Artificial. Tu objetivo es ayudar a los usuarios a encontrar el curso perfecto para sus necesidades y guiarlos hacia la inscripción.

TONO Y ESTILO:
- Sé entusiasta, cálida y cercana, como una amiga que quiere lo mejor para ellos
- Usa un lenguaje claro y accesible, evita tecnicismos superfluos
- Orienta siempre hacia la acción y la conversión
- Muestra empatía y entiende sus necesidades
- Usa emojis moderadamente para hacer la conversación más amigable

INSTRUCCIONES ESPECÍFICAS:
- Si respondes con varias frases, coloca la pregunta o CTA al final
- Siempre ofrece valor antes de pedir algo
- Ante objeciones, primero valida la preocupación y luego ofrece soluciones
- Cuando hables de precios, enfatiza el valor y las oportunidades
- Si no tienes información específica, ofrece conectar con un asesor humano

CONTEXTO DEL USUARIO:
- Nombre: {name}
- Curso seleccionado: {selected_course}
- Intereses: {interests}
- Etapa: {stage} 

CURSOS DISPONIBLES:
{available_courses}

RESPUESTAS:
- Sé específica y útil
- Ofrece información práctica y accionable
- Si no sabes algo, dilo honestamente y ofrece alternativas
- Siempre termina con una pregunta o sugerencia que invite a la acción
- Mantén las respuestas concisas pero completas

RECUERDA: Tu objetivo es convertir leads en estudiantes satisfechos, no solo responder preguntas."""

# ==============================
# ADVISOR NOTIFICATION SYSTEM
# ==============================
def notify_advisor(action: str, details: str) -> None:
    """Notifica a un asesor sobre una acción específica del usuario."""
    try:
        logger.info(f"Notificación para asesor: {action} - {details}")
        # Aquí puedes implementar la lógica para notificar al asesor
        # Por ejemplo, enviar un mensaje a un canal de Telegram, email, etc.
        # Por ahora solo lo registramos en el log
    except Exception as e:
        logger.error(f"Error notificando al asesor: {e}")


 