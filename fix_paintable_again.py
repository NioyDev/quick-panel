import glob

for file in glob.glob("/home/nioy/Proyectos/quick-panel/quick-*.py"):
    with open(file, 'r') as f:
        content = f.read()
    
    # Restore set_app_paintable(True) because TOPLEVEL windows need it to render RGBA properly
    # now that we fixed the is_composited() bug that was disabling the RGBA channel
    if "self.set_visual(visual)" in content and "self.set_app_paintable(True)" not in content:
        content = content.replace("self.set_visual(visual)", "self.set_visual(visual)\n            self.set_app_paintable(True)")
    
    with open(file, 'w') as f:
        f.write(content)
    print(f"Fixed {file}")
