import glob

for file in glob.glob("/home/nioy/Proyectos/quick-panel/quick-*.py"):
    with open(file, 'r') as f:
        content = f.read()
    
    # Remove the buggy set_app_paintable call
    new_content = content.replace("        self.set_app_paintable(True)\n", "")
    new_content = new_content.replace("        self.set_app_paintable(True)", "")
    
    if new_content != content:
        with open(file, 'w') as f:
            f.write(new_content)
        print(f"Fixed {file}")
