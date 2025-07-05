#!/usr/bin/env python3
"""
Script para eliminar bytes nulos (0x00) de archivos.
Útil para solucionar el error "ValueError: source code string cannot contain null bytes".
"""

import os
import sys

def fix_file(file_path):
    """Elimina bytes nulos de un archivo."""
    try:
        # Leer el archivo en modo binario
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Verificar si hay bytes nulos
        if b'\x00' in content:
            print(f"Encontrados bytes nulos en {file_path}. Limpiando...")
            
            # Eliminar bytes nulos
            cleaned_content = content.replace(b'\x00', b'')
            
            # Guardar el archivo limpio
            with open(file_path, 'wb') as f:
                f.write(cleaned_content)
            
            print(f"Archivo {file_path} limpiado correctamente.")
            return True
        else:
            print(f"No se encontraron bytes nulos en {file_path}.")
            return False
    except Exception as e:
        print(f"Error procesando {file_path}: {e}")
        return False

def process_directory(directory):
    """Procesa todos los archivos Python en un directorio y sus subdirectorios."""
    fixed_files = 0
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_file(file_path):
                    fixed_files += 1
    
    return fixed_files

def main():
    """Función principal."""
    if len(sys.argv) > 1:
        # Procesar archivos específicos
        fixed_files = 0
        for file_path in sys.argv[1:]:
            if os.path.isfile(file_path) and file_path.endswith('.py'):
                if fix_file(file_path):
                    fixed_files += 1
            elif os.path.isdir(file_path):
                fixed_files += process_directory(file_path)
        
        print(f"Total de archivos corregidos: {fixed_files}")
    else:
        # Si no se proporcionan argumentos, procesar directorios clave
        directories = [
            'core/agents',
            'core/handlers',
            'core/services',
            'core/utils'
        ]
        
        fixed_files = 0
        for directory in directories:
            if os.path.isdir(directory):
                print(f"Procesando directorio: {directory}")
                fixed_files += process_directory(directory)
        
        print(f"Total de archivos corregidos: {fixed_files}")

if __name__ == "__main__":
    main()
