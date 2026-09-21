import glob

for file in glob.glob("/home/nioy/Proyectos/quick-panel/quick-*.py"):
    with open(file, 'r') as f:
        content = f.read()
    
    # Remove the overly strict screen.is_composited() check which causes the black boxes
    new_content = content.replace("if visual and screen.is_composited():", "if visual:")
    new_content = new_content.replace("if visual and self.get_screen().is_composited():", "if visual:")
    
    if new_content != content:
        with open(file, 'w') as f:
            f.write(new_content)
        print(f"Fixed {file}")
