# 📚 Documentación Técnica y Funcional del Bot de Ventas

## **Contexto General y Arquitectura**

Este bot de ventas para Telegram está diseñado para asistir, persuadir y guiar a usuarios interesados en cursos de Inteligencia Artificial, combinando una experiencia conversacional cálida con flujos automatizados y persistencia de datos por usuario. El sistema está construido para ser robusto, extensible y fácil de mantener, permitiendo agregar nuevas funcionalidades y flujos de manera sencilla.

### **Estructura de Archivos Clave**
- `agente_ventas_telegram.py`: Archivo principal con toda la lógica del bot, integración con Telegram, manejo de memoria, flujos conversacionales y conexión con APIs externas.
- `plantillas.json`: Contiene plantillas de preguntas y respuestas frecuentes (FAQ) parametrizables, usadas para generar ejemplos y contexto para el modelo de lenguaje.
- `memory_{user_id}.json`: Archivo de memoria individual por usuario, donde se almacena todo el contexto relevante de cada interacción.
- Otros archivos de recursos: `pdf_prueba.pdf`, `imagen_prueba.jpg` (usados para pruebas o envíos de materiales).

---

## **Persistencia y Manejo de Memoria**

### **Memoria por Usuario (`memory_{user_id}.json`)**
- **¿Qué almacena?**
  - Datos personales y de interacción: nombre, email, teléfono, consentimiento de privacidad, intereses, etapa en el embudo de ventas, historial de mensajes, cursos vistos y seleccionados, puntaje de lead, etc.
  - Historial de conversación: últimos 50 mensajes intercambiados.
  - Últimos cursos presentados y timestamp de la última actividad.
- **¿Cómo se usa?**
  - Se carga automáticamente al inicio de cada interacción (si existe y no es muy antiguo).
  - Se actualiza y guarda cada vez que cambia el estado del usuario o se produce una acción relevante.
  - Permite que el usuario retome la conversación exactamente donde la dejó, incluso si el bot se reinicia.
  - Se eliminan memorias antiguas (más de 30 días sin actividad) para mantener el sistema limpio.

### **Plantillas FAQ (`plantillas.json`)**
- Contiene una lista de preguntas frecuentes y respuestas parametrizables.
- Se usa para generar ejemplos de contexto y respuestas automáticas, reemplazando campos dinámicamente según el curso o módulos consultados.
- Permite enriquecer el contexto enviado al modelo de lenguaje y mejorar la experiencia del usuario.

---

## **Resumen de Funcionalidades y Experiencia del Bot**

### **1. Flujo de Privacidad y Consentimiento**
- **Aviso de privacidad obligatorio:**  
  Al primer contacto, el bot muestra un aviso de privacidad con botones (“✅ Acepto y continúo” y “🔒 Ver Aviso Completo”).
- **Persistencia del consentimiento:**  
  Una vez aceptado, el consentimiento se guarda en la memoria del usuario y **no se vuelve a mostrar**, aunque el bot se reinicie.
- **No se reemplazan mensajes:**  
  El aviso de privacidad nunca desaparece; los mensajes nuevos siempre se envían como mensajes adicionales.

---

### **2. Experiencia Conversacional Mejorada**
- **Procesamiento de mensajes libres:**  
  El bot interpreta cualquier mensaje del usuario, incluso si está mal escrito, es ambiguo o tiene errores ortográficos.
- **Reconocimiento de intención con OpenAI:**  
  Si el mensaje no coincide con frases exactas, el bot usa la API de OpenAI para clasificar la intención (por ejemplo: ver cursos, hablar con asesor, ver promociones, etc.).
- **Flujo conversacional cálido y persuasivo:**  
  Las respuestas son cálidas, orientadas a conversión y siempre terminan con una pregunta o CTA.

---

### **3. Botones Funcionales y Menús Contextuales**
- **Botones principales en el saludo y menú:**  
  - 📚 **Ver Cursos** (o “Ver todos los cursos”): muestra la lista completa de cursos disponibles.
  - 🧑‍💼 **Hablar con Asesor**: inicia el flujo para que un asesor humano contacte al usuario.
  - 💰 **Ver Promociones**: muestra las promociones y descuentos activos.
