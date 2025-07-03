# ==============================
# FAQ Y PLANTILLAS DE RESPUESTAS
# ==============================
# Este módulo carga las plantillas de preguntas frecuentes y genera contexto para el LLM.

import os
import json
import logging
logger = logging.getLogger(__name__)

# === Carga de plantillas FAQ desde archivo JSON ===
PLANTILLAS_FAQ = []
try:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    faq_path = os.path.join(base_dir, 'data', 'plantillas.json')
    with open(faq_path, "r", encoding="utf-8") as f:
        PLANTILLAS_FAQ = json.load(f)
except Exception as e:
    print(f"[Error] No se pudo cargar plantillas.json: {e}")

def generar_faq_contexto(course, modules=None):
    """Genera contexto few-shot FAQ usando datos reales del curso y módulos para el LLM."""
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