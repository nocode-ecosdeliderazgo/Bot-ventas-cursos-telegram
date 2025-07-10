# 🤖 SISTEMA DE TESTING AUTOMATIZADO - BOT BRENDA

Este directorio contiene herramientas para automatizar y guiar el testing manual de tu bot Brenda en Telegram.

## 📁 Archivos Incluidos

- **`FLUJOS_VALIDACION_BOT.md`** - Documentación completa de los 3 flujos de testing
- **`simple_tester.py`** - ⭐ **RECOMENDADO** - Testing guiado paso a paso (SIN APIs)
- **`automated_bot_tester.py`** - Testing completamente automatizado (requiere APIs)
- **`get_chat_id.py`** - Utilidad para obtener tu Chat ID de Telegram
- **`results/`** - Carpeta donde se guardan todos los resultados

## 🚀 OPCIÓN 1: TESTING GUIADO (RECOMENDADO)

### Uso Simple Sin APIs

```bash
# Ejecutar el testing guiado
python3 testing_automation/simple_tester.py
```

**¿Qué hace este script?**
- Te guía paso a paso por los 3 flujos de testing
- Te dice exactamente qué mensaje enviar
- Espera 15 segundos después de cada mensaje
- Te permite registrar si funcionó o no
- Guarda los resultados en archivos `.txt` y `.json`

**Ventajas:**
- ✅ No requiere configuración de APIs
- ✅ Fácil de usar
- ✅ Control total sobre el testing
- ✅ Manejo manual de botones
- ✅ Resultados detallados

### Ejemplo de Uso:

1. **Iniciar el script:**
   ```bash
   python3 testing_automation/simple_tester.py
   ```

2. **Seleccionar flujo:**
   ```
   🎯 SELECCIONA EL FLUJO A PROBAR:
   1. 👨‍💼 Explorador Interesado (11 pasos - ~15 min)
   2. 🤔 Escéptico con Objeciones (11 pasos - ~15 min)  
   3. 🚀 Decidido / Automatización (11 pasos - ~15 min)
   
   ➡️ Tu opción (0-3): 1
   ```

3. **Seguir las instrucciones:**
   ```
   📍 PASO 1
   💬 ENVIAR: #Experto_IA_GPT_Gemini #ADSIM_01
   🎯 ESPERADO: Flujo de privacidad → botón aceptar
   
   📱 COPIA Y PEGA en Telegram:
   📋 #Experto_IA_GPT_Gemini #ADSIM_01
   ```

4. **Registrar resultado:**
   ```
   📊 REGISTRAR RESULTADO DEL PASO 1
   ¿Qué pasó después de enviar el mensaje?
   1. ✅ Funcionó como esperado
   2. ⚠️ Funcionó parcialmente
   3. ❌ No funcionó / Error
   4. 🔄 Necesita más tiempo
   
   ➡️ Resultado (1-4): 1
   ```

## 🎯 OPCIÓN 2: TESTING COMPLETAMENTE AUTOMATIZADO

### Requiere Configuración de APIs

**Paso 1: Obtener tu Chat ID**
```bash
python3 testing_automation/get_chat_id.py
```

**Paso 2: Ejecutar testing automatizado**
```bash
python3 testing_automation/automated_bot_tester.py
```

**Ventajas:**
- ✅ Envío automático de mensajes
- ✅ Timing preciso de 15 segundos
- ✅ No necesitas copiar/pegar mensajes

**Desventajas:**
- ❌ Requiere configurar APIs
- ❌ Los botones deben presionarse manualmente
- ❌ Más complejo de configurar

## 📊 Los 3 Flujos de Testing

### FLUJO 1: Usuario Explorador Interesado (11 pasos)
**Perfil:** Profesional curioso que explora opciones
**Herramientas esperadas:**
- `mostrar_syllabus_interactivo`
- `gestionar_objeciones_tiempo`
- `enviar_recursos_gratuitos`
- `mostrar_comparativa_precios`
- `mostrar_garantia_satisfaccion`
- `agendar_demo_personalizada`
- `contactar_asesor_directo`

### FLUJO 2: Usuario Escéptico con Objeciones (11 pasos)
**Perfil:** Profesional desconfiado con muchas objeciones
**Herramientas esperadas:**
- `mostrar_casos_exito_similares`
- `mostrar_social_proof_inteligente`
- `personalizar_propuesta_por_perfil`
- `mostrar_comparativa_competidores`
- `implementar_gamificacion`
- `mostrar_timeline_resultados`
- `personalizar_oferta_por_budget`

