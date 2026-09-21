import glob
import re

for file in glob.glob("/home/nioy/Proyectos/quick-panel/quick-*.py"):
    with open(file, 'r') as f:
        content = f.read()
    
    # 1. Add import cairo if not exists
    if "import cairo" not in content:
        content = content.replace("import subprocess", "import subprocess\nimport cairo")
        # In case subprocess is not there
        if "import cairo" not in content:
            content = content.replace("import gi\n", "import gi\nimport cairo\n")

    # 2. Add self.connect("draw", self.on_draw) to __init__
    if 'self.connect("draw", self.on_draw)' not in content:
        content = content.replace("self.setup_css()", "self.setup_css()\n        self.connect(\"draw\", self.on_draw)")
        
    # 3. Add on_draw function at the end of the class
    if "def on_draw(self, widget, cr):" not in content:
        on_draw_func = """
    def on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False
"""
        # Insert before if __name__ == '__main__':
        if "if __name__ == '__main__':" in content:
            content = content.replace("if __name__ == '__main__':", on_draw_func + "\nif __name__ == '__main__':")
        else:
            # For scripts without __main__, like unified ones maybe, just append to the end
            content += on_draw_func
            
    with open(file, 'w') as f:
        f.write(content)
    print(f"Injected Cairo in {file}")
