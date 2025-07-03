````markdown
# 1. **Resumen ejecutivo**  
El archivo `agente_ventas_telegram.py` es un monolito de **3 800+ líneas** que mezcla UI, lógica de negocio, persistencia y llamadas a terceros. Mantiene **claves sensibles hard‑codeadas**, combina *asyncio* con I/O síncrono y genera teclados de forma dispersa, lo que provoca inconsistencias (botones faltantes, pantallas “vacías”) y dificulta las pruebas. Además, carece de una **máquina de estados formal**: el flujo depende de múltiples *flags* (`stage`, `privacy_accepted`, etc.) con ramas muertas que complican el mantenimiento :contentReference[oaicite:0]{index=0}.  

El PDF de especificaciones resalta estos dolores y propone separar responsabilidades, ocultar secretos, mejorar la UX con CTAs persistentes y crear un *state‑machine* claro :contentReference[oaicite:1]{index=1}. La refactorización se enfoca en:  

* **Quick Wins** (≤ 2 h): saneamiento de secretos, teclados coherentes y eliminación de duplicidades.  
* **Medio Plazo** (≤ 1 día): desacoplar módulos, crear una *Keyboard Factory*, migrar llamadas a `httpx` asíncrono y asegurar *thread‑safety* en la persistencia.  
* **Estratégico** (> 1 día): introducir una FSM con `transitions`, integrar *Dependency Injection*, mover assets a CDN, cubrir con `pytest` y configurar CI/CD.  

Con ello:  
* Se reduce el riesgo de fuga de datos y se mejora la seguridad.  
* Se acorta el *time‑to‑change* (≈ 50 %) porque cada pieza será testeable aislada.  
* La latencia baja (< 2 s en saludos) al cachear intenciones triviales y usar I/O asíncrono.  
* La UX gana robustez: siempre habrá botones “Inicio” y “Atrás”, y los CTAs se adaptarán al estado real del usuario.  

---

# 2. **Tabla de prioridades**  

| # | Prioridad | Esfuerzo | Archivos/Rutas afectadas |
|---|-----------|----------|--------------------------|
| 1 | **Alta** | Bajo | `agente_ventas_telegram.py` (líneas 120‑160 y 520‑610): extraer API keys a `.env` |
| 2 | **Alta** | Bajo | `agente_ventas_telegram.py` (func. `create_contextual_cta_keyboard`, ~2 450): añadir botón “🏠 Inicio” en todos los contextos |
| 3 | **Media** | Bajo | `agente_ventas_telegram.py` (carga de `plantillas.json`, ~1 280 y ~3 150): cargar una sola vez mediante singleton |
| 4 | **Alta** | Medio | `/bot/handlers/`, `/bot/services/` (nuevo): dividir monolito en módulos *handlers* y *services* |
| 5 | **Media** | Medio | `/bot/factory/keyboard_factory.py` (nuevo): centralizar generación de teclados |
| 6 | **Media** | Medio | `/bot/services/memory.py`: añadir *file‑locking* con `fasteners` |
| 7 | **Media** | Medio | `/bot/services/llm.py`: migrar de `requests` a `httpx.AsyncClient` |
| 8 | **Baja** | Alto | `/bot/fsm/lead_fsm.py` (nuevo): implementar FSM con `transitions` |
| 9 | **Baja** | Alto | `.github/workflows/ci.yml`, `tests/` (nuevo): pytest + ruff + cobertura |

---

# 3. **Guía paso a paso para Cursor AI**  

> **Convención**: Rutas asumen un nuevo paquete raíz `/bot`. Si tu repo aún no lo tiene, créalo y mueve archivos según se indica.

### ➤ **Quick Wins**

