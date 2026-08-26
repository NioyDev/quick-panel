#!/usr/bin/env python3
import gi
import subprocess
import os
import datetime
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango, GLib

class QuickToggle(Gtk.Box):
    def __init__(self, icon_name, title, subtitle_on, subtitle_off, cmd_on, cmd_off, cmd_check):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.cmd_on = cmd_on
        self.cmd_off = cmd_off
        self.cmd_check = cmd_check
        self.subtitle_on = subtitle_on
        self.subtitle_off = subtitle_off
        self.is_active = False

        # El botón circular
        self.btn = Gtk.Button()
        self.icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DND)
        self.icon.set_pixel_size(24)
        self.btn.add(self.icon)
        self.btn.set_name("toggle_btn")
        self.btn.connect("clicked", self.on_clicked)
        self.btn.set_halign(Gtk.Align.CENTER)
        
        self.pack_start(self.btn, False, False, 0)
        
        # Textos
        self.lbl_title = Gtk.Label(label=title)
        self.lbl_title.set_markup(f"<span weight='bold' size='medium' foreground='#fafafa'>{title}</span>")
        
        self.lbl_sub = Gtk.Label(label=subtitle_off)
        self.lbl_sub.set_markup(f"<span size='small' foreground='#a1a1aa'>{subtitle_off}</span>")
        
        self.pack_start(self.lbl_title, False, False, 0)
        self.pack_start(self.lbl_sub, False, False, 0)
        
    def on_clicked(self, widget):
        if not self.is_active and self.cmd_on:
            subprocess.Popen(self.cmd_on, shell=True)
        elif self.is_active and self.cmd_off:
            subprocess.Popen(self.cmd_off, shell=True)
            
        self.is_active = not self.is_active
        self.update_ui()
            
    def update_state(self, active):
        self.is_active = active
        self.update_ui()
        
    def update_ui(self):
        ctx = self.btn.get_style_context()
        if self.is_active:
            ctx.add_class("active")
            self.lbl_sub.set_markup(f"<span size='small' foreground='#a1a1aa'>{self.subtitle_on}</span>")
        else:
            ctx.remove_class("active")
            self.lbl_sub.set_markup(f"<span size='small' foreground='#a1a1aa'>{self.subtitle_off}</span>")


