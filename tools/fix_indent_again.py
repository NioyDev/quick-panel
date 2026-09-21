import glob
import re

good_on_draw = """    def on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False

    def __init__(self):"""

for file in glob.glob("/home/nioy/Proyectos/quick-panel/quick-*.py"):
    with open(file, 'r') as f:
        content = f.read()
    
    # regex to match any weirdly indented on_draw block immediately preceding def __init__(self):
    # This regex is robust
    content = re.sub(r'\s*def on_draw\(self, widget, cr\):\s*cr\.set_source_rgba\(0, 0, 0, 0\)\s*cr\.set_operator\(cairo\.OPERATOR_SOURCE\)\s*cr\.paint\(\)\s*return False\s*def __init__\(self\):', good_on_draw, content)
    
    with open(file, 'w') as f:
        f.write(content)
    print(f"Fixed {file}")
