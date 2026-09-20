#!/usr/bin/env python3
import gi
import subprocess
import threading
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

class QuickBluetooth(Gtk.Window):
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
        self.main_box.set_name("bluetooth_box")
        
        # --- BLUETOOTH SECTION ---
        bt_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bt_icon = Gtk.Image.new_from_icon_name("bluetooth-active-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        bt_label = Gtk.Label(label="Bluetooth")
        bt_label.set_name("bt_label")
        bt_label.set_halign(Gtk.Align.START)
        
        self.bt_switch = Gtk.Switch()
        self.bt_switch.set_valign(Gtk.Align.CENTER)
        self.bt_switch.connect("notify::active", self.on_bt_switch_toggled)
        
        bt_settings = Gtk.Button()
        bt_settings.add(Gtk.Image.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.MENU))
        bt_settings.connect("clicked", lambda x: self.open_bt_settings())
        bt_settings.set_name("bt_settings_btn")
        
        bt_header.pack_start(bt_icon, False, False, 0)
        bt_header.pack_start(bt_label, True, True, 0)
        bt_header.pack_start(self.bt_switch, False, False, 0)
        bt_header.pack_start(bt_settings, False, False, 0)
        
        self.main_box.pack_start(bt_header, False, False, 0)
        
        # Scrolled window for bluetooth devices
        self.bt_scroll = Gtk.ScrolledWindow()
        self.bt_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.bt_scroll.set_min_content_height(100)
        self.bt_scroll.set_max_content_height(300)
        
        self.bt_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.bt_scroll.add(self.bt_list_box)
        self.main_box.pack_start(self.bt_scroll, True, True, 0)
        
        self.add(self.main_box)
        
        self.connect("focus-out-event", lambda *args: Gtk.main_quit())
        self.connect("map-event", self.on_map)
        self.connect("unmap-event", self.on_unmap)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self.on_button_press)
        self.connect("key-press-event", self.on_key_press)
        
        self.ignore_bt_switch = True
        GLib.idle_add(self.populate_bt)
        GLib.idle_add(self.position_window)

    def populate_bt(self):
        for child in self.bt_list_box.get_children():
            self.bt_list_box.remove(child)
            
        try:
            bt_out = subprocess.check_output("LC_ALL=C bluetoothctl show", shell=True).decode()
            is_powered = "Powered: yes" in bt_out
            self.ignore_bt_switch = True
            self.bt_switch.set_active(is_powered)
            self.ignore_bt_switch = False
        except: pass
        
        bt_devices = self.get_bt_devices()
        for dev in bt_devices:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lbl = Gtk.Label(label=dev['name'])
            lbl.set_halign(Gtk.Align.START)
            btn = Gtk.Button()
            btn.set_name("bt_dev_btn")
            if dev['connected']:
                btn.set_label("Desconectar")
                btn.connect("clicked", self.on_bt_disconnect, dev['mac'])
                lbl.set_markup(f"<b>{dev['name']}</b> (Conectado)")
            else:
                btn.set_label("Conectar")
                btn.connect("clicked", self.on_bt_connect, dev['mac'])
            
            row.pack_start(lbl, True, True, 0)
            row.pack_start(btn, False, False, 0)
            self.bt_list_box.pack_start(row, False, False, 0)
            
        self.bt_list_box.show_all()
        return False

    def get_connected_bt(self):
        try:
            out = subprocess.check_output("LC_ALL=C bluetoothctl devices Connected", shell=True).decode()
            return [line.split(" ")[1] for line in out.split('\n') if line.startswith("Device ")]
        except: return []

    def get_bt_devices(self):
        connected_macs = self.get_connected_bt()
        try:
            out = subprocess.check_output("LC_ALL=C bluetoothctl devices", shell=True).decode()
            devices = []
            for line in out.split('\n'):
                if line.startswith("Device "):
                    parts = line.split(" ", 2)
                    if len(parts) == 3:
                        devices.append({'mac': parts[1], 'name': parts[2], 'connected': parts[1] in connected_macs})
            return devices
        except: return []

    def on_bt_switch_toggled(self, switch, gparam):
        if self.ignore_bt_switch: return
        state = switch.get_active()
        cmd_arg = "on" if state else "off"
        subprocess.Popen(["bluetoothctl", "power", cmd_arg])
        GLib.timeout_add(1000, self.populate_bt)
        
    def on_bt_connect(self, btn, mac):
        btn.set_label("...")
        def worker():
            subprocess.run(["bluetoothctl", "connect", mac])
            GLib.idle_add(self.populate_bt)
        threading.Thread(target=worker).start()
        
    def on_bt_disconnect(self, btn, mac):
        btn.set_label("...")
        def worker():
            subprocess.run(["bluetoothctl", "disconnect", mac])
            GLib.idle_add(self.populate_bt)
        threading.Thread(target=worker).start()
        
    def open_bt_settings(self):
        subprocess.Popen(["blueman-manager"])
        Gtk.main_quit()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

    def position_window(self):
        geometry = Gdk.Display.get_default().get_primary_monitor().get_geometry()
        width, height = self.get_size()
        x = geometry.width - width - 240 # Shift slightly left from volume
        y = geometry.height - height - 60
        self.move(x, y)
        self.present()
        return False

    def setup_css(self):
        css = b'''
        * { outline: none; }
        window { background-color: transparent; }
        #bluetooth_box {
            background-color: #18181b;
            border-radius: 20px;
            border: 1px solid #27272a;
            padding: 24px;
        }
        image { color: #fafafa; }
        #bt_label {
            color: #fafafa;
            font-size: 14px;
            font-weight: bold;
        }
        #bt_settings_btn {
            background-color: transparent;
            color: #fafafa;
            border: none;
            box-shadow: none;
            border-radius: 12px;
        }
        #bt_settings_btn:hover { background-color: #27272a; }
        #bt_dev_btn {
            background-color: #3f3f46;
            color: #fafafa;
            border: none;
            border-radius: 8px;
            font-size: 12px;
            padding: 2px 8px;
        }
        #bt_dev_btn:hover { background-color: #52525b; }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

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
            Gtk.main_quit()
            return True
        return False

if __name__ == "__main__":
    app = QuickBluetooth()
    app.show_all()
    Gtk.main()
