# ==============================
# FUNCIONES UTILITARIAS Y VALIDADORES
# ==============================
# Este módulo contiene validadores y helpers puros para el bot.

import re
import asyncio

def validar_email(email: str) -> bool:
    """Valida si el email tiene un formato correcto."""
    patron = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(patron, email) is not None

def validar_telefono(telefono: str) -> bool:
    """Valida si el teléfono tiene entre 10 y 12 dígitos."""
    solo_digitos = re.sub(r"[^0-9]", "", telefono)
    return 10 <= len(solo_digitos) <= 12

def detect_negative_feedback(user_input: str) -> bool:
    """Detecta si el input contiene feedback negativo por palabras clave."""
    negative_keywords = [
        "no me gustó", "no me gusto", "malo", "pésimo", "pesimo", "no sirve", "no funciona", "molesto", "spam", "demasiado caro", "engaño", "fraude"
    ]
    return any(kw in user_input.lower() for kw in negative_keywords)

async def send_grouped_messages(send_func, update, texts: list[str], keyboard=None, msg_critico=False) -> None:
    """Envía múltiples mensajes, mostrando botones solo en el último mensaje."""
    if not texts:
        return
    for text in texts[:-1]:
        await send_func(update, text, None, msg_critico=False)
        await asyncio.sleep(0.5)
    await send_func(update, texts[-1], keyboard, msg_critico=msg_critico)
