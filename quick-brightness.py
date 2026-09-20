import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import subprocess
import sys
import os

class QuickBrightness(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_app_paintable(True)
        
        # Position near the pill widget (bottom right)
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        
        self.set_default_size(300, 80)
        self.move(geometry.width - 320, geometry.height - 160)
        
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            
        self.setup_css()
        
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", self.on_focus_out)
        self.connect("map-event", self.on_map)
        self.connect("unmap-event", self.on_unmap)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self.on_button_press)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        main_box.set_name("bright_box")
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        
        icon = Gtk.Image.new_from_icon_name("display-brightness-symbolic", Gtk.IconSize.DND)
        main_box.pack_start(icon, False, False, 0)
        
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 5, 100, 5)
        self.scale.set_name("bright_scale")
        self.scale.set_draw_value(False)
        self.scale.set_hexpand(True)
        
        # Get current brightness
        try:
            curr = float(subprocess.check_output(["brightnessctl", "get"]).decode().strip())
            m = float(subprocess.check_output(["brightnessctl", "max"]).decode().strip())
            pct = int((curr / m) * 100)
            self.scale.set_value(pct)
        except:
            self.scale.set_value(100)
            
        self.scale.connect("value-changed", self.on_scale_changed)
        
        main_box.pack_start(self.scale, True, True, 0)
        
        self.add(main_box)
        self.show_all()
        self.present()

    def on_scale_changed(self, scale):
        val = int(scale.get_value())
        subprocess.Popen(["brightnessctl", "set", f"{val}%"])
        
    def on_focus_out(self, widget, event):
        Gtk.main_quit()
        return False

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
        return False

    def setup_css(self):
        css = b"""
        window { background-color: transparent; }
        #bright_box {
            background-color: #18181b;
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 24px;
        }
        scale trough {
            background-color: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            min-height: 8px;
        }
        scale highlight {
            background-color: #fafafa;
            border-radius: 10px;
        }
        scale slider {
            min-width: 16px;
            min-height: 16px;
            background-color: #fafafa;
            border-radius: 50%;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


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

if __name__ == '__main__':
    win = QuickBrightness()
    Gtk.main()
