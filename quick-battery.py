#!/usr/bin/env python3
import gi
import os
import subprocess

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

CSS = """
window {
    background-color: transparent;
}
decoration, decoration:backdrop {
    box-shadow: none;
    background-color: transparent;
}
#main_box {
    background-color: #18181b;
    border-radius: 20px;
    border: 1px solid #27272a;
    padding: 24px;
}
.title-label {
    font-size: 16px;
    font-weight: bold;
    color: #ffffff;
}
.metric-value {
    font-size: 14px;
    font-weight: bold;
    color: #e4e4e7;
}
.metric-label {
    font-size: 11px;
    color: #a1a1aa;
}
.progress-bar {
    min-height: 8px;
    border-radius: 4px;
    background-color: alpha(#ffffff, 0.1);
}
.progress-bar trough {
    border-radius: 4px;
    background-color: transparent;
}
.progress-bar progress {
    border-radius: 4px;
    background-image: linear-gradient(to right, #10b981, #34d399);
}
.btn-profile {
    background-color: alpha(#ffffff, 0.05);
    border-radius: 8px;
    padding: 8px;
    border: 1px solid transparent;
}
.btn-profile:hover {
    background-color: alpha(#ffffff, 0.1);
}
.btn-profile:checked {
    background-color: alpha(#3b82f6, 0.2);
    border: 1px solid #3b82f6;
}
* { outline: none; }
"""