- **Botones contextuales según el flujo:**  
  - Al seleccionar un curso:  
    - 💳 Comprar Curso  
    - 📋 Ver Módulos  
    - 🎯 Aplicar Descuento  
  - En flujos de precio/interés alto:  
    - ✅ Finalizar Compra  
    - 🤝 Negociar Precio  
    - 👨‍💼 Asesor Especializado  
    - 🎯 Reservar Lugar  
    - 📞 Llamada Inmediata  
- **Navegación:**  
  - 🏠 Menú principal  
  - ⬅️ Atrás  
  - ➡️ Siguiente  
  - Los botones de navegación siempre envían nuevos mensajes, nunca editan ni borran los anteriores.

---

### **4. Flujos y Acciones Automáticas**
- **“Ver todos los cursos”**:  
  - El usuario puede escribirlo o presionar el botón, y siempre verá la lista completa de cursos, aunque ya haya seleccionado uno antes.
- **“Hablar con asesor”**:  
  - El usuario puede escribirlo o presionar el botón, y el bot notifica a un asesor humano para que lo contacte.
- **“Ver promociones”**:  
  - El usuario puede escribirlo o presionar el botón, y el bot muestra las promociones activas.
- **Compra simulada:**  
  - Al presionar “Comprar Curso”, el bot muestra un mensaje con un enlace de compra (simulado si no existe en la base), sin mostrar errores técnicos.
- **Manejo de módulos y detalles:**  
  - El usuario puede ver los módulos de cada curso y detalles relevantes.

---

### **5. Robustez y Persistencia**
- **Memoria por usuario:**  
  - Toda la información relevante (nombre, consentimiento, curso seleccionado, historial, etc.) se guarda por usuario y persiste entre reinicios.
- **No se pierden datos ni flujos:**  
  - El usuario puede continuar su experiencia donde la dejó, sin tener que repetir pasos.
- **Manejo de errores:**  
  - El bot responde de forma proactiva y nunca se queda “trabado” en un flujo.

---

### **6. Adaptabilidad y Extensibilidad**
- **Fácil de agregar nuevos botones o flujos:**  
  - Puedes agregar más botones (por ejemplo, “Descargar temario”, “Testimonios”, etc.) y conectar su funcionalidad fácilmente.
- **Reconocimiento de frases complejas:**  
  - El bot entiende frases como “kiero ver los curzos”, “me puedes mostrar los cursos?”, “necesito ablar con un asessor”, etc.

---

## **Resumen de Botones y Acciones Principales**

| Botón / Frase reconocida         | Acción que ejecuta                                              |
|----------------------------------|----------------------------------------------------------------|
| 📚 Ver Cursos / “ver todos los cursos” | Muestra la lista completa de cursos disponibles                |
| 🧑‍💼 Hablar con Asesor / “hablar con asesor” | Notifica a un asesor humano para contactar al usuario          |
| 💰 Ver Promociones / “ver promociones” | Muestra promociones y descuentos activos                       |
| 💳 Comprar Curso                 | Muestra mensaje con enlace de compra (simulado si es necesario) |
| 📋 Ver Módulos                   | Muestra los módulos del curso seleccionado                      |
| 🎯 Aplicar Descuento             | Muestra promociones/códigos de descuento                        |
| 🏠 Menú principal                | Muestra el menú principal con botones contextuales              |
| ⬅️ Atrás / ➡️ Siguiente          | Navegación amigable entre flujos                                |

---

## **¿Qué puedes agregar fácilmente?**
- Más botones contextuales (ej. “Descargar temario”, “Testimonios”, “Ver próximos eventos”).
- Más frases/intenciones reconocidas.
- Flujos personalizados para cada curso o promoción.

---

## **Notas Técnicas para Desarrolladores**
- El código está modularizado y documentado, facilitando la extensión de flujos y la integración con nuevas APIs.
- La lógica de persistencia y manejo de memoria está centralizada en la clase `Memory`.
- El sistema de plantillas permite enriquecer el contexto para el modelo de lenguaje y personalizar respuestas.
- El bot es tolerante a errores y está preparado para manejar entradas ambiguas o inesperadas.
- Se recomienda revisar las funciones principales en `agente_ventas_telegram.py` para entender los puntos de entrada y los flujos de usuario. 