1. **Extraer claves a .env**  
   *Ubicación exacta*: `agente_ventas_telegram.py`, líneas 120‑160  
   *Acción*: **extraer** constantes `SUPABASE_KEY`, `OPENAI_API_KEY`, `TELEGRAM_API_TOKEN`, credenciales SMTP, etc. a variables de entorno.  
   *Explicación técnica*: Oculta secretos y facilita despliegues multi‑entorno.  
   *Snippet orientativo* (15 líneas):  
   ```python
   # config/settings.py
   from pydantic import BaseSettings

   class Settings(BaseSettings):
       supabase_url: str
       supabase_key: str
       openai_api_key: str
       telegram_api_token: str
       smtp_username: str
       smtp_password: str

       class Config:
           env_file = ".env"

   settings = Settings()
````

Luego sustituye cada referencia `SUPABASE_KEY` por `settings.supabase_key`, etc.

2. **Botón Inicio universal**
   *Ubicación*: `agente_ventas_telegram.py` → función `create_contextual_cta_keyboard`, \~2 450
   *Acción*: **añadir** fallback “🏠 Volver al inicio” a todos los contextos.
   *Por qué*: Evita que el usuario “se pierda” en sub‑menús.
   *Snippet*:

   ```python
   # Al final de create_contextual_cta_keyboard()
   if not any(btn.callback_data == "cta_inicio" for row in buttons for btn in row):
       buttons.append([InlineKeyboardButton("🏠 Volver al inicio", callback_data="cta_inicio")])
   ```

3. **Cargar plantillas FAQ una sola vez**
   *Ubicación*: dos bloques `with open(... "plantillas.json")` (\~1 280 y \~3 150)
   *Acción*: **eliminar** duplicado y **mover** a `/bot/services/template_loader.py` con patrón singleton.
   *Beneficio*: Menos I/O y riesgo de estado inconsistente.
   *Snippet*:

   ```python
   _faq_cache = None

   def load_faq():
       global _faq_cache
       if _faq_cache is None:
           path = Path(__file__).parent / "plantillas.json"
           _faq_cache = json.loads(path.read_text("utf-8"))
       return _faq_cache
   ```

4. **Sanitizar Markdown/HTML**
   *Ubicación*: `send_agent_telegram`, \~2 150
   *Acción*: **envolver** `msg` con util de sanitización (`html.escape` + regex md).
   *Beneficio*: Previene inyecciones y formateo roto.
   *Snippet*:

   ```python
   from html import escape as _esc

   safe_msg = _esc(msg, quote=False)
   await update.effective_chat.send_message(safe_msg, parse_mode="HTML")
   ```

### ➤ **Medio Plazo**

5. **Descomponer en paquetes**
   *Ubicación*: raíz del proyecto
   *Acción*: **mover** y **renombrar**:

   * `/bot/main.py` – arranque del bot.
   * `/bot/handlers/start.py`, `messages.py`, `callbacks.py`, etc.
   * `/bot/services/supabase.py`, `llm.py`, `memory.py`, `email.py`.
     *Explicación*: Cada módulo tendrá una sola responsabilidad, facilitando tests unitarios.
     *Snippet* (estructura):

   ```
   bot/
   ├─ main.py
   ├─ handlers/
   │  ├─ __init__.py
   │  ├─ start.py
   │  ├─ courses.py
   │  └─ promotions.py
   ├─ services/
   │  ├─ __init__.py
   │  ├─ llm.py
   │  ├─ supabase.py
   │  ├─ memory.py
   │  └─ email.py
   ├─ factory/
   │  └─ keyboard_factory.py
   ├─ fsm/
   │  └─ lead_fsm.py
   └─ config/
      └─ settings.py
   ```

6. **Keyboard Factory centralizada**
   *Ubicación*: `/bot/factory/keyboard_factory.py` (nuevo)
   *Acción*: **extraer** toda la construcción de teclados (`create_*_keyboard`) a una fábrica con métodos descriptivos.
   *Beneficio*: Cambiar o probar teclados sin tocar lógica de negocio.
   *Snippet*:

   ```python
   class KeyboardFactory:
       @staticmethod
       def main() -> InlineKeyboardMarkup: ...
       @staticmethod
       def course(course_id: str) -> InlineKeyboardMarkup: ...
       @staticmethod
       def cta(context: str, score: int) -> InlineKeyboardMarkup: ...
   ```

7. **File‑locking en persistencia**
   *Ubicación*: `/bot/services/memory.py`
   *Acción*: **envolver** `save()` y `load()` con `fasteners.InterProcessLock`.
   *Snippet*:

   ```python
   lock_path = Path(f"mem_{self.lead_data.user_id}.lock")
   with fasteners.InterProcessLock(str(lock_path)):
       # operaciones de lectura/escritura
   ```

8. **Migrar a HTTPX asíncrono**
   *Ubicación*: `/bot/services/llm.py` y `/bot/services/supabase.py`
   *Acción*: **reemplazar** `requests` por `httpx.AsyncClient`, usando *connection pooling* y cancelación.
   *Snippet* (llm):

   ```python
   async with httpx.AsyncClient(timeout=30) as client:
       r = await client.post(url, headers=headers, json=payload)
   ```

9. **Cache de intenciones rápidas**
   *Ubicación*: `/bot/services/llm.py` → función `classify_intent`
   *Acción*: **añadir** `functools.lru_cache(maxsize=1_000)` sobre clasificadores de saludos y frases cortas.
   *Beneficio*: Ahorra tokens y reduce latencia.

### ➤ **Estratégico**

10. **FSM con `transitions`**
    *Ubicación*: `/bot/fsm/lead_fsm.py`
    *Acción*: **crear** clase `LeadFSM` con estados (`anon`, `privacy`, `named`, `browsing`, `interested`, `checkout`, `post_sale`) y transiciones explícitas. Inyectar instancia en cada `ContextTypes.DEFAULT_TYPE` vía *dependency injection*.
    *Snippet* (esqueleto):

    ```python
    from transitions import Machine, State

    class LeadFSM:
        states = [
            State("anon", on_enter="ask_privacy"),
            State("privacy", on_enter="ask_name"),
            State("named", on_enter="show_main_menu"),
            # ...
        ]

        def __init__(self):
            self.machine = Machine(model=self, states=self.states, initial="anon")
            self.machine.add_transition("accept_privacy", "anon", "privacy")
            self.machine.add_transition("set_name", "privacy", "named")
            # ...
    ```

11. **Dependency Injection + Settings**
    *Ubicación*: `/bot/config/settings.py`
    *Acción*: **usar** `pydantic.BaseSettings` y pasar al resto vía constructor (ej. `SupabaseClient(settings)`), evitando *imports circulares*.

12. **CDN para assets**
    *Ubicación*: recursos estáticos (`pdf_prueba.pdf`, `imagen_prueba.jpg`)
    *Acción*: **subir** a bucket/CDN y **reemplazar** envíos de archivo local por links.

13. **CI/CD**
    *Ubicación*: `.github/workflows/ci.yml`
    *Acción*: **crear** pipeline que ejecute `ruff`, `pytest`, `mypy` y *coverage > 80 %* antes de permitir *merge*.

14. **Pruebas unitarias exhaustivas**
    *Ubicación*: `tests/`
    *Acción*: **cubrir**:

    * `memory.save()` (con lock)
    * `keyboard_factory` (estructura correcta)
    * `fsm` (transiciones válidas)
    * `llm.classify_intent` (caché y fallback)

---

# 4. **Validación y pruebas sugeridas**

| Caso                    | Comando / Script                                     | Métrica de aceptación                 |     |
| ----------------------- | ---------------------------------------------------- | ------------------------------------- | --- |
| Secrets fuera de código | \`grep -R "sk-" bot                                  | wc -l\`                               | = 0 |
| FSM transiciones        | `pytest tests/test_fsm.py`                           | 100 % verde                           |     |
| Teclado universal       | `pytest tests/test_keyboards.py::test_inicio_button` | Tecla presente en todos los contextos |     |
| File‑locking            | `pytest tests/test_memory.py::test_concurrent_save`  | Sin `AssertionError` ni corrupción    |     |
| Latencia saludo         | `python tests/bench_latency.py`                      | `< 2 s` promedio                      |     |
| Lint                    | `ruff check bot`                                     | 0 errores críticos                    |     |
| Tipado                  | `mypy bot`                                           | Sin errores                           |     |
| Cobertura               | `pytest --cov=bot`                                   | ≥ 80 %                                |     |

Ejemplo de *pytest* para teclado:

```python
def test_inicio_button():
    factory = KeyboardFactory()
    for ctx in ["default", "course_selected", "pricing_inquiry"]:
        kb = factory.cta(ctx, score=0)
        assert any(b.text.startswith("🏠") for row in kb.inline_keyboard for b in row)
