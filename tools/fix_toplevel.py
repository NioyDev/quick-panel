import glob

for file in glob.glob("/home/nioy/Proyectos/quick-panel/quick-*.py"):
    with open(file, 'r') as f:
        content = f.read()
    
    # Revert POPUP back to TOPLEVEL so windows can receive keyboard focus
    new_content = content.replace("super().__init__(type=Gtk.WindowType.POPUP)", "super().__init__(type=Gtk.WindowType.TOPLEVEL)")
    
    # Inject the CSS shadow removal back in, safely since paintable bug is gone
    if "decoration:backdrop" not in new_content:
        new_content = new_content.replace("window { background-color: transparent; }", "window { background-color: transparent; }\n        decoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }")
        new_content = new_content.replace("window {", "window {\n        decoration, decoration:backdrop { box-shadow: none; background-color: transparent; border: none; }")
    
    if new_content != content:
        with open(file, 'w') as f:
            f.write(new_content)
        print(f"Fixed {file}")
