import os

code = """#!/usr/bin/env python3
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

CATEGORIES = {
    "Todas": "",
    "Internet": "Network;WebBrowser;Email;",
    "Juegos": "Game;",
    "Oficina": "Office;",
    "Multimedia": "AudioVideo;Audio;Video;Graphics;",
    "Sistema": "System;Settings;Utility;"
}

class PopupManager:
    def __init__(self):
        self.active_popup = None
        self.timeout_id = None
        self.last_close_time = 0
        self.popups = {}
        
    def init_popups(self):
        self.popups['volume'] = QuickVolume(self)
        self.popups['brightness'] = QuickBrightness(self)
        self.popups['calendar'] = QuickCalendar(self)
        self.popups['power'] = QuickPower(self)
        self.popups['launcher'] = QuickLauncher(self)

    def close_active(self):
        if self.active_popup:
            self.active_popup.hide()
            self.active_popup = None
            self.last_close_time = time.time()
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
            self.timeout_id = None

    def toggle(self, popup_name):
        # Prevent reopen if toggle button was clicked and caused focus-out
        if time.time() - self.last_close_time < 0.15:
            return
            
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
            self.timeout_id = None

        if self.active_popup and self.active_popup != self.popups[popup_name]:
            self.active_popup.hide()
            
        target = self.popups[popup_name]
        if target.get_visible():
            target.hide()
            self.active_popup = None
            self.last_close_time = time.time()
        else:
            if hasattr(target, 'refresh_state'):
                target.refresh_state()
            target.show_all()
            target.present()
            self.active_popup = target
            self.timeout_id = GLib.timeout_add_seconds(60, self.auto_close)

    def reset_timer(self):
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
        if self.active_popup:
            self.timeout_id = GLib.timeout_add_seconds(60, self.auto_close)

    def auto_close(self):
        if self.active_popup:
            self.active_popup.hide()
            self.active_popup = None
            self.last_close_time = time.time()
        self.timeout_id = None
        return False


class BasePopup(Gtk.Window):
    def __init__(self, manager, **kwargs):
        super().__init__(type=Gtk.WindowType.POPUP, **kwargs)
        self.manager = manager
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            
        self.connect("focus-out-event", self.on_focus_out)
        self.connect("key-press-event", self.on_key_press)
        
    def on_focus_out(self, widget, event):
        self.manager.close_active()
        return False
        
    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.manager.close_active()
        else:
            self.manager.reset_timer()
        return False


class QuickVolume(BasePopup):
    def __init__(self, manager):
        super().__init__(manager)
        self.setup_css()
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.main_box.set_name("volume_box")
        
        spk_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        spk_icon = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        self.spk_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.spk_scale.set_draw_value(False)
        self.spk_scale.set_size_request(200, -1)
        self.spk_scale.connect("value-changed", self.on_spk_changed)
        spk_box.pack_start(spk_icon, False, False, 0)
        spk_box.pack_start(self.spk_scale, True, True, 0)
        
        mic_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        mic_icon = Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        self.mic_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.mic_scale.set_draw_value(False)
        self.mic_scale.set_size_request(200, -1)
        self.mic_scale.connect("value-changed", self.on_mic_changed)
        mic_box.pack_start(mic_icon, False, False, 0)
        mic_box.pack_start(self.mic_scale, True, True, 0)
        
        self.main_box.pack_start(spk_box, False, False, 0)
        self.main_box.pack_start(mic_box, False, False, 0)
        
        self.add(self.main_box)
        GLib.idle_add(self.position_window)

    def refresh_state(self):
        self.spk_scale.set_value(self.get_current_volume("@DEFAULT_SINK@"))
        self.mic_scale.set_value(self.get_current_volume("@DEFAULT_SOURCE@"))

    def get_current_volume(self, device):
        try:
            out = subprocess.check_output(f"pactl get-sink-volume {device}" if "SINK" in device else f"pactl get-source-volume {device}", shell=True).decode()
            match = re.search(r"/\s*([0-9]+)%", out)
            if match: return int(match.group(1))
        except: pass
        return 50

    def on_spk_changed(self, scale):
        self.manager.reset_timer()
        val = int(scale.get_value())
        subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{val}%"])

    def on_mic_changed(self, scale):
        self.manager.reset_timer()
        val = int(scale.get_value())
        subprocess.Popen(["pactl", "set-source-volume", "@DEFAULT_SOURCE@", f"{val}%"])

    def position_window(self):
        geometry = Gdk.Display.get_default().get_primary_monitor().get_geometry()
        width, height = self.get_size()
        x = geometry.width - width - 180
        y = geometry.height - height - 60
        self.move(x, y)
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
        scale trough { background-color: #3f3f46; border-radius: 10px; min-height: 6px; }
        scale highlight { background-color: #ef4444; border-radius: 10px; }
        scale slider { background-color: #fafafa; min-width: 16px; min-height: 16px; border-radius: 50%; margin: -5px; }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


class QuickBrightness(BasePopup):
    def __init__(self, manager):
        super().__init__(manager)
        self.setup_css()
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        self.main_box.set_name("bright_box")
        
        icon = Gtk.Image.new_from_icon_name("display-brightness-symbolic", Gtk.IconSize.DND)
        self.main_box.pack_start(icon, False, False, 0)
        
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 5, 100, 5)
        self.scale.set_name("bright_scale")
        self.scale.set_draw_value(False)
        self.scale.set_hexpand(True)
        self.scale.connect("value-changed", self.on_scale_changed)
        
        self.main_box.pack_start(self.scale, True, True, 0)
        self.add(self.main_box)
        GLib.idle_add(self.position_window)

    def refresh_state(self):
        try:
            curr = float(subprocess.check_output(["brightnessctl", "get"]).decode().strip())
            m = float(subprocess.check_output(["brightnessctl", "max"]).decode().strip())
            pct = int((curr / m) * 100)
            self.scale.set_value(pct)
        except:
            self.scale.set_value(100)

    def on_scale_changed(self, scale):
        self.manager.reset_timer()
        val = int(scale.get_value())
        subprocess.Popen(["brightnessctl", "set", f"{val}%"])

    def position_window(self):
        geometry = Gdk.Display.get_default().get_primary_monitor().get_geometry()
        width, height = self.get_size()
        x = geometry.width - width - 240
        y = geometry.height - height - 60
        self.move(x, y)
        return False

    def setup_css(self):
        css = b'''
        window { background-color: transparent; }
        #bright_box {
            background-color: #18181b;
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 24px;
        }
        scale trough { background-color: rgba(255, 255, 255, 0.2); border-radius: 10px; min-height: 8px; }
        scale highlight { background-color: #fafafa; border-radius: 10px; }
        scale slider { min-width: 16px; min-height: 16px; background-color: #fafafa; border-radius: 50%; }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


class QuickCalendar(BasePopup):
    def __init__(self, manager):
        super().__init__(manager)
        self.setup_css()
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.main_box.set_name("cal_box")
        
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self.lbl_time = Gtk.Label()
        self.lbl_time.set_name("time_label")
        self.lbl_time.set_halign(Gtk.Align.START)
        
        self.lbl_date = Gtk.Label()
        self.lbl_date.set_name("date_label")
        self.lbl_date.set_halign(Gtk.Align.END)
        
        header_box.pack_start(self.lbl_time, True, True, 0)
        header_box.pack_start(self.lbl_date, False, False, 0)
        self.main_box.pack_start(header_box, False, False, 0)
        
        self.calendar = Gtk.Calendar()
        self.calendar.set_name("calendar_grid")
        self.main_box.pack_start(self.calendar, True, True, 0)
        
        self.add(self.main_box)
        GLib.timeout_add_seconds(1, self.update_time)
        GLib.idle_add(self.position_window)

    def refresh_state(self):
        self.update_time()

    def update_time(self):
        now = datetime.datetime.now()
        hour12 = now.hour % 12
        if hour12 == 0: hour12 = 12
        ampm = "AM" if now.hour < 12 else "PM"
        self.lbl_time.set_markup(f"<span weight='bold' size='24000'>{hour12}:{now.strftime('%M')} {ampm}</span>")
        self.lbl_date.set_markup(f"<span weight='bold' size='14000'>{now.strftime('%m/%d')}</span>")
        return True

    def position_window(self):
        geometry = Gdk.Display.get_default().get_primary_monitor().get_geometry()
        width, height = self.get_size()
        x = geometry.width - width - 100
        y = geometry.height - height - 60
        self.move(x, y)
        return False

    def setup_css(self):
        css = b'''
        * { outline: none; color: #fafafa; }
        window { background-color: transparent; }
        #cal_box {
            background-color: #18181b;
            border-radius: 20px;
            border: 1px solid #27272a;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            padding: 24px;
        }
        calendar { background-color: #18181b; color: #fafafa; }
        calendar:selected { background-color: #ef4444; color: #ffffff; border-radius: 4px; }
        #time_label { color: #fafafa; }
        #date_label { color: #a1a1aa; }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


class QuickPower(BasePopup):
    def __init__(self, manager):
        super().__init__(manager)
        self.setup_css()
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_box.set_name("power_box")
        
        lbl_title = Gtk.Label(label="Menú de Energía")
        lbl_title.set_markup("<span weight='bold' foreground='#fafafa' size='x-large'>Opciones del Sistema</span>")
        main_box.pack_start(lbl_title, False, False, 10)
        
        grid = Gtk.Grid(column_spacing=20, row_spacing=20)
        grid.set_halign(Gtk.Align.CENTER)
        
        btn_power = self.make_action_btn("system-shutdown-symbolic", "Apagar", "systemctl poweroff")
        btn_restart = self.make_action_btn("view-refresh-symbolic", "Reiniciar", "systemctl reboot")
        btn_logout = self.make_action_btn("system-log-out-symbolic", "Cerrar Sesión", "pkill xfce4-session")
        btn_user = self.make_action_btn("system-users-symbolic", "Cambiar Perfil", "dm-tool switch-to-greeter")
        
        grid.attach(btn_power, 0, 0, 1, 1)
        grid.attach(btn_restart, 1, 0, 1, 1)
        grid.attach(btn_logout, 0, 1, 1, 1)
        grid.attach(btn_user, 1, 1, 1, 1)
        
        main_box.pack_start(grid, False, False, 0)
        self.add(main_box)
        GLib.idle_add(self.position_window)

    def make_action_btn(self, icon_name, label_text, cmd):
        btn = Gtk.Button()
        btn.set_name("power_btn")
        btn.set_can_focus(False)
        btn.set_size_request(140, 140)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_valign(Gtk.Align.CENTER)
        
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
        icon.set_pixel_size(48)
        lbl = Gtk.Label(label=label_text)
        
        vbox.pack_start(icon, False, False, 0)
        vbox.pack_start(lbl, False, False, 0)
        btn.add(vbox)
        
        btn.connect("clicked", lambda w: self.run_command(cmd))
        return btn

    def run_command(self, cmd):
        subprocess.Popen(cmd, shell=True)
        self.manager.close_active()

    def position_window(self):
        geometry = Gdk.Display.get_default().get_primary_monitor().get_geometry()
        width, height = self.get_size()
        x = geometry.x + (geometry.width - width) // 2
        y = geometry.y + (geometry.height - height) // 2
        self.move(x, y)
        return False

    def setup_css(self):
        css = b'''
        window { background-color: transparent; }
        #power_box {
            background-color: #18181b;
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 30px;
        }
        #power_btn {
            background-color: #27272a;
            border-radius: 16px;
            border: 1px solid transparent;
            color: #fafafa;
        }
        #power_btn:hover {
            background-color: rgba(255, 255, 255, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.3);
            transition: all 0.2s ease;
        }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


class QuickLauncher(BasePopup):
    def __init__(self, manager):
        super().__init__(manager)
        self.set_default_size(650, 500)
        self.setup_css()
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.main_box.set_name("launcher_box")
        self.add(self.main_box)
        
        self.search = Gtk.SearchEntry()
        self.search.set_name("launcher_search")
        self.search.set_placeholder_text("Buscar aplicaciones...")
        self.search.connect("search-changed", self.on_filter_changed)
        self.search.set_margin_top(20)
        self.search.set_margin_start(20)
        self.search.set_margin_end(20)
        self.main_box.pack_start(self.search, False, False, 0)
        
        self.cat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.cat_box.set_margin_start(20)
        self.cat_box.set_margin_end(20)
        self.cat_box.set_halign(Gtk.Align.CENTER)
        self.main_box.pack_start(self.cat_box, False, False, 0)
        
        self.active_category = "Todas"
        self.cat_buttons = {}
        for cat_name in CATEGORIES.keys():
            btn = Gtk.Button(label=cat_name)
            btn.set_name("cat_btn")
            btn.set_can_focus(False)
            btn.connect("clicked", self.on_category_clicked, cat_name)
            self.cat_buttons[cat_name] = btn
            self.cat_box.pack_start(btn, False, False, 0)
            
        self.cat_buttons["Todas"].get_style_context().add_class("active")
        
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(6)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_name("launcher_flow")
        
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.add(self.flowbox)
        self.scroll.set_margin_start(20)
        self.scroll.set_margin_end(20)
        self.scroll.set_margin_bottom(20)
        self.main_box.pack_start(self.scroll, True, True, 0)
        
        self.load_apps()
        GLib.idle_add(self.position_window)

    def refresh_state(self):
        self.search.set_text("")
        self.search.grab_focus()

    def position_window(self):
        geometry = Gdk.Display.get_default().get_primary_monitor().get_geometry()
        width, height = self.get_size()
        x = geometry.x + (geometry.width - width) // 2
        y = geometry.y + (geometry.height - height) // 2
        self.move(x, y)
        return False

    def load_apps(self):
        apps = Gio.AppInfo.get_all()
        apps = sorted(apps, key=lambda a: a.get_name().lower() if a.get_name() else "")
        for app in apps:
            if not app.should_show() or app.get_nodisplay(): continue
            btn = Gtk.Button()
            btn.set_name("app_btn")
            btn.app_info = app
            btn.app_name = app.get_name().lower() if app.get_name() else ""
            btn.app_categories = app.get_categories() or ""
            btn.connect("clicked", self.on_app_clicked)
            
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            icon = app.get_icon()
            if icon: img = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DIALOG)
            else: img = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.DIALOG)
            img.set_pixel_size(48)
            box.pack_start(img, False, False, 0)
            
            name = app.get_name() or "App"
            if len(name) > 13: name = name[:11] + "..."
            lbl = Gtk.Label(label=name)
            lbl.set_name("app_label")
            box.pack_start(lbl, False, False, 0)
            
            btn.add(box)
            btn.set_halign(Gtk.Align.CENTER)
            btn.set_size_request(90, 100)
            self.flowbox.insert(btn, -1)
            
    def on_category_clicked(self, widget, cat_name):
        self.manager.reset_timer()
        for name, btn in self.cat_buttons.items():
            btn.get_style_context().remove_class("active")
        widget.get_style_context().add_class("active")
        self.active_category = cat_name
        self.on_filter_changed(None)

    def on_filter_changed(self, entry=None):
        self.manager.reset_timer()
        search_text = self.search.get_text().lower()
        active_cat_keywords = CATEGORIES[self.active_category].split(";")
        def filter_func(child):
            btn = child.get_child()
            matches_text = True
            if search_text: matches_text = search_text in btn.app_name
            matches_cat = True
            if self.active_category != "Todas":
                matches_cat = any(kw in btn.app_categories for kw in active_cat_keywords if kw)
            return matches_text and matches_cat
        self.flowbox.set_filter_func(filter_func)

    def on_app_clicked(self, widget):
        try: widget.app_info.launch([], None)
        except: pass
        self.manager.close_active()

    def setup_css(self):
        css = b'''
        * { outline: none; }
        window { background-color: transparent; }
        #launcher_box {
            background-color: rgba(24, 24, 27, 0.95);
            border-radius: 24px;
            border: 1px solid #27272a;
            box-shadow: 0 8px 32px rgba(0,0,0,0.8);
        }
        #launcher_search {
            background-color: #27272a; color: #ffffff;
            border: 1px solid #3f3f46; border-radius: 12px;
            padding: 12px 16px; font-size: 15px;
        }
        #cat_btn {
            background-color: transparent; color: #a1a1aa;
            border: 1px solid #3f3f46; border-radius: 20px;
            padding: 6px 16px; font-size: 13px; font-weight: bold;
            transition: all 200ms ease;
        }
        #cat_btn:hover { background-color: rgba(255, 255, 255, 0.05); color: #ffffff; }
        #cat_btn.active { background-color: #3b82f6; color: #ffffff; border-color: #3b82f6; }
        #app_btn { background-color: transparent; border: none; border-radius: 16px; padding: 12px 8px; transition: all 200ms ease; }
        #app_btn:hover { background-color: rgba(255, 255, 255, 0.08); }
        #app_label { color: #fafafa; font-size: 12px; margin-top: 10px; }
        scrolledwindow { background-color: transparent; }
        viewport { background-color: transparent; }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


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
        
        self.popup_manager = PopupManager()
        self.popup_manager.init_popups()
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.main_box.set_name("panel_box")
        self.main_box.set_margin_bottom(8)
        
        self.btn_launcher = Gtk.Button()
        self.btn_launcher.set_name("panel_btn")
        self.btn_launcher.set_can_focus(False)
        self.btn_launcher.connect("clicked", lambda w: self.popup_manager.toggle('launcher'))
        self.btn_launcher.add(Gtk.Image.new_from_icon_name("view-app-grid-symbolic", Gtk.IconSize.MENU))
        self.main_box.pack_start(self.btn_launcher, False, False, 4)
        
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_top(4)
        sep.set_margin_bottom(4)
        self.main_box.pack_start(sep, False, False, 0)
        
        self.win_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.scroll.add(self.win_box)
        self.main_box.pack_start(self.scroll, True, True, 4)
        
        def make_indicator():
            b = Gtk.Button()
            b.set_name("pill_item")
            b.set_can_focus(False)
            return b
            
        self.btn_vol = make_indicator()
        self.icon_vol = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.MENU)
        self.btn_vol.add(self.icon_vol)
        self.btn_vol.connect("clicked", lambda w: self.popup_manager.toggle('volume'))
        self.main_box.pack_start(self.btn_vol, False, False, 0)
        
        self.btn_bright = make_indicator()
        self.btn_bright.add(Gtk.Image.new_from_icon_name("display-brightness-symbolic", Gtk.IconSize.MENU))
        self.btn_bright.connect("clicked", lambda w: self.popup_manager.toggle('brightness'))
        self.main_box.pack_start(self.btn_bright, False, False, 0)
        
        self.btn_wifi = make_indicator()
        self.btn_wifi.add(Gtk.Image.new_from_icon_name("network-wireless-symbolic", Gtk.IconSize.MENU))
        self.btn_wifi.connect("clicked", lambda x: subprocess.Popen(["nm-connection-editor"]))
        self.main_box.pack_start(self.btn_wifi, False, False, 0)
        
        self.btn_bat = make_indicator()
        self.icon_bat = Gtk.Image.new_from_icon_name("battery-good-symbolic", Gtk.IconSize.MENU)
        self.lbl_bat = Gtk.Label()
        box_bat = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box_bat.pack_start(self.icon_bat, False, False, 0)
        box_bat.pack_start(self.lbl_bat, False, False, 0)
        self.btn_bat.add(box_bat)
        self.btn_bat.connect("clicked", lambda x: subprocess.Popen(["xfce4-power-manager-settings"]))
        self.main_box.pack_start(self.btn_bat, False, False, 0)
        
        self.btn_time = make_indicator()
        self.lbl_time = Gtk.Label()
        self.lbl_time.set_name("pill_label")
        self.btn_time.add(self.lbl_time)
        self.btn_time.connect("clicked", lambda w: self.popup_manager.toggle('calendar'))
        self.main_box.pack_start(self.btn_time, False, False, 0)
        
        self.btn_power = make_indicator()
        self.btn_power.add(Gtk.Image.new_from_icon_name("system-shutdown-symbolic", Gtk.IconSize.MENU))
        self.btn_power.connect("clicked", lambda w: self.popup_manager.toggle('power'))
        self.main_box.pack_start(self.btn_power, False, False, 4)
        
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
            background-color: #18181b; border-radius: 20px;
            border: 1px solid #27272a; box-shadow: 0 4px 12px rgba(0,0,0,0.5); padding: 4px;
        }
        #panel_btn, #pill_item {
            background-color: transparent; color: #fafafa; border: none; box-shadow: none;
            border-radius: 12px; padding: 4px 10px; transition: all 200ms ease-in-out;
        }
        #panel_btn { min-width: 24px; }
        #panel_btn:hover, #pill_item:hover { background-color: #27272a; }
        #panel_btn.running { padding: 4px 14px; border-bottom: 2px solid #3f3f46; background-color: #27272a; }
        #panel_btn.active { padding: 4px 14px; border-bottom: 2px solid #60a5fa; background-color: #3f3f46; }
        #app_label, #pill_label { color: #fafafa; font-size: 13px; font-weight: 500; }
        image { color: #fafafa; }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

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
        # Do not auto-hide panel if a popup is active
        if self.popup_manager.active_popup: return False
        self.hide_timer = GLib.timeout_add(2000, self.hide_panel)
        return False
        
    def hide_panel(self):
        self.hide_timer = None
        # Never hide panel while a popup is open!
        if self.popup_manager.active_popup: return False
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
        if self.popup_manager.active_popup: return True
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
        
        target_width = geometry.width - 32
        self.set_size_request(target_width, -1)
        
        width, height = self.get_size()
        x = 16
        self.base_y = geometry.height - height
        
        if self.current_y == 0:
            self.current_y = self.base_y
            self.move(x, self.base_y)
            
        return False

if __name__ == "__main__":
    app = QuickPanel()
    app.show_all()
    Gtk.main()
"""

with open('/home/nioy/.local/bin/quick-panel-unified.py', 'w') as f:
    f.write(code)

os.system('chmod +x /home/nioy/.local/bin/quick-panel-unified.py')
