#!/usr/bin/env python3
"""
Análisis de datos del curso basado en archivos SQL.
Identifica información real disponible vs lo que inventa el agente.
"""

import re
import json
from datetime import datetime

# ID del curso que mapea #CURSO_IA_CHATGPT
COURSE_ID = 'a392bf83-4908-4807-89a9-95d0acc807c9'

def analyze_course_from_sql():
    """Analiza la información real del curso desde los archivos SQL."""
    print("🔍 ANÁLISIS DEL CURSO DESDE BASE DE DATOS")
    print("=" * 60)
    print(f"🎯 Curso ID: {COURSE_ID}")
    print(f"🔗 Mapeo: #CURSO_IA_CHATGPT → {COURSE_ID}")
    
    # Leer archivo de cursos
    try:
        with open('/home/gael/proyectos/ventas/Bot-ventas-cursos-telegram/database/sql/courses_rows.sql', 'r', encoding='utf-8') as f:
            courses_sql = f.read()
        
        # Buscar el curso específico
        course_pattern = rf"INSERT INTO.*?'{COURSE_ID}'.*?VALUES.*?\((.*?)\);"
        match = re.search(course_pattern, courses_sql, re.DOTALL)
        
        if match:
            course_data = match.group(1)
            # Dividir por comas, pero respetando comillas
            values = parse_sql_values(course_data)
            
            course_info = {
                'id': values[0].strip("'"),
                'name': values[1].strip("'"),
                'short_description': values[2].strip("'"),
                'long_description': values[3].strip("'"),
                'total_duration': values[4].strip("'"),
                'price_usd': values[5].strip("'"),
                'currency': values[6].strip("'"),
                'level': values[9].strip("'"),
                'category': values[10].strip("'"),
                'tools_used': values[20].strip("'"),
                'schedule': values[21].strip("'"),
                'prerequisites': values[27].strip("'"),
                'requirements': values[28].strip("'"),
            }
            
            print_course_details(course_info)
            return course_info
        else:
            print("❌ No se encontró el curso en el archivo SQL")
            return None
            
    except Exception as e:
        print(f"❌ Error leyendo archivo SQL: {e}")
        return None

def parse_sql_values(values_string):
    """Parsea los valores de un INSERT SQL de manera básica."""
    # Esta es una implementación simplificada
    # En un caso real usarías un parser SQL apropiado
    values = []
    current_value = ""
    in_quotes = False
    i = 0
    
    while i < len(values_string):
        char = values_string[i]
        
        if char == "'" and (i == 0 or values_string[i-1] != '\\'):
            in_quotes = not in_quotes
            current_value += char
        elif char == ',' and not in_quotes:
            values.append(current_value.strip())
            current_value = ""
        else:
            current_value += char
        i += 1
    
    if current_value.strip():
        values.append(current_value.strip())
    
    return values

def print_course_details(course_info):
    """Imprime los detalles del curso de manera organizada."""
    print("\n📚 INFORMACIÓN REAL DEL CURSO")
    print("-" * 50)
    
    print(f"📖 Nombre: {course_info['name']}")
    print(f"💰 Precio: ${course_info['price_usd']} {course_info['currency']}")
    print(f"⏱️ Duración: {course_info['total_duration']}")
    print(f"📊 Nivel: {course_info['level']}")
    print(f"🏷️ Categoría: {course_info['category']}")
    print(f"🗓️ Horario: {course_info['schedule']}")
    
    print(f"\n📝 Descripción corta:")
    print(f"   {course_info['short_description']}")
    
    print(f"\n🛠️ Herramientas mencionadas:")
    tools = course_info['tools_used'].strip('{}').replace('"', '').split(',')
    for tool in tools:
        print(f"   • {tool.strip()}")
    
    print(f"\n📋 Prerrequisitos:")
    prereqs = course_info['prerequisites'].strip('{}').replace('"', '').split(',')
    for prereq in prereqs:
        print(f"   • {prereq.strip()}")