```

---

# 5. **Checklist final**

* [ ] `.env` creado y poblado; variables consumidas vía `Settings`.
* [ ] Todas las referencias a claves hard‑codeadas eliminadas del código.
* [ ] `create_contextual_cta_keyboard` siempre añade “🏠 Volver al inicio”.
* [ ] `plantillas.json` se carga solo una vez mediante `template_loader.load_faq()`.
* [ ] Mensajes sanitizados con `html.escape` antes de enviar.
* [ ] Monolito particionado: `handlers/`, `services/`, `factory/`, `fsm/`.
* [ ] `KeyboardFactory` genera todos los teclados; llamadas antiguas reemplazadas.
* [ ] Persistencia con `fasteners` testea seguro en concurrencia.
* [ ] Todas las llamadas HTTP usan `httpx.AsyncClient`.
* [ ] Cache de intenciones triviales implementado y medido (< 1 token).
* [ ] `LeadFSM` controla el flujo; pruebas de cobertura pasan al 100 %.
* [ ] Assets migrados a CDN y links actualizados.
* [ ] Pipeline CI ejecuta ruff, pytest, mypy y bloquea *merge* si falla.
* [ ] Tiempo medio de respuesta en “Hola” < 2 s según `bench_latency.py`.
* [ ] Conversión a compra instrumentada vía Supabase (campo `stage = checkout`).
* [ ] Documentación interna actualizada (`README.md` + diagrama plantuml).

```
```
