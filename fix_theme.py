import glob
import re

for file in glob.glob("/home/nioy/Proyectos/quick-panel/quick-*.py"):
    with open(file, 'r') as f:
        content = f.read()
    
    # Force window to have no background image (which is what XFCE Greybird theme uses to draw the gray background)
    content = content.replace("window { background-color: transparent; }", "window { background-color: transparent; background-image: none; }")
    
    # Change any background-color: #HEX to background: #HEX to override any background-image from the theme on buttons and boxes
    content = re.sub(r'background-color:\s*(#[0-9a-fA-F]+|transparent|rgba\([^)]+\));', r'background: \1;', content)
    
    with open(file, 'w') as f:
        f.write(content)
    print(f"Fixed theme overriding in {file}")
