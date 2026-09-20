import glob

for file in glob.glob("/home/nioy/Proyectos/quick-panel/quick-*.py"):
    with open(file, 'r') as f:
        content = f.read()
    
    # Fix the nested CSS bug I introduced
    bad_css = "window {\n        decoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }"
    good_css = "window { background-color: transparent; }\n        decoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }"
    
    new_content = content.replace(bad_css, good_css)
    
    if new_content != content:
        with open(file, 'w') as f:
            f.write(new_content)
        print(f"Fixed {file}")
