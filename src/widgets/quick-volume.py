#!/usr/bin/env python3
import gi
import subprocess
import re
import sys
import os
import signal

try:
    pids = subprocess.check_output(["pgrep", "-f", "quick-volume.py"]).decode().strip().split('\n')
    current_pid = str(os.getpid())
    other_pids = [p for p in pids if p and p != current_pid]
    if other_pids:
        for pid_str in other_pids:
            try:
                os.kill(int(pid_str), signal.SIGKILL)
            except Exception:
                pass
        sys.exit(0)
except Exception:
    pass

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
        if visual:
            self.set_visual(visual)
            
        self.setup_css()
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.main_box.set_name("volume_box")
        
        # --- AUDIO SECTION ---
        # Speaker
        spk_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        spk_icon = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        
        spk_right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.spk_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.spk_scale.set_draw_value(False)
        self.spk_scale.set_size_request(200, -1)
        
        self.spk_combo = Gtk.ComboBoxText()
        self.spk_combo.set_name("device_combo")
        self.spk_combo.connect("changed", self.on_spk_combo_changed)
        
        spk_right_box.pack_start(self.spk_scale, True, True, 0)
        spk_right_box.pack_start(self.spk_combo, False, False, 0)
        
        spk_box.pack_start(spk_icon, False, False, 0)
        spk_box.pack_start(spk_right_box, True, True, 0)
        
        # Mic
        mic_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        mic_icon = Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        
        mic_right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.mic_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.mic_scale.set_draw_value(False)
        self.mic_scale.set_size_request(200, -1)
        
        self.mic_combo = Gtk.ComboBoxText()
        self.mic_combo.set_name("device_combo")
        self.mic_combo.connect("changed", self.on_mic_combo_changed)
        
        mic_right_box.pack_start(self.mic_scale, True, True, 0)
        mic_right_box.pack_start(self.mic_combo, False, False, 0)
        
        mic_box.pack_start(mic_icon, False, False, 0)
        mic_box.pack_start(mic_right_box, True, True, 0)
        
        self.main_box.pack_start(spk_box, False, False, 0)
        self.main_box.pack_start(mic_box, False, False, 0)
        
        self.add(self.main_box)
        
        self.connect("focus-out-event", lambda *args: Gtk.main_quit())
        self.connect("map-event", self.on_map)
        self.connect("unmap-event", self.on_unmap)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self.on_button_press)
        self.connect("key-press-event", self.on_key_press)
        
        self.ignore_spk_combo = True
        self.ignore_mic_combo = True
        
        GLib.idle_add(self.populate_audio)
        GLib.idle_add(self.position_window)

    def populate_audio(self):
        # Audio volumes
        self.spk_scale.set_value(self.get_current_volume("@DEFAULT_SINK@"))
        self.spk_scale.connect("value-changed", self.on_spk_changed)
        self.mic_scale.set_value(self.get_current_volume("@DEFAULT_SOURCE@"))
        self.mic_scale.connect("value-changed", self.on_mic_changed)
        
        # Sinks
        sinks = self.get_pactl_devices("sinks")
        def_sink = self.get_default_device("sink")
        matched_sink = False
        for s in sinks:
            self.spk_combo.append(s['name'], s['description'])
            if s['name'] == def_sink:
                self.spk_combo.set_active_id(s['name'])
                matched_sink = True
        if not matched_sink and sinks:
            self.spk_combo.set_active(0)
                
        # Sources
        sources = self.get_pactl_devices("sources")
        def_source = self.get_default_device("source")
        matched_source = False
        for s in sources:
            if "monitor" in s['name'].lower(): continue
            self.mic_combo.append(s['name'], s['description'])
            if s['name'] == def_source:
                self.mic_combo.set_active_id(s['name'])
                matched_source = True
        if not matched_source and len(self.mic_combo.get_model()) > 0:
            self.mic_combo.set_active(0)
                
        self.ignore_spk_combo = False
        self.ignore_mic_combo = False
        return False

    def get_pactl_devices(self, dev_type):
        try:
            output = subprocess.check_output(f"LC_ALL=C pactl list {dev_type}", shell=True).decode('utf-8', errors='ignore')
            devices = []
            current_dev = {}
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith("Sink #") or line.startswith("Source #"):
                    if current_dev and 'name' in current_dev and 'description' in current_dev:
                        devices.append(current_dev)
                    current_dev = {}
                elif line.startswith("Name: "):
                    current_dev['name'] = line.split("Name: ")[1].strip()
                elif line.startswith("Description: "):
                    current_dev['description'] = line.split("Description: ")[1].strip()
            if current_dev and 'name' in current_dev and 'description' in current_dev:
                devices.append(current_dev)
            return devices
        except: return []

    def get_default_device(self, dev_type):
        try:
            return subprocess.check_output(f"LC_ALL=C pactl get-default-{dev_type}", shell=True).decode('utf-8').strip()
        except: return None

    def get_current_volume(self, device):
        try:
            out = subprocess.check_output(f"LC_ALL=C pactl get-sink-volume {device}" if "SINK" in device else f"LC_ALL=C pactl get-source-volume {device}", shell=True).decode()
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

    def on_spk_combo_changed(self, combo):
        if self.ignore_spk_combo: return
        dev_id = combo.get_active_id()
        if dev_id:
            subprocess.Popen(["pactl", "set-default-sink", dev_id])

    def on_mic_combo_changed(self, combo):
        if self.ignore_mic_combo: return
        dev_id = combo.get_active_id()
        if dev_id:
            subprocess.Popen(["pactl", "set-default-source", dev_id])

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
        #device_combo {
            background: #27272a;
            color: #fafafa;
            border-radius: 8px;
            font-size: 12px;
            border: 1px solid #3f3f46;
        }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def on_map(self, widget, event):
        seat = Gdk.Display.get_default().get_default_seat()
        seat.grab(self.get_window(), Gdk.SeatCapabilities.ALL_POINTING, False, None, None, None)
        return False
        
    def on_unmap(self, widget, event):
        seat = Gdk.Display.get_default().get_default_seat()
        seat.ungrab()
        return False

    def on_button_press(self, widget, event):
        width, height = self.get_size()
        if event.x < 0 or event.x > width or event.y < 0 or event.y > height:
            Gtk.main_quit()
            return True
        return False

if __name__ == "__main__":
    app = QuickVolume()
    app.show_all()
    Gtk.main()
