#!/usr/bin/env python3
import gi
import subprocess
import json
import os
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango, GLib

class KeyboardSettingsPanel(Gtk.Window):
    def __init__(self):
        super().__init__(title="Panel de Teclado")
        self.set_default_size(750, 500)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Diccionarios de traducción
        self.xfce_to_human_map = {
            "<Primary>": "Ctrl + ",
            "<Control>": "Ctrl + ",
            "<Alt>": "Alt + ",
            "<Shift>": "Shift + ",
            "<Super>": "Super + "
        }
        
        self.desc_file = os.path.expanduser("~/.config/atajos_desc.json")
        
        # HeaderBar oscuro
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Configuración")
        self.set_titlebar(header)

        # Stack para las Pestañas (Reemplaza al viejo Notebook)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(250)
        self.add(self.stack)
        
        # StackSwitcher integrado en el título
        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        header.set_custom_title(switcher)

        # Crear las pestañas
        self.create_tab_atajos()
        self.create_tab_comportamiento()
        self.create_tab_distribucion()

        # CSS Impeccable: Vercel/Linear Premium Monochrome
        css = '''
        * {
            outline: none;
            font-family: system-ui, sans-serif;
        }
        
        window { 
            background-color: #09090b; 
            color: #fafafa; 
        }
        
        headerbar {
            background-color: #09090b;
            border-bottom: 1px solid #27272a;
        }
        
        stackswitcher button {
            background-color: transparent;
            color: #a1a1aa;
            border: none;
            border-radius: 6px;
            padding: 6px 16px;
            margin: 0 2px;
            font-weight: 500;
        }
        stackswitcher button:hover {
            background-color: #18181b;
            color: #fafafa;
        }
        stackswitcher button:checked {
            background-color: #27272a;
            color: #fafafa;
            box-shadow: none;
        }
        
        entry { 
            background-color: #09090b; 
            color: #fafafa; 
            border-radius: 8px; 
            border: 1px solid #27272a; 
            padding: 10px 14px; 
            transition: all 200ms ease;
            box-shadow: none;
        }
        entry:focus { 
            border: 1px solid #71717a; 
            background-color: #09090b;
            box-shadow: 0 0 0 2px rgba(250,250,250,0.05); 
        }
        
        #btn_add { 
            background-color: #fafafa; 
            color: #09090b; 
            border-radius: 8px; 
            padding: 8px 24px; 
            font-weight: bold; 
            border: 1px solid #fafafa; 
            transition: all 150ms ease;
        }
        #btn_add:hover { 
            background-color: #e4e4e7; 
            border-color: #e4e4e7;
        }
        #btn_add:active { 
            background-color: #d4d4d8; 
        }
        
        #btn_delete { 
            background-color: transparent; 
            color: #71717a; 
            border-radius: 8px; 
            padding: 8px; 
            border: none;
            transition: all 150ms ease;
        }
        #btn_delete:hover { 
            background-color: rgba(239, 68, 68, 0.1); 
            color: #ef4444; 
        }
        #btn_delete:active {
            background-color: rgba(239, 68, 68, 0.2);
        }
        
        list { background-color: transparent; }
        row { 
            padding: 16px 20px; 
            border-radius: 8px; 
            margin: 6px 12px; 
            border: 1px solid #27272a;
            background-color: #18181b; 
            transition: all 150ms ease;
        }
        row:hover { 
            background-color: #27272a; 
            border: 1px solid #3f3f46;
        }
        
        notebook { background-color: #09090b; }
        
        combobox { 
            background-color: #18181b; 
            border-radius: 8px; 
            padding: 8px; 
            border: 1px solid #27272a; 
            transition: all 150ms ease;
        }
        combobox:hover { 
            background-color: #27272a;
        }
        
        scrolledwindow { 
            border: none;
            background-color: transparent; 
        }
        
        scrollbar {
            background-color: transparent;
            border: none;
        }
        scrollbar slider {
            background-color: #3f3f46;
            border-radius: 4px;
            min-width: 6px;
            min-height: 6px;
            border: 2px solid transparent;
            background-clip: padding-box;
        }
        scrollbar slider:hover {
            background-color: #71717a;
        }
        scrollbar slider:active {
            background-color: #a1a1aa;
        }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Optimización: deferimos la carga de datos para que la ventana abra instantáneamente
        GLib.idle_add(self.load_all_data)

    # --- PESTAÑA 1: ATAJOS ---
    def create_tab_atajos(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        main_box.set_margin_top(24)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)

        # Sección de Agregar (Top)
        add_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        self.entry_keys = Gtk.Entry()
        self.entry_keys.set_placeholder_text("Teclas (ej: Ctrl+D)")
        self.entry_keys.set_hexpand(True)
        self.entry_keys.connect("key-press-event", self.on_key_press)
        
        self.entry_cmd = Gtk.Entry()
        self.entry_cmd.set_placeholder_text("Comando (ej: alacritty)")
        self.entry_cmd.set_hexpand(True)
        
        self.entry_desc = Gtk.Entry()
        self.entry_desc.set_placeholder_text("Descripción (Opcional)")
        self.entry_desc.set_hexpand(True)
        
        self.btn_add = Gtk.Button(label="Agregar")
        self.btn_add.set_name("btn_add")
        self.btn_add.connect("clicked", self.on_add_clicked)
        
        add_box.pack_start(self.entry_keys, True, True, 0)
        add_box.pack_start(self.entry_cmd, True, True, 0)
        add_box.pack_start(self.entry_desc, True, True, 0)
        add_box.pack_start(self.btn_add, False, False, 0)
        
        main_box.pack_start(add_box, False, False, 0)

        # Separador eliminado (El espaciado y el diseño Card lo hacen innecesario)

        # Lista de atajos (Bottom) - Sin encabezados de columna gracias al diseño Card Impeccable
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.add(self.listbox)
        
        main_box.pack_start(scroll, True, True, 0)
        self.stack.add_titled(main_box, "atajos", "Atajos")

    # --- PESTAÑA 2: COMPORTAMIENTO ---
    def create_tab_comportamiento(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=30)
        box.set_margin_top(40)
        box.set_margin_bottom(20)
        box.set_margin_start(40)
        box.set_margin_end(40)

        # Switch de repetición
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        lbl = Gtk.Label(label="<big>Habilitar repetición de teclas</big>")
        lbl.set_use_markup(True)
        lbl.set_halign(Gtk.Align.START)
        self.switch_repeat = Gtk.Switch()
        self.switch_repeat.set_valign(Gtk.Align.CENTER)
        
        hbox.pack_start(lbl, True, True, 0)
        hbox.pack_end(self.switch_repeat, False, False, 0)
        box.pack_start(hbox, False, False, 0)
        
        # Sliders
        # Retraso
        box_delay = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        lbl_delay = Gtk.Label(label="Retraso antes de repetir (ms):")
        lbl_delay.set_halign(Gtk.Align.START)
        self.scale_delay = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 100, 1000, 10)
        box_delay.pack_start(lbl_delay, False, False, 0)
        box_delay.pack_start(self.scale_delay, False, False, 0)
        box.pack_start(box_delay, False, False, 0)

        # Velocidad
        box_rate = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        lbl_rate = Gtk.Label(label="Velocidad de repetición (caracteres/s):")
        lbl_rate.set_halign(Gtk.Align.START)
        self.scale_rate = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1)
        box_rate.pack_start(lbl_rate, False, False, 0)
        box_rate.pack_start(self.scale_rate, False, False, 0)
        box.pack_start(box_rate, False, False, 0)
        
        # Valores por defecto para renderizado rápido
        self.switch_repeat.set_active(True)
        self.scale_delay.set_value(500)
        self.scale_rate.set_value(20)

        self.stack.add_titled(box, "comportamiento", "Comportamiento")

    # --- PESTAÑA 3: DISTRIBUCIÓN ---
    def create_tab_distribucion(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=30)
        box.set_margin_top(40)
        box.set_margin_bottom(20)
        box.set_margin_start(40)
        box.set_margin_end(40)

        lbl = Gtk.Label(label="<big><b>Idioma y Distribución del Teclado</b></big>")
        lbl.set_use_markup(True)
        lbl.set_halign(Gtk.Align.START)
        box.pack_start(lbl, False, False, 0)
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        lbl_sel = Gtk.Label(label="Seleccionar idioma:")
        
        self.combo_lang = Gtk.ComboBoxText()
        self.combo_lang.append("es", "Español (es)")
        self.combo_lang.append("latam", "Español Latinoamericano (latam)")
        self.combo_lang.append("us", "Inglés (us)")
        self.combo_lang.append("gb", "Inglés Británico (gb)")
        self.combo_lang.append("fr", "Francés (fr)")
        self.combo_lang.append("de", "Alemán (de)")
        
        self.combo_lang.set_active_id("es")
        
        hbox.pack_start(lbl_sel, False, False, 0)
        hbox.pack_start(self.combo_lang, True, True, 0)
        box.pack_start(hbox, False, False, 0)

        self.stack.add_titled(box, "distribucion", "Distribución")

    def load_all_data(self):
        self._loading = True
        # 1. Comportamiento
        try:
            repeat = subprocess.check_output(["xfconf-query", "-c", "keyboards", "-p", "/Default/KeyRepeat"]).decode().strip()
            self.switch_repeat.set_active(repeat == "true")
        except: pass
        try:
            delay = subprocess.check_output(["xfconf-query", "-c", "keyboards", "-p", "/Default/KeyRepeatDelay"]).decode().strip()
            self.scale_delay.set_value(float(delay))
        except: pass
        try:
            rate = subprocess.check_output(["xfconf-query", "-c", "keyboards", "-p", "/Default/KeyRepeatRate"]).decode().strip()
            self.scale_rate.set_value(float(rate))
        except: pass
        
        self.switch_repeat.connect("notify::active", self.on_repeat_changed)
        self.scale_delay.connect("value-changed", self.on_delay_changed)
        self.scale_rate.connect("value-changed", self.on_rate_changed)

        # 2. Distribución
        try:
            out = subprocess.check_output(["setxkbmap", "-query"]).decode()
            for line in out.splitlines():
                if line.startswith("layout:"):
                    lang = line.split(":")[1].strip()
                    self.combo_lang.set_active_id(lang)
                    break
        except: pass
        self.combo_lang.connect("changed", self.on_lang_changed)

        # 3. Atajos
        self.load_shortcuts()
        self._loading = False
        return False

    # --- EVENTOS DE COMPORTAMIENTO Y DISTRIBUCIÓN ---
    def on_repeat_changed(self, switch, gparam):
        if getattr(self, "_loading", False): return
        val = "true" if switch.get_active() else "false"
        subprocess.Popen(["xfconf-query", "-c", "keyboards", "-p", "/Default/KeyRepeat", "-n", "-t", "bool", "-s", val])
        # Aplicar al instante en x11
        arg = "on" if switch.get_active() else "off"
        subprocess.Popen(["xset", "r", arg])

    def on_delay_changed(self, scale):
        if getattr(self, "_loading", False): return
        val = int(scale.get_value())
        subprocess.Popen(["xfconf-query", "-c", "keyboards", "-p", "/Default/KeyRepeatDelay", "-n", "-t", "int", "-s", str(val)])
        self.apply_xset_rate()

    def on_rate_changed(self, scale):
        if getattr(self, "_loading", False): return
        val = int(scale.get_value())
        subprocess.Popen(["xfconf-query", "-c", "keyboards", "-p", "/Default/KeyRepeatRate", "-n", "-t", "int", "-s", str(val)])
        self.apply_xset_rate()
        
    def apply_xset_rate(self):
        delay = int(self.scale_delay.get_value())
        rate = int(self.scale_rate.get_value())
        subprocess.Popen(["xset", "r", "rate", str(delay), str(rate)])

    def on_lang_changed(self, combo):
        if getattr(self, "_loading", False): return
        lang = combo.get_active_id()
        if lang:
            # Aplicar en la sesión actual
            subprocess.Popen(["setxkbmap", lang])
            # Guardar en XFCE para reinicios
            subprocess.Popen(["xfconf-query", "-c", "keyboard-layout", "-p", "/Default/XkbDisable", "-n", "-t", "bool", "-s", "false"])
            subprocess.Popen(["xfconf-query", "-c", "keyboard-layout", "-p", "/Default/XkbLayout", "-n", "-t", "string", "-s", lang])

    # --- FUNCIONES DE ATAJOS (TAB 1) ---
    def load_shortcuts(self):
        for child in self.listbox.get_children():
            self.listbox.remove(child)
            
        desc_map = {}
        if os.path.exists(self.desc_file):
            try:
                with open(self.desc_file, 'r') as f:
                    desc_map = json.load(f)
            except:
                pass
            
        try:
            out = subprocess.check_output(["xfconf-query", "-c", "xfce4-keyboard-shortcuts", "-l", "-v"]).decode('utf-8')
            for line in out.splitlines():
                if "/commands/custom/" in line:
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        raw_key = parts[0].replace("/commands/custom/", "")
                        cmd = parts[1]
                        
                        if cmd.strip() == "startup-notify":
                            continue
                            
                        desc = desc_map.get(raw_key, "")
                        
                        human_key = raw_key
                        for xfce, hum in self.xfce_to_human_map.items():
                            human_key = human_key.replace(xfce, hum)
                        human_key = human_key.title().replace("+ ", "+ ")
                        
                        self.add_row_to_list(human_key, raw_key, cmd, desc)
        except Exception as e:
            print("Error cargando atajos:", e)

    def add_row_to_list(self, display_key, raw_key, cmd, desc):
        row = Gtk.ListBoxRow()
        
        main_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        
        # Izquierda: Tecla
        lbl_k = Gtk.Label()
        lbl_k.set_markup(f"<span size='large' weight='bold' foreground='#ffffff'>{display_key}</span>")
        lbl_k.set_halign(Gtk.Align.START)
        lbl_k.set_valign(Gtk.Align.CENTER)
        lbl_k.set_width_chars(15) # Ancho visual fijo para que sirva de ancla
        
        # Centro: Descripcion y comando
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_valign(Gtk.Align.CENTER)
        
        desc_text = desc if desc else "Atajo del Sistema"
        lbl_d = Gtk.Label()
        lbl_d.set_markup(f"<span size='medium' weight='semibold' foreground='#e5e5ea'>{desc_text}</span>")
        lbl_d.set_halign(Gtk.Align.START)
        lbl_d.set_ellipsize(Pango.EllipsizeMode.END)
        
        lbl_c = Gtk.Label()
        lbl_c.set_markup(f"<span font_family='monospace' size='small' foreground='#8e8e93'>{cmd}</span>")
        lbl_c.set_halign(Gtk.Align.START)
        lbl_c.set_ellipsize(Pango.EllipsizeMode.END)
        
        vbox.pack_start(lbl_d, False, False, 0)
        vbox.pack_start(lbl_c, False, False, 0)
        
        # Derecha: Botón de borrar (Icono)
        icon = Gtk.Image.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON)
        btn_del = Gtk.Button()
        btn_del.add(icon)
        btn_del.set_name("btn_delete")
        btn_del.set_valign(Gtk.Align.CENTER)
        btn_del.connect("clicked", self.on_delete_clicked, raw_key, row)
        
        main_hbox.pack_start(lbl_k, False, False, 0)
        main_hbox.pack_start(vbox, True, True, 0)
        main_hbox.pack_end(btn_del, False, False, 0)
        
        row.add(main_hbox)
        self.listbox.add(row)
        self.listbox.show_all()

    def on_add_clicked(self, widget):
        raw_key = getattr(self, "current_raw_key", None)
        if not raw_key:
            return
            
        cmd = self.entry_cmd.get_text().strip()
        desc = self.entry_desc.get_text().strip()
        
        if not cmd:
            return
            
        subprocess.Popen(["xfconf-query", "-c", "xfce4-keyboard-shortcuts", "-p", f"/commands/custom/{raw_key}", "-n", "-t", "string", "-s", cmd])
        
        desc_map = {}
        if os.path.exists(self.desc_file):
            try:
                with open(self.desc_file, 'r') as f:
                    desc_map = json.load(f)
            except:
                pass
        desc_map[raw_key] = desc
        with open(self.desc_file, 'w') as f:
            json.dump(desc_map, f)
        
        self.entry_keys.set_text("")
        self.entry_cmd.set_text("")
        self.entry_desc.set_text("")
        self.current_raw_key = None
        self.entry_keys.grab_focus()
        
        GLib.timeout_add(200, self.load_shortcuts_delayed)

    def on_delete_clicked(self, widget, key, row):
        subprocess.Popen(["xfconf-query", "-c", "xfce4-keyboard-shortcuts", "-p", f"/commands/custom/{key}", "-r", "-R"])
        self.listbox.remove(row)

    def load_shortcuts_delayed(self):
        self.load_shortcuts()
        return False

    def on_key_press(self, widget, event):
        keyval = event.keyval
        
        is_mod = keyval in [
            Gdk.KEY_Control_L, Gdk.KEY_Control_R, 
            Gdk.KEY_Alt_L, Gdk.KEY_Alt_R, 
            Gdk.KEY_Shift_L, Gdk.KEY_Shift_R, 
            Gdk.KEY_Super_L, Gdk.KEY_Super_R
        ]
        if is_mod:
            return True

        mods = []
        human_mods = []
        state = event.state
        if state & Gdk.ModifierType.CONTROL_MASK:
            mods.append("<Primary>")
            human_mods.append("Ctrl + ")
        if state & Gdk.ModifierType.MOD1_MASK:
            mods.append("<Alt>")
            human_mods.append("Alt + ")
        if state & Gdk.ModifierType.SHIFT_MASK:
            mods.append("<Shift>")
            human_mods.append("Shift + ")
        if state & Gdk.ModifierType.SUPER_MASK:
            mods.append("<Super>")
            human_mods.append("Super + ")

        if keyval == Gdk.KEY_BackSpace and not mods:
            widget.set_text("")
            self.current_raw_key = None
            return True

        key_name = Gdk.keyval_name(keyval)
        if not key_name:
            return True

        raw_key = "".join(mods) + key_name.lower()
        human_key = "".join(human_mods) + key_name.title()
        
        self.current_raw_key = raw_key
        widget.set_text(human_key)
        self.entry_cmd.grab_focus()
        return True

if __name__ == '__main__':
    win = KeyboardSettingsPanel()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
