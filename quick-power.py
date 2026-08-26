import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import subprocess
import sys

class QuickPower(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_app_paintable(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            
        self.setup_css()
        
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", self.on_focus_out)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_box.set_name("power_box")
        main_box.set_margin_top(50)
        main_box.set_margin_bottom(50)
        main_box.set_margin_start(60)
        main_box.set_margin_end(60)
        
        lbl_title = Gtk.Label(label="Menú de Energía")
        lbl_title.set_markup("<span weight='bold' foreground='#fafafa' size='x-large'>Opciones del Sistema</span>")
        main_box.pack_start(lbl_title, False, False, 10)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        
        btn_box.pack_start(self.make_action_btn("system-shutdown-symbolic", "Apagar", "systemctl poweroff"), False, False, 0)
        btn_box.pack_start(self.make_action_btn("view-refresh-symbolic", "Reiniciar", "systemctl reboot"), False, False, 0)
        btn_box.pack_start(self.make_action_btn("system-log-out-symbolic", "Cerrar Sesión", "pkill xfce4-session"), False, False, 0)
        btn_box.pack_start(self.make_action_btn("system-users-symbolic", "Cambiar Perfil", "dm-tool switch-to-greeter"), False, False, 0)
        
        main_box.pack_start(btn_box, False, False, 0)
        
        self.add(main_box)
        self.show_all()
        
        # Grab focus
        self.present()

    def make_action_btn(self, icon_name, label_text, cmd):
        btn = Gtk.Button()
        btn.set_name("power_btn")
        btn.set_can_focus(False)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(30)
        vbox.set_margin_bottom(30)
        vbox.set_margin_start(30)
        vbox.set_margin_end(30)
        
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
        Gtk.main_quit()
        
    def on_focus_out(self, widget, event):
        Gtk.main_quit()
        return False

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
        return False

    def setup_css(self):
        css = b"""
        #power_box {
            background-color: rgba(20, 20, 20, 0.85);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
        }
        #power_btn {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            border: 1px solid transparent;
            color: #fafafa;
        }
        #power_btn:hover {
            background-color: rgba(255, 255, 255, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.3);
            transition: all 0.2s ease;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

if __name__ == '__main__':
    win = QuickPower()
    Gtk.main()
