import glob
import re

for file in glob.glob("/home/nioy/Proyectos/quick-panel/quick-*.py"):
    with open(file, 'r') as f:
        content = f.read()
    
    # If it already has the decoration fix, skip
    if "decoration:backdrop" in content:
        continue
        
    # Find the CSS block and inject the decoration fix after 'window { background-color: transparent; }' or similar
    # A generic approach: inject it right after any 'window {' block or at the start of the CSS string
    
    # Let's just find the CSS string definition
    # Usually it's css = b''' or CSS = """
    if "css = b'''" in content:
        content = content.replace("css = b'''", "css = b'''\n        decoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }")
    elif 'CSS = """' in content:
        content = content.replace('CSS = """', 'CSS = """\ndecoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }')
    elif "css = b\"\"\"" in content:
        content = content.replace("css = b\"\"\"", "css = b\"\"\"\n        decoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }")
    else:
        print(f"Could not automatically patch {file}")
        
    with open(file, 'w') as f:
        f.write(content)
    print(f"Patched {file}")