def extract_modules_from_description(long_description):
    """Extrae los módulos reales de la descripción larga."""
    print("\n🎓 MÓDULOS REALES IDENTIFICADOS")
    print("-" * 50)
    
    # Buscar patrones de módulos en la descripción
    module_patterns = [
        r'(\d+)\.\s*([^:]+):([^\.]+)',  # Patrón: "1. Nombre: Descripción"
        r'(\w+[^:]+):\s*([^\.]+)',      # Patrón: "Nombre: Descripción"
    ]
    
    modules_found = []
    
    # Dividir por párrafos para mejor análisis
    paragraphs = long_description.split('\n\n')
    
    for paragraph in paragraphs:
        if 'módulo' in paragraph.lower() or 'module' in paragraph.lower():
            print(f"📍 Párrafo con módulos encontrado:")
            print(f"   {paragraph[:200]}...")
            
            # Buscar líneas que empiecen con número o nombre seguido de ":"
            lines = paragraph.split('\n')
            for line in lines:
                if ':' in line and (line.strip()[0].isdigit() or any(word in line.lower() for word in ['chatgpt', 'documento', 'imagen', 'proyecto'])):
                    modules_found.append(line.strip())
    
    if modules_found:
        print(f"\n✅ Módulos identificados ({len(modules_found)}):")
        for i, module in enumerate(modules_found, 1):
            print(f"   {i}. {module}")
    else:
        print("❌ No se encontraron módulos estructurados en la descripción")
        
        # Buscar menciones de contenido temático
        content_keywords = ['chatgpt', 'documento', 'imagen', 'proyecto', 'automatización', 'prompt']
        print(f"\n🔍 Contenido temático mencionado:")
        for keyword in content_keywords:
            if keyword.lower() in long_description.lower():
                print(f"   ✓ {keyword.capitalize()}")
    
    return modules_found

def analyze_bonuses():
    """Analiza los bonos disponibles para el curso."""
    print(f"\n🎁 BONOS DISPONIBLES PARA EL CURSO")
    print("-" * 50)
    
    try:
        with open('/home/gael/proyectos/ventas/Bot-ventas-cursos-telegram/database/sql/limited_time_bonuses_rows.sql', 'r', encoding='utf-8') as f:
            bonuses_sql = f.read()
        
        # Buscar bonos para nuestro curso
        bonus_pattern = rf"'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'{COURSE_ID}'"
        matches = re.findall(bonus_pattern, bonuses_sql)
        
        if matches:
            print(f"✅ Se encontraron {len(matches)} bonos:")
            for i, match in enumerate(matches, 1):
                name = match[1]
                description = match[2]
                value = match[4]
                expires = match[5]
                print(f"   {i}. {name}")
                print(f"      💰 Valor: ${value}")
                print(f"      📅 Expira: {expires}")
                print(f"      📝 {description}")
                print()
        else:
            print("❌ No se encontraron bonos para este curso")
            
    except Exception as e:
        print(f"❌ Error leyendo bonos: {e}")

