import os

files = ['quick-brightness.py', 'quick-calendar.py', 'quick-power.py']
for f in files:
    path = f"/home/nioy/.local/bin/{f}"
    with open(path, 'r') as file:
        content = file.read()
    
    content = content.replace("import sys\n            sys.exit(0)\n        return False", "Gtk.main_quit()\n            return True\n        return False")
            
    with open(path, 'w') as file:
        file.write(content)
