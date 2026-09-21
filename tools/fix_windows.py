import glob
import re

for file in glob.glob("/home/nioy/Proyectos/quick-panel/quick-*.py"):
    with open(file, 'r') as f:
        content = f.read()
    
    # 1. Revert the broken CSS decoration trick
    content = content.replace("decoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }\n", "")
    content = content.replace("        decoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }\n", "")
    content = content.replace("decoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }", "")
    
    content = content.replace("decoration, decoration:backdrop { box-shadow: none; background-color: transparent; }\n", "")
    content = content.replace("        decoration, decoration:backdrop { box-shadow: none; background-color: transparent; }\n", "")
    content = content.replace("decoration, decoration:backdrop { box-shadow: none; background-color: transparent; }", "")
    
    # 2. Convert all TOPLEVEL windows to POPUP to natively fix the shadows
    content = content.replace("super().__init__(type=Gtk.WindowType.TOPLEVEL)", "super().__init__(type=Gtk.WindowType.POPUP)")
    
    with open(file, 'w') as f:
        f.write(content)
    print(f"Fixed {file}")
