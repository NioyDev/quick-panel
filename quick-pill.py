#!/usr/bin/env python3
import subprocess
import os
import psutil
import datetime
import sys
import gi
sys.path.append('/home/nioy/.local/bin')
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from sync_manager import SyncManager

class QuickPill(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_accept_focus(False)
        self.set_app_paintable(True)
        
        # Transparencia
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        self.setup_css()
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.main_box.set_name("pill_box")
        self.main_box.set_margin_bottom(8)
        self.main_box.set_margin_end(16)
        
        def make_btn():
            b = Gtk.Button()
            b.set_name("pill_item")
            b.set_can_focus(False)
            return b
            
        # Volume
        self.btn_vol = make_btn()
        self.icon_vol = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.MENU)
        self.btn_vol.add(self.icon_vol)
        self.btn_vol.connect("clicked", self.on_vol_click)
        self.main_box.pack_start(self.btn_vol, False, False, 0)
        
        # Brightness
        self.btn_bright = make_btn()
        self.icon_bright = Gtk.Image.new_from_icon_name("display-brightness-symbolic", Gtk.IconSize.MENU)
        self.btn_bright.add(self.icon_bright)
        self.btn_bright.connect("clicked", self.on_bright_click)
        self.main_box.pack_start(self.btn_bright, False, False, 0)
        
        # Wifi
        self.btn_wifi = make_btn()
        self.icon_wifi = Gtk.Image.new_from_icon_name("network-wireless-symbolic", Gtk.IconSize.MENU)
        self.btn_wifi.add(self.icon_wifi)
        self.btn_wifi.connect("clicked", self.on_wifi_click)
        self.main_box.pack_start(self.btn_wifi, False, False, 0)
        
        # Battery
        self.btn_bat = make_btn()
        self.icon_bat = Gtk.Image.new_from_icon_name("battery-good-symbolic", Gtk.IconSize.MENU)
        self.lbl_bat = Gtk.Label()
        
        box_bat = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box_bat.pack_start(self.icon_bat, False, False, 0)
        box_bat.pack_start(self.lbl_bat, False, False, 0)
        
        self.btn_bat.add(box_bat)
        self.btn_bat.connect("clicked", self.on_bat_click)
        self.main_box.pack_start(self.btn_bat, False, False, 0)
        
        # Time
        self.btn_time = make_btn()
        self.lbl_time = Gtk.Label()
        self.lbl_time.set_name("pill_label")
        self.btn_time.add(self.lbl_time)
        self.btn_time.connect("clicked", self.on_time_click)
        self.main_box.pack_start(self.btn_time, False, False, 0)
        
        # Power
        self.btn_power = make_btn()
        self.icon_power = Gtk.Image.new_from_icon_name("system-shutdown-symbolic", Gtk.IconSize.MENU)
        self.btn_power.add(self.icon_power)
        self.btn_power.connect("clicked", self.on_power_click)
        self.main_box.pack_start(self.btn_power, False, False, 0)
        
        self.add(self.main_box)
        
        # Auto-hide properties
        self.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)
        self.is_hidden = False
        self.hide_timer = None
        self.anim_timer = None
        self.current_y = 0
        self.target_y = 0
        self.base_y = 0
        self.sync_mgr = SyncManager(self, "quick-pill", "quick-dock")
        
        GLib.timeout_add_seconds(1, self.update_status)
        self.update_status()
        GLib.idle_add(self.reposition)
        GLib.timeout_add(500, self.remove_struts)
        self.setup_fullscreen_detector()

    def setup_fullscreen_detector(self):
        try:
            gi.require_version('Wnck', '3.0')
            from gi.repository import Wnck
            self.wnck_screen = Wnck.Screen.get_default()
            self.wnck_screen.force_update()
            self.wnck_screen.connect("active-window-changed", self.on_active_window_changed)
            
            # Check initial state
            GLib.idle_add(lambda: self.on_active_window_changed(self.wnck_screen, None) or False)
        except Exception as e:
            print("Wnck error:", e)

    def on_active_window_changed(self, screen, previously_active_window):
        win = screen.get_active_window()
        if not win:
            self.show_all()
            return
            
        is_fs = win.is_fullscreen()
        geom = win.get_geometry()
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        m_geom = monitor.get_geometry()
        
        is_borderless = (geom.widthp >= m_geom.width and geom.heightp >= m_geom.height and not win.is_maximized())
        
        if is_fs or is_borderless:
            self.hide()
        else:
            self.show_all()

    def reposition(self):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        width, height = self.get_size()
        
        x = geometry.width - width
        self.base_y = geometry.height - height
        
        if self.current_y == 0:
            self.current_y = self.base_y
            self.move(x, self.base_y)
            # Auto-hide after 2 seconds on startup
            self.hide_timer = GLib.timeout_add(2000, self.hide_dock)
        else:
            self.move(x, self.current_y)
            
        return False

    def show_dock_sync(self):
        if not self.should_show_dock():
            return
        if self.hide_timer:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = None
        self.show_dock()
        
    def hide_dock_sync(self):
        if self.hide_timer:
            GLib.source_remove(self.hide_timer)
        self.hide_timer = GLib.timeout_add(2000, self.hide_dock)

    def on_mouse_enter(self, widget, event):
        if event.detail == Gdk.NotifyType.INFERIOR:
            return False
        self.sync_mgr.notify_enter()
        return False
        
    def on_mouse_leave(self, widget, event):
        if event.detail == Gdk.NotifyType.INFERIOR:
            return False
        self.sync_mgr.notify_leave()
        return False
        
    def hide_dock(self):
        self.hide_timer = None
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        
        self.target_y = geometry.height - 2
        self.start_animation()
        return False
        
    def should_show_dock(self):
        try:
            win = self.wnck_screen.get_active_window()
            if not win: return True
            
            is_fs = win.is_fullscreen()
            geom = win.get_geometry()
            display = Gdk.Display.get_default()
            monitor = display.get_primary_monitor()
            m_geom = monitor.get_geometry()
            is_borderless = (geom.widthp >= m_geom.width and geom.heightp >= m_geom.height and not win.is_maximized())
            return not (is_fs or is_borderless)
        except:
            return True

    def show_dock(self):
        if not self.should_show_dock():
            return
        self.target_y = self.base_y
        self.start_animation()
        
    def start_animation(self):
        if self.anim_timer:
            GLib.source_remove(self.anim_timer)
        self.anim_timer = GLib.timeout_add(16, self.animate_step)

    def animate_step(self):
        width, height = self.get_size()
        x, y = self.get_position()
        
        diff = self.target_y - y
        if abs(diff) <= 2:
            self.move(x, self.target_y)
            self.current_y = self.target_y
            self.anim_timer = None
            return False
            
        step = int(diff * 0.2)
        if step == 0:
            step = 1 if diff > 0 else -1
            
        new_y = y + step
        self.move(x, new_y)
        self.current_y = new_y
        return True

    def on_vol_click(self, widget):
        try: subprocess.Popen(["pavucontrol"])
        except: pass

    def on_bright_click(self, widget):
        try: subprocess.Popen(["python3", "/home/nioy/.local/bin/quick-brightness.py"])
        except: pass

    def on_wifi_click(self, widget):
        try: subprocess.Popen(["nm-connection-editor"])
        except: pass

    def on_bat_click(self, widget):
        try: subprocess.Popen(["xfce4-power-manager-settings"])
        except: pass

    def on_time_click(self, widget):
        try: subprocess.Popen(["orage"])
        except: pass

    def on_power_click(self, widget):
        try: subprocess.Popen(["python3", "/home/nioy/.local/bin/quick-power.py"])
        except: pass

    def update_status(self):
        now = datetime.datetime.now()
        hour12 = now.hour % 12
        if hour12 == 0: hour12 = 12
        ampm = "AM" if now.hour < 12 else "PM"
        time_str = f"{hour12}:{now.strftime('%M')} {ampm}"
        self.lbl_time.set_markup(f"<span weight='bold' foreground='#fafafa' size='medium'>{time_str}</span>")
        
        # Actualizar icono de sonido
        try:
            vol_out = subprocess.check_output("amixer sget Master", shell=True).decode('utf-8')
            if "[off]" in vol_out:
                self.icon_vol.set_from_icon_name("audio-volume-muted-symbolic", Gtk.IconSize.MENU)
            else:
                import re
                match = re.search(r"\[([0-9]+)%\]", vol_out)
                if match:
                    vol = int(match.group(1))
                    if vol == 0:
                        icon = "audio-volume-muted-symbolic"
                    elif vol < 33:
                        icon = "audio-volume-low-symbolic"
                    elif vol < 66:
                        icon = "audio-volume-medium-symbolic"
                    else:
                        icon = "audio-volume-high-symbolic"
                    self.icon_vol.set_from_icon_name(icon, Gtk.IconSize.MENU)
        except Exception:
            pass
        
        # Actualizar icono de bateria
        try:
            import glob
            bat_paths = glob.glob("/sys/class/power_supply/BAT*")
            if bat_paths:
                bat_path = bat_paths[0]
                with open(f"{bat_path}/capacity", "r") as f:
                    pct = int(f.read().strip())
                with open(f"{bat_path}/status", "r") as f:
                    state = f.read().strip().lower()
            else:
                pct = 100
                state = "full"
                    
            if state == "charging":
                if pct < 20: icon_name = "battery-empty-charging-symbolic"
                elif pct < 50: icon_name = "battery-low-charging-symbolic"
                elif pct < 80: icon_name = "battery-good-charging-symbolic"
                else: icon_name = "battery-full-charging-symbolic"
            else:
                if pct < 20: icon_name = "battery-empty-symbolic"
                elif pct < 50: icon_name = "battery-low-symbolic"
                elif pct < 80: icon_name = "battery-good-symbolic"
                else: icon_name = "battery-full-symbolic"
                
            self.icon_bat.set_from_icon_name(icon_name, Gtk.IconSize.MENU)
            self.lbl_bat.set_markup(f"<span weight='bold' foreground='#fafafa' size='medium'>{pct}%</span>")
        except Exception:
            pass
            
        return True
        
    

    def remove_struts(self):
        if self.get_window():
            xid = self.get_window().get_xid()
            import subprocess
            subprocess.Popen(['xprop', '-id', str(xid), '-remove', '_NET_WM_STRUT_PARTIAL'])
            subprocess.Popen(['xprop', '-id', str(xid), '-remove', '_NET_WM_STRUT'])
        return False

    def setup_css(self):
        css = b'''
        * {
            outline: none;
            font-family: system-ui, sans-serif;
        }
        window { 
            background-color: transparent; 
        }
        #pill_box {
            background-color: #18181b; /* Zinc 900 */
            border-radius: 20px;
            border: 1px solid #27272a; /* Zinc 800 */
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            padding: 4px;
        }
        #pill_item {
            background-color: transparent;
            color: #fafafa;
            border-radius: 16px;
            border: none;
            box-shadow: none;
            padding: 4px 10px;
            transition: all 200ms ease;
        }
        #pill_item:hover {
            background-color: #27272a;
        }
        #pill_item:active {
            background-color: #3f3f46;
        }
        #pill_label {
            color: #fafafa;
            font-size: 13px;
            font-weight: 500;
        }
        image {
            color: #fafafa;
        }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

if __name__ == '__main__':
    win = QuickPill()
    win.show_all()
    Gtk.main()
