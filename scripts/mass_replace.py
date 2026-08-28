import os
import re

# Mapeos de reemplazo
# Orden importante: de lo ms especfico a lo ms general si aplicara
REPLACEMENTS = {
    # Nombres de marca con case exacto o general
    "DemoCorp": "DemoCorp",
    "democorp": "democorp",
    "Democorp": "Democorp",
    
    # Nombres del bot
    "DemoAgent": "DemoAgent",
    "demobot": "demobot",
    "Demobot": "Demobot",
    
    # Archivos especficos que renombraremos (las referencias dentro de archivos)
    "democorp_modulos.md": "modulos_erp.md",
}

def replace_in_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"No se pudo leer {filepath}: {e}")
        return False

    new_content = content
    for old_str, new_str in REPLACEMENTS.items():
        new_content = new_content.replace(old_str, new_str)
        
    if new_content != content:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Modificado: {filepath}")
            return True
        except Exception as e:
            print(f"No se pudo escribir {filepath}: {e}")
    return False

def main():
    skip_dirs = {'.git', '.claude', 'node_modules', '__pycache__', 'venv', 'env'}
    skip_exts = {'.pdf', '.db', '.pyc', '.png', '.jpg'}
    
    modified_count = 0
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in skip_exts:
                continue
            
            filepath = os.path.join(root, file)
            if replace_in_file(filepath):
                modified_count += 1
                
    print(f"\nTotal archivos modificados: {modified_count}")

if __name__ == '__main__':
    main()