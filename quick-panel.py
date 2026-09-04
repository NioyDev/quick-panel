#!/usr/bin/env python3
import gi
import sys
import subprocess
import time
import os
import datetime
import glob
import re
gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Wnck, Gio

PINNED_APPS = [
    "brave-browser.desktop",
    "code.desktop",
    "thunar.desktop",
    "xfce4-terminal.desktop"
]

class QuickPanel(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("QuickPanel")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_accept_focus(False)
        self.set_app_paintable(True)
        
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            
        self.setup_css()
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.main_box.set_name("panel_box")
        self.main_box.set_margin_bottom(8)
        
        # --- CENTER (Launcher & Apps) ---
        self.center_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.center_box.set_halign(Gtk.Align.CENTER)
        self.btn_launcher = Gtk.Button()
        self.btn_launcher.set_name("panel_btn")
        self.btn_launcher.set_can_focus(False)
        self.btn_launcher.connect("clicked", self.on_launcher_clicked)
        self.btn_launcher.add(Gtk.Image.new_from_icon_name("view-app-grid-symbolic", Gtk.IconSize.MENU))
        self.center_box.pack_start(self.btn_launcher, False, False, 4)
        
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_top(4)
        sep.set_margin_bottom(4)
        self.center_box.pack_start(sep, False, False, 0)
        
        self.win_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.scroll.set_propagate_natural_width(True)
        self.scroll.add(self.win_box)
        self.center_box.pack_start(self.scroll, True, True, 4)
        
        self.main_box.pack_start(self.center_box, False, False, 4)
        
        # --- RIGHT SIDE (Indicators) ---
        self.right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        def make_indicator():
            b = Gtk.Button()
            b.set_name("pill_item")
            b.set_can_focus(False)
            return b
            
        self.btn_vol = make_indicator()
        self.icon_vol = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.MENU)
        self.btn_vol.add(self.icon_vol)
        self.btn_vol.connect("clicked", lambda x: subprocess.Popen(["python3", "/home/nioy/.local/bin/quick-volume.py"]))
        self.right_box.pack_start(self.btn_vol, False, False, 0)
        
        self.btn_bright = make_indicator()
        self.btn_bright.add(Gtk.Image.new_from_icon_name("display-brightness-symbolic", Gtk.IconSize.MENU))
        self.btn_bright.connect("clicked", lambda x: subprocess.Popen(["python3", "/home/nioy/.local/bin/quick-brightness.py"]))
        self.right_box.pack_start(self.btn_bright, False, False, 0)
        
        self.btn_wifi = make_indicator()
        self.btn_wifi.add(Gtk.Image.new_from_icon_name("network-wireless-symbolic", Gtk.IconSize.MENU))
        self.btn_wifi.connect("clicked", lambda x: subprocess.Popen(["nm-connection-editor"]))
        self.right_box.pack_start(self.btn_wifi, False, False, 0)
        
        self.btn_bat = make_indicator()
        self.icon_bat = Gtk.Image.new_from_icon_name("battery-good-symbolic", Gtk.IconSize.MENU)
        self.lbl_bat = Gtk.Label()
        box_bat = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box_bat.pack_start(self.icon_bat, False, False, 0)
        box_bat.pack_start(self.lbl_bat, False, False, 0)
        self.btn_bat.add(box_bat)
        self.btn_bat.connect("clicked", lambda x: subprocess.Popen(["xfce4-power-manager-settings"]))
        self.right_box.pack_start(self.btn_bat, False, False, 0)
        
        self.btn_time = make_indicator()
        self.lbl_time = Gtk.Label()
        self.lbl_time.set_name("pill_label")
        self.btn_time.add(self.lbl_time)
        self.btn_time.connect("clicked", lambda x: subprocess.Popen(["python3", "/home/nioy/.local/bin/quick-calendar.py"]))
        self.right_box.pack_start(self.btn_time, False, False, 0)
        
        self.btn_power = make_indicator()
        self.btn_power.add(Gtk.Image.new_from_icon_name("system-shutdown-symbolic", Gtk.IconSize.MENU))
        self.btn_power.connect("clicked", lambda x: subprocess.Popen(["python3", "/home/nioy/.local/bin/quick-power.py"]))
        self.right_box.pack_start(self.btn_power, False, False, 4)
        
        self.main_box.pack_end(self.right_box, False, False, 4)
        
        self.add(self.main_box)
        
        self.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)
        
        self.hide_timer = None
        self.anim_timer = None
        self.current_y = 0
        self.target_y = 0
        self.base_y = 0
        
        self.app_buttons = {}
        self.pinned_info = self.load_pinned_apps()
        
        self.wnck_screen = Wnck.Screen.get_default()
        self.wnck_screen.force_update()
        self.wnck_screen.connect("window-opened", self.on_window_changed)
        self.wnck_screen.connect("window-closed", self.on_window_changed)
        self.wnck_screen.connect("active-window-changed", self.on_active_window_changed)
        
        GLib.idle_add(lambda: self.on_active_window_changed(self.wnck_screen, None) or False)
        GLib.timeout_add(1000, self.enforce_visibility)
        
        GLib.timeout_add_seconds(1, self.update_status)
        self.update_status()
        
        GLib.idle_add(self.refresh_windows)
        GLib.idle_add(self.reposition)
        GLib.timeout_add(500, self.remove_struts)
        
        self.hide_timer = GLib.timeout_add(2000, self.hide_panel)

    def remove_struts(self):
        if self.get_window():
            xid = self.get_window().get_xid()
            subprocess.Popen(['xprop', '-id', str(xid), '-remove', '_NET_WM_STRUT_PARTIAL'])
            subprocess.Popen(['xprop', '-id', str(xid), '-remove', '_NET_WM_STRUT'])
        return False

    def setup_css(self):
        css = b'''
        * { outline: none; font-family: system-ui, sans-serif; }
        window, scrolledwindow, viewport { background-color: transparent; }
        #panel_box {
            background-color: #18181b;
            border-radius: 20px;
            border: 1px solid #27272a;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            padding: 4px;
        }
        #panel_btn, #pill_item {
            background-color: transparent;
            color: #fafafa;
            border: none;
            box-shadow: none;
            border-radius: 12px;
            padding: 4px 10px;
            transition: all 200ms ease-in-out;
        }
        #panel_btn { min-width: 24px; }
        #panel_btn:hover, #pill_item:hover { background-color: #27272a; }
        #panel_btn.running {
            padding: 4px 14px;
            border-bottom: 2px solid #3f3f46;
            background-color: #27272a;
        }
        #panel_btn.active {
            padding: 4px 14px;
            border-bottom: 2px solid #60a5fa;
            background-color: #3f3f46;
        }
        #app_label, #pill_label {
            color: #fafafa;
            font-size: 13px;
            font-weight: 500;
        }
        image { color: #fafafa; }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def load_pinned_apps(self):
        pinned = []
        app_info = Gio.AppInfo.get_all()
        for p in PINNED_APPS:
            for app in app_info:
                if app.get_id() == p:
                    pinned.append({'id': p, 'name': app.get_name(), 'icon': app.get_icon(), 'exec': app.get_executable(), 'app_info': app})
                    break
        return pinned

    def on_mouse_enter(self, widget, event):
        if event.detail == Gdk.NotifyType.INFERIOR: return False
        if self.hide_timer:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = None
        self.show_panel()
        return False
        
    def on_mouse_leave(self, widget, event):
        if event.detail == Gdk.NotifyType.INFERIOR: return False
        self.hide_timer = GLib.timeout_add(2000, self.hide_panel)
        return False
        
    def hide_panel(self):
        self.hide_timer = None
        geometry = Gdk.Display.get_default().get_primary_monitor().get_geometry()
        self.target_y = geometry.height - 2
        self.start_animation()
        return False

    def show_panel(self):
        self.target_y = self.base_y
        self.start_animation()
        
    def start_animation(self):
        if self.anim_timer: GLib.source_remove(self.anim_timer)
        self.anim_timer = GLib.timeout_add(16, self.animate_step)
        
    def animate_step(self):
        x, y = self.get_position()
        diff = self.target_y - y
        if abs(diff) <= 2:
            self.move(x, self.target_y)
            self.current_y = self.target_y
            self.anim_timer = None
            return False
        step = int(diff * 0.2)
        if step == 0: step = 1 if diff > 0 else -1
        new_y = y + step
        self.move(x, new_y)
        self.current_y = new_y
        return True

    def on_launcher_clicked(self, widget):
        subprocess.Popen(["python3", "/home/nioy/.local/bin/quick-launcher.py"])

    def get_window_class(self, win):
        cg = win.get_class_group()
        if cg: return cg.get_name().lower()
        return win.get_name().lower()
        
    def match_pinned_app(self, wm_class):
        for p in self.pinned_info:
            if p['id'].lower().startswith(wm_class) or wm_class in p['id'].lower(): return p['id']
            if "code" in wm_class and "code" in p['id'].lower(): return p['id']
            if "brave" in wm_class and "brave" in p['id'].lower(): return p['id']
            if "terminal" in wm_class and "terminal" in p['id'].lower(): return p['id']
        return None

    def get_clean_name(self, raw_str):
        raw = raw_str.lower()
        if "brave" in raw: return "Brave"
        if "terminal" in raw: return "Terminal"
        if "code" in raw: return "VS Code"
        if "thunar" in raw: return "Archivos"
        if "antigravity" in raw: return "Antigravity"
        if "pinta" in raw: return "Pinta"
        if "steam" in raw: return "Steam"
        return raw.split('-')[0].split('.')[0].capitalize()

    def refresh_windows(self):
        for child in self.win_box.get_children():
            self.win_box.remove(child)
        self.app_buttons.clear()
        
        for p in self.pinned_info:
            btn = Gtk.Button()
            btn.set_name("panel_btn")
            btn.set_can_focus(False)
            icon = p['icon']
            if icon: img = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.MENU)
            else: img = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.MENU)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            box.pack_start(img, False, False, 0)
            lbl = Gtk.Label(label=self.get_clean_name(p['id']))
            lbl.set_name("app_label")
            lbl.set_no_show_all(True)
            lbl.hide()
            box.pack_start(lbl, False, False, 0)
            btn.add(box)
            btn.dock_label = lbl
            btn.dock_is_pinned = True
            btn.dock_app_id = p['id']
            btn.dock_windows = []
            btn.connect("clicked", self.on_app_clicked, p['id'])
            self.app_buttons[p['id']] = btn
            self.win_box.pack_start(btn, False, False, 0)
            
        windows = self.wnck_screen.get_windows()
        for win in windows:
            if win.is_skip_pager() or win.is_skip_tasklist() or win.get_window_type() != Wnck.WindowType.NORMAL:
                continue
            wm_class = self.get_window_class(win)
            matched_id = self.match_pinned_app(wm_class)
            
            if matched_id and matched_id in self.app_buttons:
                self.app_buttons[matched_id].dock_windows.append(win)
            else:
                unpinned_id = "unpinned_" + wm_class
                if unpinned_id not in self.app_buttons:
                    btn = Gtk.Button()
                    btn.set_name("panel_btn")
                    btn.set_can_focus(False)
                    pixbuf = win.get_icon()
                    if pixbuf:
                        try:
                            pixbuf = pixbuf.scale_simple(16, 16, GdkPixbuf.InterpType.BILINEAR)
                            img = Gtk.Image.new_from_pixbuf(pixbuf)
                        except:
                            img = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.MENU)
                    else:
                        img = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.MENU)
                    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                    box.pack_start(img, False, False, 0)
                    lbl = Gtk.Label(label=self.get_clean_name(wm_class))
                    lbl.set_name("app_label")
                    lbl.set_no_show_all(True)
                    lbl.hide()
                    box.pack_start(lbl, False, False, 0)
                    btn.add(box)
                    btn.dock_label = lbl
                    btn.dock_is_pinned = False
                    btn.dock_app_id = unpinned_id
                    btn.dock_windows = [win]
                    btn.connect("clicked", self.on_app_clicked, unpinned_id)
                    self.app_buttons[unpinned_id] = btn
                    self.win_box.pack_start(btn, False, False, 0)
                else:
                    self.app_buttons[unpinned_id].dock_windows.append(win)
                    
        self.update_classes()
        self.win_box.show_all()
        GLib.idle_add(self.reposition)
        
    def update_classes(self):
        active_win = self.wnck_screen.get_active_window()
        active_xid = active_win.get_xid() if active_win else -1
        for app_id, btn in self.app_buttons.items():
            context = btn.get_style_context()
            context.remove_class("running")
            context.remove_class("active")
            if len(btn.dock_windows) > 0:
                btn.dock_label.show()
                if any(w.get_xid() == active_xid for w in btn.dock_windows):
                    context.add_class("active")
                else:
                    context.add_class("running")
            else:
                btn.dock_label.hide()

    def on_app_clicked(self, widget, app_id):
        btn = self.app_buttons[app_id]
        windows = btn.dock_windows
        if len(windows) == 0:
            for p in self.pinned_info:
                if p['id'] == app_id:
                    try: p['app_info'].launch([], None)
                    except: pass
                    break
        else:
            active_win = self.wnck_screen.get_active_window()
            if active_win in windows:
                if len(windows) == 1:
                    active_win.minimize()
                else:
                    idx = windows.index(active_win)
                    windows[(idx + 1) % len(windows)].activate(int(time.time()))
            else:
                windows[0].activate(int(time.time()))

    def update_status(self):
        now = datetime.datetime.now()
        hour12 = now.hour % 12
        if hour12 == 0: hour12 = 12
        ampm = "AM" if now.hour < 12 else "PM"
        self.lbl_time.set_markup(f"<span weight='bold' foreground='#fafafa' size='medium'>{hour12}:{now.strftime('%M')} {ampm}</span>")
        
        try:
            vol_out = subprocess.check_output("amixer sget Master", shell=True).decode('utf-8')
            if "[off]" in vol_out: self.icon_vol.set_from_icon_name("audio-volume-muted-symbolic", Gtk.IconSize.MENU)
            else:
                match = re.search(r"\[([0-9]+)%\]", vol_out)
                if match:
                    vol = int(match.group(1))
                    if vol == 0: icon = "audio-volume-muted-symbolic"
                    elif vol < 33: icon = "audio-volume-low-symbolic"
                    elif vol < 66: icon = "audio-volume-medium-symbolic"
                    else: icon = "audio-volume-high-symbolic"
                    self.icon_vol.set_from_icon_name(icon, Gtk.IconSize.MENU)
        except: pass
        
        try:
            bat_paths = glob.glob("/sys/class/power_supply/BAT*")
            if bat_paths:
                with open(f"{bat_paths[0]}/capacity", "r") as f: pct = int(f.read().strip())
                with open(f"{bat_paths[0]}/status", "r") as f: state = f.read().strip().lower()
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
        except: pass
        return True

    def on_window_changed(self, screen, window):
        if window:
            if window.is_skip_pager() or window.is_skip_tasklist() or window.get_window_type() != Wnck.WindowType.NORMAL:
                return
        self.refresh_windows()

    def should_show_panel(self):
        try:
            display = Gdk.Display.get_default()
            monitor = display.get_primary_monitor()
            m_geom = monitor.get_geometry()
            
            active_win = self.wnck_screen.get_active_window()
            if not active_win: return True
            if active_win.get_window_type() == Wnck.WindowType.DESKTOP: return True
            
            geom = active_win.get_geometry()
            is_borderless = (geom.widthp >= m_geom.width and geom.heightp >= m_geom.height and not active_win.is_maximized())
            if active_win.is_fullscreen() or is_borderless:
                return False
                
            active_app = active_win.get_application()
            if active_app:
                for w in active_app.get_windows():
                    if w == active_win: continue
                    if w.is_fullscreen(): return False
                    w_geom = w.get_geometry()
                    if w_geom.widthp >= m_geom.width and w_geom.heightp >= m_geom.height and not w.is_maximized():
                        return False
            return True
        except:
            return True

    def on_active_window_changed(self, screen, previously_active_window):
        win = screen.get_active_window()
        if not win:
            self.show_panel()
            self.update_classes()
            return
            
        if self.should_show_panel():
            self.show_panel()
        else:
            self.hide_panel()
            
        self.update_classes()

    def enforce_visibility(self):
        if not self.should_show_panel():
            if self.get_mapped(): self.hide()
        else:
            if not self.get_mapped(): self.show_all()
        return True

    def reposition(self):
        geometry = Gdk.Display.get_default().get_primary_monitor().get_geometry()
        
        # Configure width (16px margin on left and right = 32px subtracted)
        target_width = geometry.width - 32
        self.set_size_request(target_width, -1)
        
        width, height = self.get_size()
        x = geometry.x + 16
        self.base_y = geometry.y + geometry.height - height
        
        if self.current_y == 0:
            self.current_y = self.base_y
            self.move(x, self.base_y)
            
        return False

if __name__ == "__main__":
    app = QuickPanel()
    app.show_all()
    Gtk.main()