class QuickBattery(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_default_size(320, -1)
        
        screen = Gdk.Screen.get_default()
        monitor = screen.get_monitor_geometry(screen.get_primary_monitor())
        self.move(monitor.width - 340, monitor.height - 450)
        
        self.set_decorated(False)
        
        # Activar fondo transparente (Glassmorphism)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        
        self.provider = Gtk.CssProvider()
        self.provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), 
            self.provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        self.connect("map-event", self.on_map)
        self.connect("unmap-event", self.on_unmap)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self.on_button_press)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.main_box.set_name("main_box")
        
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.icon_bat = Gtk.Image.new_from_icon_name("battery-full-symbolic", Gtk.IconSize.MENU)
        self.icon_bat.set_pixel_size(24)
        self.lbl_title = Gtk.Label(label="Batería")
        self.lbl_title.get_style_context().add_class("title-label")
        header.pack_start(self.icon_bat, False, False, 0)
        header.pack_start(self.lbl_title, False, False, 0)
        self.main_box.pack_start(header, False, False, 0)
        
        self.progress = Gtk.ProgressBar()
        self.progress.get_style_context().add_class("progress-bar")
        self.progress.set_fraction(0.0)
        self.main_box.pack_start(self.progress, False, False, 0)
        
        self.lbl_status = Gtk.Label(label="Calculando...")
        self.lbl_status.set_halign(Gtk.Align.START)
        self.main_box.pack_start(self.lbl_status, False, False, 0)
        
        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(24)
        self.grid.set_row_spacing(12)
        self.main_box.pack_start(self.grid, False, False, 8)
        
        lbl_prof = Gtk.Label(label="Rendimiento")
        lbl_prof.set_halign(Gtk.Align.START)
        lbl_prof.get_style_context().add_class("title-label")
        self.main_box.pack_start(lbl_prof, False, False, 0)
        
        self.prof_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.main_box.pack_start(self.prof_box, False, False, 0)
        
        self.add(self.main_box)
        self.update_data()
        self.show_all()
        
    def add_metric(self, row, col, label, value_id):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_v = Gtk.Label(label="-")
        lbl_v.set_halign(Gtk.Align.START)
        lbl_v.get_style_context().add_class("metric-value")
        setattr(self, value_id, lbl_v)
        
        lbl_l = Gtk.Label(label=label)
        lbl_l.set_halign(Gtk.Align.START)
        lbl_l.get_style_context().add_class("metric-label")
        
        box.pack_start(lbl_v, False, False, 0)
        box.pack_start(lbl_l, False, False, 0)
        self.grid.attach(box, col, row, 1, 1)

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
        
    def read_sysfs(self, node):
        try:
            with open(f"/sys/class/power_supply/BAT0/{node}", "r") as f:
                return f.read().strip()
        except:
            return None

    def update_data(self):
        self.add_metric(0, 0, "Salud", "val_health")
        self.add_metric(0, 1, "Consumo", "val_power")
        self.add_metric(1, 0, "Temperatura", "val_temp")
        self.add_metric(1, 1, "Tiempo", "val_time")
        
        status = self.read_sysfs("status")
        cap = self.read_sysfs("capacity")
        
        volt = self.read_sysfs("voltage_now")
        curr = self.read_sysfs("current_now")
        
        full_des = self.read_sysfs("charge_full_design") or self.read_sysfs("energy_full_design")
        full_now = self.read_sysfs("charge_full") or self.read_sysfs("energy_full")
        charge_now = self.read_sysfs("charge_now") or self.read_sysfs("energy_now")
        temp = self.read_sysfs("temp")
        
        if cap:
            cap_int = int(cap)
            self.progress.set_fraction(cap_int / 100.0)
            self.lbl_title.set_markup(f"<b>Batería {cap}%</b>")
            
            ctx = self.progress.get_style_context()
            if cap_int <= 20:
                css = b".progress-bar progress { background-image: none; background-color: #ef4444; }"
            else:
                css = b".progress-bar progress { background-image: linear-gradient(to right, #10b981, #34d399); }"
            prv = Gtk.CssProvider()
            prv.load_from_data(css)
            ctx.add_provider(prv, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            
        if status:
            if status == "Charging": s_text = "<span foreground='#10b981'>⚡ Cargando</span>"
            elif status == "Discharging": s_text = "<span foreground='#eab308'>🔋 Descargando</span>"
            elif status == "Full": s_text = "<span foreground='#3b82f6'>✅ Completamente cargada</span>"
            else: s_text = status
            self.lbl_status.set_markup(s_text)
            
        if full_des and full_now:
            h = (float(full_now) / float(full_des)) * 100
            self.val_health.set_text(f"{h:.1f}%")
            if h < 50: self.val_health.set_markup(f"<span foreground='#ef4444'>{h:.1f}% (Degradada)</span>")
            
        watts = 0
        if volt and curr:
            watts = (float(volt) / 1e6) * (float(curr) / 1e6)
            self.val_power.set_text(f"{watts:.1f} W")
            
        if temp:
            t = float(temp) / 10.0
            self.val_temp.set_text(f"{t:.1f} °C")
            
        if charge_now and curr and float(curr) > 0:
            if status == "Charging":
                rem = float(full_now) - float(charge_now)
            else:
                rem = float(charge_now)
            hrs = rem / float(curr)
            mins = int(hrs * 60)
            hh = mins // 60
            mm = mins % 60
            self.val_time.set_text(f"{hh}h {mm}m")
        else:
            self.val_time.set_text("Calculando...")
            
        self.setup_profiles()
        
    def setup_profiles(self):
        try:
            out = subprocess.check_output(["powerprofilesctl", "list"]).decode()
            current = "balanced"
            try:
                curr_out = subprocess.check_output(["powerprofilesctl", "get"]).decode().strip()
                if curr_out: current = curr_out
            except: pass
            
            profiles = [
                ("power-saver", "Ahorro", "battery-good-symbolic"),
                ("balanced", "Balance", "speedometer-symbolic"),
                ("performance", "Máximo", "weather-clear-symbolic")
            ]
            
            for pid, label, icon in profiles:
                if pid in out:
                    btn = Gtk.ToggleButton()
                    btn.set_active(pid == current)
                    btn.get_style_context().add_class("btn-profile")
                    
                    b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                    b.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU), False, False, 0)
                    b.pack_start(Gtk.Label(label=label), False, False, 0)
                    btn.add(b)
                    
                    btn.connect("toggled", self.on_prof_toggled, pid)
                    self.prof_box.pack_start(btn, True, True, 0)
        except Exception as e:
            lbl = Gtk.Label(label="No se detectó powerprofilesctl")
            lbl.get_style_context().add_class("metric-label")
            self.prof_box.pack_start(lbl, False, False, 0)
            
    def on_prof_toggled(self, btn, pid):
        if btn.get_active():
            for child in self.prof_box.get_children():
                if child != btn and isinstance(child, Gtk.ToggleButton):
                    child.handler_block_by_func(self.on_prof_toggled)
                    child.set_active(False)
                    child.handler_unblock_by_func(self.on_prof_toggled)
            try:
                subprocess.run(["powerprofilesctl", "set", pid])
            except: pass

if __name__ == "__main__":
    app = QuickBattery()
    Gtk.main()
