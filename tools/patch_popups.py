import os, sys

files = ['quick-volume.py', 'quick-brightness.py', 'quick-calendar.py', 'quick-power.py']
grab_code = """
    def on_map(self, widget, event):
        seat = Gdk.Display.get_default().get_default_seat()
        seat.grab(self.get_window(), Gdk.SeatCapabilities.ALL_POINTING, True, None, None, None)
        return False
        
    def on_unmap(self, widget, event):
        seat = Gdk.Display.get_default().get_default_seat()
        seat.ungrab()
        return False

    def on_button_press(self, widget, event):
        width, height = self.get_size()
        if event.x < 0 or event.x > width or event.y < 0 or event.y > height:
            import sys
            sys.exit(0)
        return False
"""

for f in files:
    path = f"/home/nioy/.local/bin/{f}"
    with open(path, 'r') as file:
        content = file.read()
    
    if "on_map" not in content:
        # We need to inject the connect signals into __init__
        # Find where focus-out-event is connected, and add our new events below it
        for line in content.split('\n'):
            if "focus-out-event" in line:
                indent = line.split("self.connect")[0]
                new_connects = f"""{line}
{indent}self.connect("map-event", self.on_map)
{indent}self.connect("unmap-event", self.on_unmap)
{indent}self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
{indent}self.connect("button-press-event", self.on_button_press)"""
                content = content.replace(line, new_connects)
                break
                
        # Now inject the methods at the end of the class (before def main or if __name__)
        # We find "if __name__ == "__main__":"
        idx = content.find("if __name__ == ")
        if idx != -1:
            content = content[:idx] + grab_code + "\n" + content[idx:]
            
        with open(path, 'w') as file:
            file.write(content)
