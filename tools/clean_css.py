import glob
import re

for file in glob.glob("/home/nioy/Proyectos/quick-panel/quick-*.py"):
    with open(file, 'r') as f:
        content = f.read()
    
    # 1. Strip out any garbled window decoration CSS I injected earlier
    # Let's just find the CSS string block and clean it.
    
    # Replace all variations of the messy window block with a single clean one
    content = re.sub(r'window\s*\{\s*background-color:\s*transparent;\s*\}.*?(?=\s*#[a-zA-Z0-9_]+\s*\{|\s*\*\s*\{)', 
                     'window { background-color: transparent; }\n        decoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }\n', 
                     content, flags=re.DOTALL)
    
    # Fix any orphaned closing braces
    content = content.replace("} background-color: transparent; }", "")
    content = content.replace("decoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }\n        decoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }", "decoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }")
    
    with open(file, 'w') as f:
        f.write(content)
    print(f"Cleaned {file}")
