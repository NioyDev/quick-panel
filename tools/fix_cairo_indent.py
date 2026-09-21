import glob
import re

on_draw_func = """
    def on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False
"""

for file in glob.glob("/home/nioy/Proyectos/quick-panel/quick-*.py"):
    with open(file, 'r') as f:
        content = f.read()
    
    # Remove all trailing on_draw that were appended at the end incorrectly
    if content.endswith(on_draw_func):
        content = content[:-len(on_draw_func)]
        
    # Also remove any on_draw that was inserted right before if __name__ incorrectly (with double newlines or wrong indent)
    # Actually, it's safer to just regex out the whole on_draw function completely from the file
    content = re.sub(r'\n    def on_draw\(self, widget, cr\):\n        cr\.set_source_rgba\(0, 0, 0, 0\)\n        cr\.set_operator\(cairo\.OPERATOR_SOURCE\)\n        cr\.paint\(\)\n        return False\n', '', content)
    
    # Now, find the class definition and insert it at the very end of the class.
    # The safest way is to find the LAST method before __main__ or EOF
    # Or simply replace `def __init__` with the on_draw method and then __init__
    if "def on_draw" not in content:
        content = content.replace("def __init__(self):", on_draw_func.lstrip("\n") + "\n    def __init__(self):")
        
    with open(file, 'w') as f:
        f.write(content)
    print(f"Fixed indent in {file}")
