#!/usr/bin/env python3
import gi
import subprocess
import re
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

class QuickVolume(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            
        self.setup_css()
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.main_box.set_name("volume_box")
        
        # Speaker
        spk_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        spk_icon = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        self.spk_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.spk_scale.set_draw_value(False)
        self.spk_scale.set_size_request(200, -1)
        self.spk_scale.set_value(self.get_current_volume("@DEFAULT_SINK@"))
        self.spk_scale.connect("value-changed", self.on_spk_changed)
        spk_box.pack_start(spk_icon, False, False, 0)
        spk_box.pack_start(self.spk_scale, True, True, 0)
        
        # Mic
        mic_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        mic_icon = Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        self.mic_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.mic_scale.set_draw_value(False)
        self.mic_scale.set_size_request(200, -1)
        self.mic_scale.set_value(self.get_current_volume("@DEFAULT_SOURCE@"))
        self.mic_scale.connect("value-changed", self.on_mic_changed)
        mic_box.pack_start(mic_icon, False, False, 0)
        mic_box.pack_start(self.mic_scale, True, True, 0)
        
        self.main_box.pack_start(spk_box, False, False, 0)
        self.main_box.pack_start(mic_box, False, False, 0)
        
        self.add(self.main_box)
        
        self.connect("focus-out-event", lambda *args: Gtk.main_quit())
        self.connect("key-press-event", self.on_key_press)
        
        GLib.idle_add(self.position_window)

    def get_current_volume(self, device):
        try:
            out = subprocess.check_output(f"pactl get-sink-volume {device}" if "SINK" in device else f"pactl get-source-volume {device}", shell=True).decode()
            match = re.search(r"/\s*([0-9]+)%", out)
            if match: return int(match.group(1))
        except: pass
        return 50

    def on_spk_changed(self, scale):
        val = int(scale.get_value())
        subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{val}%"])

    def on_mic_changed(self, scale):
        val = int(scale.get_value())
        subprocess.Popen(["pactl", "set-source-volume", "@DEFAULT_SOURCE@", f"{val}%"])

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

    def position_window(self):
        geometry = Gdk.Display.get_default().get_primary_monitor().get_geometry()
        width, height = self.get_size()
        x = geometry.width - width - 180
        y = geometry.height - height - 60
        self.move(x, y)
        self.present()
        return False

    def setup_css(self):
        css = b'''
        * { outline: none; }
        window { background-color: transparent; }
        #volume_box {
            background-color: #18181b;
            border-radius: 20px;
            border: 1px solid #27272a;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            padding: 24px;
        }
        image { color: #fafafa; }
        scale trough {
            background-color: #3f3f46;
            border-radius: 10px;
            min-height: 6px;
        }
        scale highlight {
            background-color: #ef4444;
            border-radius: 10px;
        }
        scale slider {
            background-color: #fafafa;
            min-width: 16px;
            min-height: 16px;
            border-radius: 50%;
            margin: -5px;
        }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

if __name__ == "__main__":
    app = QuickVolume()
    app.show_all()
    Gtk.main()