### FLUJO 3: Usuario Decidido que busca Automatización (11 pasos)
**Perfil:** Empresario que busca soluciones específicas
**Herramientas esperadas:**
- `detectar_necesidades_automatizacion`
- `mostrar_casos_automatizacion`
- `calcular_roi_personalizado`
- `ofrecer_implementacion_asistida`
- `recomendar_herramientas_ia`
- `conectar_con_comunidad`
- `generar_link_pago_personalizado`

## 📁 Resultados de Testing

Después de cada flujo, se generan dos archivos:

### Archivo de Texto (`.txt`)
```
# REPORTE DE TESTING BOT BRENDA
==================================================

Flujo: FLUJO 1: USUARIO EXPLORADOR INTERESADO
Fecha: 2025-07-09T15:30:00
Total de pasos: 11
Exitosos: 9
Fallidos: 2
Tasa de éxito: 81.8%

## DETALLE POR PASO
------------------------------

### PASO 1 ✅
**Mensaje:** #Experto_IA_GPT_Gemini #ADSIM_01
**Esperado:** Flujo de privacidad → botón aceptar
**Resultado:** Funcionó como esperado
**Observaciones:** Bot respondió inmediatamente con botón
**Timestamp:** 2025-07-09T15:30:15

[... más pasos ...]
```

### Archivo JSON (`.json`)
```json
{
  "flow_number": 1,
  "flow_name": "FLUJO 1: USUARIO EXPLORADOR INTERESADO",
  "execution_date": "2025-07-09T15:30:00",
  "total_steps": 11,
  "successful_steps": 9,
  "failed_steps": 2,
  "results": [
    {
      "step": 1,
      "timestamp": "2025-07-09T15:30:15",
      "message_sent": "#Experto_IA_GPT_Gemini #ADSIM_01",
      "expected": "Flujo de privacidad → botón aceptar",
      "result_status": "success",
      "result_description": "Funcionó como esperado",
      "observations": "Bot respondió inmediatamente con botón",
      "flow": "FLUJO 1: USUARIO EXPLORADOR INTERESADO"
    }
    // ... más resultados
  ]
}
```

## 📋 Checklist de Testing

### Antes de empezar:
- [ ] Bot Brenda está ejecutándose
- [ ] Tienes Telegram abierto con tu bot
- [ ] Has ejecutado los scripts SQL necesarios
- [ ] Variables de entorno configuradas

### Durante el testing:
- [ ] Enviar cada mensaje exactamente como se indica
- [ ] Esperar 15 segundos completos después de cada mensaje
- [ ] Presionar botones cuando sea necesario
- [ ] Observar si las herramientas se activan
- [ ] Registrar el resultado honestamente

### Después del testing:
- [ ] Revisar archivos de resultados
- [ ] Identificar patrones de errores
- [ ] Documentar problemas encontrados
- [ ] Planificar correcciones si es necesario

## 🎯 Qué Validar en Cada Paso

### ✅ Señales de Éxito:
- Bot responde en menos de 15 segundos
- Herramienta específica se activa (aparece en logs)
- Información es real de la base de datos
- No se inventa módulos o precios
- Memoria persiste entre mensajes
- Personalización progresiva funciona

### ❌ Señales de Problema:
- Bot tarda más de 15 segundos en responder
- Herramienta incorrecta se activa
- Información inventada o genérica
- Bot pregunta datos ya conocidos
- Errores en logs
- Respuestas no relacionadas al contexto

## 🔧 Solución de Problemas

### Problema: Script no ejecuta
```bash
# Verificar Python
python3 --version

# Verificar permisos
chmod +x testing_automation/simple_tester.py
```

### Problema: Bot no responde
- ✅ Verificar que el bot esté ejecutándose
- ✅ Comprobar logs del bot: `tail -f bot.log`
- ✅ Verificar conexión a base de datos

### Problema: Herramientas no se activan
- ✅ Revisar logs de OpenAI API
- ✅ Verificar que la clasificación de intenciones funcione
- ✅ Comprobar que agent_tools.py está actualizado

## 📞 Soporte

Si encuentras problemas durante el testing:

1. **Revisa los logs del bot**: `tail -f bot.log`
2. **Consulta los archivos de resultados** generados
3. **Documenta el error específico** con capturas de pantalla
4. **Incluye el contexto completo** (qué mensaje enviaste, qué esperabas, qué pasó)

---

**🎉 ¡Con este sistema podrás validar completamente que tu Bot Brenda funciona al 100%!**