class QuickSettingsPanel(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_type_hint(Gdk.WindowTypeHint.DROPDOWN_MENU)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_default_size(380, 520)
        
        # Add timer for live battery updates
        GLib.timeout_add_seconds(5, self.update_battery)
        
        # Transparencia para esquinas redondeadas
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

        self.setup_css()
        
        # Contenedor principal
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.main_box.set_name("main_window")
        self.main_box.set_margin_top(24)
        self.main_box.set_margin_bottom(20)
        self.main_box.set_margin_start(24)
        self.main_box.set_margin_end(24)
        self.add(self.main_box)
        
        self.build_header()
        self.build_grid()
        self.build_sliders()
        self.build_footer()
        
        GLib.idle_add(self.check_initial_states)
        GLib.idle_add(self.reposition)

    def reposition(self):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        width, height = self.get_size()
        # 16px de padding desde la derecha, 100px desde abajo para flotar encima del Pill
        self.move(geometry.width - width - 16, geometry.height - height - 100)
        return False
        
    def build_header(self):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        # Avatar placeholder
        avatar = Gtk.Image.new_from_icon_name("avatar-default-symbolic", Gtk.IconSize.DND)
        avatar.set_name("avatar")
        
        hbox.pack_start(avatar, False, False, 0)
        
        # Spacer
        spacer = Gtk.Box()
        hbox.pack_start(spacer, True, True, 0)
        
        # Icon buttons
        btn_power = Gtk.Button.new_from_icon_name("system-shutdown-symbolic", Gtk.IconSize.BUTTON)
        btn_power.set_name("icon_btn")
        btn_power.connect("clicked", lambda w: (subprocess.Popen("xfce4-session-logout", shell=True), Gtk.main_quit()))
        
        btn_lock = Gtk.Button.new_from_icon_name("system-lock-screen-symbolic", Gtk.IconSize.BUTTON)
        btn_lock.set_name("icon_btn")
        btn_lock.connect("clicked", lambda w: (subprocess.Popen("xflock4", shell=True), Gtk.main_quit()))
        
        btn_settings = Gtk.Button.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON)
        btn_settings.set_name("icon_btn")
        btn_settings.connect("clicked", lambda w: (subprocess.Popen("xfce4-settings-manager", shell=True), Gtk.main_quit()))
        
        hbox.pack_start(btn_power, False, False, 0)
        hbox.pack_start(btn_lock, False, False, 0)
        hbox.pack_start(btn_settings, False, False, 0)
        
        self.main_box.pack_start(hbox, False, False, 0)

    def build_grid(self):
        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(32)
        self.grid.set_row_spacing(24)
        self.grid.set_halign(Gtk.Align.CENTER)
        
        self.toggles = {
            "wifi": QuickToggle("network-wireless-symbolic", "Wi-Fi", "Conectado", "Desconectado", 
                                "nmcli radio wifi on", "nmcli radio wifi off", "nmcli radio wifi | grep -q enabled"),
            "bt": QuickToggle("bluetooth-active-symbolic", "Bluetooth", "Activado", "Desactivado", 
                              "rfkill unblock bluetooth", "rfkill block bluetooth", "rfkill list bluetooth | grep -q 'Soft blocked: no'"),
            "dnd": QuickToggle("notifications-disabled-symbolic", "No Molestar", "Activado", "Desactivado", 
                               "xfconf-query -c xfce4-notifyd -p /do-not-disturb -n -t bool -s true", 
                               "xfconf-query -c xfce4-notifyd -p /do-not-disturb -s false", 
                               "xfconf-query -c xfce4-notifyd -p /do-not-disturb | grep -qi true"),
            "dark": QuickToggle("weather-clear-night-symbolic", "Tema Oscuro", "Activado", "Desactivado", 
                                "xfconf-query -c xsettings -p /Net/ThemeName -s Mint-Y-Dark-Aqua", 
                                "xfconf-query -c xsettings -p /Net/ThemeName -s Mint-Y-Aqua", 
                                "xfconf-query -c xsettings -p /Net/ThemeName | grep -qi dark"),
            "mic": QuickToggle("audio-input-microphone-muted-symbolic", "Micrófono", "Activo", "Silenciado", 
                               "pactl set-source-mute @DEFAULT_SOURCE@ 0", 
                               "pactl set-source-mute @DEFAULT_SOURCE@ 1", 
                               "pactl get-source-mute @DEFAULT_SOURCE@ | grep -q 'Mute: no'"),
            "night": QuickToggle("display-brightness-symbolic", "Luz Nocturna", "Activado", "Desactivado", 
                                 "redshift -O 4500K", "redshift -x", "pgrep -f 'redshift -O'")
        }
        
        self.grid.attach(self.toggles["wifi"], 0, 0, 1, 1)
        self.grid.attach(self.toggles["bt"], 1, 0, 1, 1)
        self.grid.attach(self.toggles["dnd"], 2, 0, 1, 1)
        
        self.grid.attach(self.toggles["dark"], 0, 1, 1, 1)
        self.grid.attach(self.toggles["mic"], 1, 1, 1, 1)
        self.grid.attach(self.toggles["night"], 2, 1, 1, 1)
        
        self.main_box.pack_start(self.grid, False, False, 16)
        
    def build_sliders(self):
        # Volumen
        box_vol = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        icon_vol = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        
        self.scale_vol = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale_vol.set_hexpand(True)
        self.scale_vol.set_draw_value(False)
        self.scale_vol.set_name("custom_slider")
        self.scale_vol.connect("value-changed", self.on_vol_changed)
        
        box_vol.pack_start(icon_vol, False, False, 0)
        box_vol.pack_start(self.scale_vol, True, True, 0)
        
        # Brillo
        box_bri = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        icon_bri = Gtk.Image.new_from_icon_name("display-brightness-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        
        self.scale_bri = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 5, 100, 1)
        self.scale_bri.set_hexpand(True)
        self.scale_bri.set_draw_value(False)
        self.scale_bri.set_name("custom_slider")
        self.scale_bri.connect("value-changed", self.on_bri_changed)
        
        box_bri.pack_start(icon_bri, False, False, 0)
        box_bri.pack_start(self.scale_bri, True, True, 0)
        
        self.main_box.pack_start(box_vol, False, False, 8)
        self.main_box.pack_start(box_bri, False, False, 8)
        
    def build_footer(self):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        
        now = datetime.datetime.now()
        lbl_date = Gtk.Label()
        lbl_date.set_markup(f"<span foreground='#a1a1aa' weight='medium'>{now.strftime('%a, %b %d')}</span>")
        
        sep = Gtk.Label()
        sep.set_markup("<span foreground='#3f3f46'>|</span>")
        
        self.lbl_bat = Gtk.Label()
        self.lbl_bat.set_markup("<span foreground='#a1a1aa'>Calculando...</span>")
        
        hbox.pack_start(lbl_date, False, False, 0)
        hbox.pack_start(sep, False, False, 0)
        hbox.pack_start(self.lbl_bat, False, False, 0)
        
        self.main_box.pack_end(hbox, False, False, 8)

    def check_initial_states(self):
        self._loading = True
        
        # Load toggle states
        for key, toggle in self.toggles.items():
            if toggle.cmd_check:
                ret = subprocess.call(toggle.cmd_check, shell=True)
                toggle.update_state(ret == 0)
        
        # Volume
        try:
            out = subprocess.check_output("pactl get-sink-volume @DEFAULT_SINK@ | grep -Po '\\d+(?=%)' | head -n 1", shell=True).decode().strip()
            if out:
                self.scale_vol.set_value(float(out))
        except: pass
        
        # Brightness
        try:
            max_bri = float(subprocess.check_output("brightnessctl m", shell=True).decode().strip())
            cur_bri = float(subprocess.check_output("brightnessctl g", shell=True).decode().strip())
            self.scale_bri.set_value((cur_bri / max_bri) * 100)
        except: pass

        self.update_battery()
        self._loading = False
        return False

    def update_battery(self):
        try:
            bat_out = subprocess.check_output("upower -i $(upower -e | grep BAT)", shell=True).decode('utf-8')
            pct = "100%"
            state = "desconocido"
            for line in bat_out.split('\n'):
                if 'percentage:' in line:
                    pct = line.split(':')[1].strip()
                if 'state:' in line:
                    state = line.split(':')[1].strip()
            
            if state == "charging":
                status = f"{pct} (Cargando)"
            elif state == "fully-charged":
                status = f"{pct} (Cargada)"
            else:
                status = f"{pct} restante"
                
            self.lbl_bat.set_markup(f"<span foreground='#a1a1aa'>{status}</span>")
        except Exception:
            self.lbl_bat.set_markup(f"<span foreground='#a1a1aa'>100% (AC)</span>")
        return True

    def on_vol_changed(self, scale):
        if getattr(self, "_loading", False): return
        val = int(scale.get_value())
        subprocess.Popen(f"pactl set-sink-volume @DEFAULT_SINK@ {val}%", shell=True)
        
    def on_bri_changed(self, scale):
        if getattr(self, "_loading", False): return
        val = int(scale.get_value())
        subprocess.Popen(f"brightnessctl set {val}%", shell=True)

    def setup_css(self):
        css = '''
        * {
            outline: none;
            font-family: system-ui, sans-serif;
        }
        
        window { 
            background-color: transparent; 
        }
        
        #main_window {
            background-color: #09090b; /* Zinc 950 */
            border-radius: 28px;
            border: 1px solid #27272a;
            box-shadow: 0 10px 30px rgba(0,0,0,0.8);
        }
        
        #avatar {
            background-color: #27272a;
            border-radius: 50%;
            padding: 8px;
            min-width: 24px;
            min-height: 24px;
        }
        
        #btn_signout {
            background-color: #18181b;
            color: #fafafa;
            border-radius: 16px;
            padding: 6px 16px;
            border: 1px solid #27272a;
            font-weight: 500;
            transition: all 150ms ease;
        }
        #btn_signout:hover { background-color: #27272a; }
        
        #icon_btn {
            background-color: #18181b;
            color: #fafafa;
            border-radius: 100%;
            padding: 10px;
            border: none;
            transition: all 150ms ease;
        }
        #icon_btn:hover { background-color: #27272a; }
        
        #toggle_btn {
            background-color: #18181b;
            color: #a1a1aa;
            border-radius: 100%;
            min-width: 64px;
            min-height: 64px;
            border: none;
            transition: all 250ms ease;
        }
        #toggle_btn:hover {
            background-color: #27272a;
        }
        #toggle_btn.active {
            background-color: #fafafa;
            color: #09090b;
        }
        #toggle_btn.active:hover {
            background-color: #e4e4e7;
        }
        
        #custom_slider trough {
            background-color: #27272a;
            border-radius: 6px;
            min-height: 4px;
            background-image: none;
        }
        #custom_slider highlight,
        #custom_slider trough highlight {
            background-color: #fafafa;
            border-radius: 6px;
            background-image: none;
        }
        #custom_slider slider {
            background-color: #ffffff;
            min-width: 16px;
            min-height: 16px;
            border-radius: 50%;
            border: 1px solid #18181b;
            box-shadow: 0 2px 4px rgba(0,0,0,0.5);
            margin: -6px 0;
            background-image: none;
        }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

if __name__ == '__main__':
    win = QuickSettingsPanel()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