def analyze_career_benefits():
    """Analiza cómo el curso puede beneficiar a diferentes carreras."""
    print(f"\n💼 ANÁLISIS PARA DIFERENTES CARRERAS")
    print("=" * 60)
    
    # Basado en la información REAL del curso
    real_content = {
        "nombre": "Curso de Inteligencia Artificial para tu día a día profesional desde cero (con ChatGPT e imágenes)",
        "herramientas": ["ChatGPT", "Midjourney", "DALL-E", "Canva"],
        "duracion": "12 horas",
        "precio": "$120 USD",
        "nivel": "Beginner",
        "temas_principales": [
            "ChatGPT como asistente en tareas diarias",
            "Creación de documentos profesionales",
            "Generación de imágenes con IA",
            "Proyecto personal integrado"
        ]
    }
    
    careers = {
        "Marketing Digital": {
            "beneficios_reales": [
                "Automatizar creación de contenido para redes sociales usando ChatGPT",
                "Generar imágenes profesionales para campañas con DALL-E y Midjourney",
                "Crear copys persuasivos y optimizados para diferentes plataformas",
                "Desarrollar presentaciones de marketing más impactantes"
            ],
            "aplicacion_practica": "El módulo de generación de imágenes + ChatGPT permite crear campañas completas en minutos"
        },
        "Ingeniería en Ciencia de Datos": {
            "beneficios_reales": [
                "Automatizar documentación técnica de proyectos usando ChatGPT",
                "Generar visualizaciones y diagramas explicativos con IA",
                "Crear presentaciones de resultados más comprensibles para stakeholders",
                "Optimizar comunicación de hallazgos técnicos"
            ],
            "aplicacion_practica": "Módulo de documentos profesionales ayuda a comunicar análisis complejos de manera clara"
        },
        "Administración de Empresas": {
            "beneficios_reales": [
                "Automatizar reportes ejecutivos y análisis empresariales",
                "Crear presentaciones profesionales para juntas directivas",
                "Generar contenido para comunicación interna y externa",
                "Optimizar procesos de toma de decisiones con asistencia IA"
            ],
            "aplicacion_practica": "Proyecto integrado permite implementar IA en procesos administrativos reales"
        }
    }
    
    for career, analysis in careers.items():
        print(f"\n🎯 {career.upper()}")
        print(f"   💡 Beneficios específicos:")
        for benefit in analysis["beneficios_reales"]:
            print(f"     • {benefit}")
        print(f"   🔧 Aplicación práctica:")
        print(f"     → {analysis['aplicacion_practica']}")

def compare_with_agent_response():
    """Compara la información real vs lo que el agente inventó."""
    print(f"\n🚨 COMPARACIÓN: REAL vs INVENTADO POR EL AGENTE")
    print("=" * 60)
    
    print("❌ LO QUE EL AGENTE INVENTÓ:")
    invented_modules = [
        "La IA como Pilar del Liderazgo Estratégico",
        "Foresight y Análisis Predictivo Aumentado por IA", 
        "Optimización de Decisiones y Modelado de Escenarios",
        "Liderazgo Adaptativo y Agilidad Organizacional",
        "Ética, Gobernanza y Legado del Liderazgo"
    ]
    
    for module in invented_modules:
        print(f"   • {module}")
    
    print("\n✅ LO QUE EXISTE REALMENTE:")
    real_modules = [
        "ChatGPT como asistente en tareas diarias",
        "Creación de documentos profesionales con ChatGPT",
        "Generación de imágenes con IA (DALL·E)",
        "Proyecto personal integrado"
    ]
    
    for module in real_modules:
        print(f"   • {module}")
    
    print(f"\n🔍 DIAGNÓSTICO:")
    print(f"   • El agente inventó módulos de LIDERAZGO que NO existen")
    print(f"   • El curso real es de IA PRÁCTICA para uso diario")
    print(f"   • Nivel: Beginner (no Ejecutivo-Estratégico)")
    print(f"   • Enfoque: Herramientas prácticas, no liderazgo empresarial")

def main():
    """Función principal del análisis."""
    print("🚀 ANÁLISIS COMPLETO DEL CURSO REAL")
    print(f"⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Analizar información del curso
    course_info = analyze_course_from_sql()
    
    if course_info:
        # 2. Extraer módulos de la descripción
        modules = extract_modules_from_description(course_info.get('long_description', ''))
        
        # 3. Analizar bonos
        analyze_bonuses()
        
        # 4. Análisis para carreras
        analyze_career_benefits()
        
        # 5. Comparar con lo inventado
        compare_with_agent_response()
        
        print(f"\n📊 CONCLUSIONES")
        print("=" * 60)
        print("✅ El curso SÍ existe en la base de datos")
        print("✅ La información básica es accesible (nombre, precio, duración)")
        print("⚠️ Los módulos específicos están en la descripción, no en tabla separada")
        print("❌ El agente inventó módulos completamente diferentes")
        print("🔧 SOLUCIÓN: El agente debe leer la descripción larga del curso")
        
    else:
        print("❌ No se pudo acceder a la información del curso")
    
    print(f"\n🎉 ANÁLISIS COMPLETADO")

if __name__ == "__main__":
    main()