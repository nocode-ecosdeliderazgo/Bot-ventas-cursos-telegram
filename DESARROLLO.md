# 🚀 Guía de Desarrollo - Bot de Ventas

## 📋 Configuración Automática del Entorno

Este proyecto está configurado para activar automáticamente el entorno virtual en Cursor/VSCode.

### ✅ Lo que ya está configurado:

1. **Entorno virtual**: `venv/` en la raíz del proyecto
2. **Configuración de VSCode/Cursor**: `.vscode/settings.json`
3. **Tareas automáticas**: `.vscode/tasks.json`
4. **Configuración de debug**: `.vscode/launch.json`
5. **Script de activación**: `activate_env.ps1`

---

## 🎯 Cómo usar el entorno automático

### **Opción 1: Terminal Integrada (Recomendado)**
1. Abre una **nueva terminal** en Cursor/VSCode
2. El entorno virtual se activará automáticamente
3. Verás `(venv)` en el prompt

### **Opción 2: Tareas de VSCode/Cursor**
- **Ctrl+Shift+P** → "Tasks: Run Task" → Selecciona:
  - `Activar Entorno Virtual`
  - `Instalar Dependencias`
  - `Ejecutar Bot`
  - `Ejecutar Tests`

### **Opción 3: Debug/Launch**
- **F5** o **Ctrl+Shift+D** → Selecciona:
  - `Ejecutar Bot de Ventas`
  - `Ejecutar Tests`

### **Opción 4: Script manual**
```powershell
.\activate_env.ps1
```

---

## 🔧 Comandos útiles

### **Activar entorno manualmente:**
```powershell
.\venv\Scripts\Activate.ps1
```

### **Instalar dependencias:**
```powershell
pip install -r requirements.txt
```

### **Ejecutar el bot:**
```powershell
python agente_ventas_telegram.py
```

### **Ejecutar tests:**
```powershell
python test_imports.py
```

### **Verificar entorno:**
```powershell
python --version
pip list
```

---

## 📁 Estructura del proyecto

```
Bot_ventas/
├── 🤖 agente_ventas_telegram.py    # Archivo principal
├── 🔧 .vscode/                     # Configuración de Cursor/VSCode
│   ├── settings.json              # Configuración automática
│   ├── tasks.json                 # Tareas predefinidas
│   └── launch.json                # Configuración de debug
├── 🐍 venv/                       # Entorno virtual
├── 📦 requirements.txt            # Dependencias
├── 🚀 activate_env.ps1            # Script de activación
└── 📝 DESARROLLO.md               # Esta guía
```

---

## ⚠️ Solución de problemas

### **Si no se activa automáticamente:**
1. Verifica que tienes permisos de PowerShell:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

2. Cierra y vuelve a abrir Cursor/VSCode

3. Abre una nueva terminal integrada

### **Si las dependencias no se instalan:**
```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### **Si hay errores de importación:**
1. Verifica que el entorno está activado: `(venv)` en el prompt
2. Ejecuta: `python test_imports.py`
3. Si hay errores, reinstala dependencias

---

## 🎉 ¡Listo para desarrollar!

Con esta configuración, cada vez que abras el proyecto en Cursor/VSCode:
- ✅ El entorno virtual se activará automáticamente
- ✅ Tendrás acceso a todas las dependencias
- ✅ Podrás ejecutar el bot directamente
- ✅ Los tests funcionarán correctamente

**¡Disfruta programando tu bot de ventas! 🚀** 