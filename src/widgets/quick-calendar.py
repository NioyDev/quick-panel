#!/usr/bin/env python3
import gi
import datetime
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

class QuickCalendar(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            
        self.setup_css()
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.main_box.set_name("cal_box")
        
        # Header (Time and Date)
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
        
        # Calendar Grid
        self.calendar = Gtk.Calendar()
        self.calendar.set_name("calendar_grid")
        self.main_box.pack_start(self.calendar, True, True, 0)
        
        self.add(self.main_box)
        
        self.connect("focus-out-event", lambda *args: Gtk.main_quit())
        self.connect("map-event", self.on_map)
        self.connect("unmap-event", self.on_unmap)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self.on_button_press)
        self.connect("key-press-event", self.on_key_press)
        
        GLib.timeout_add_seconds(1, self.update_time)
        self.update_time()
        
        GLib.idle_add(self.position_window)

    def update_time(self):
        now = datetime.datetime.now()
        hour12 = now.hour % 12
        if hour12 == 0: hour12 = 12
        ampm = "AM" if now.hour < 12 else "PM"
        
        self.lbl_time.set_markup(f"<span weight='bold' size='24000'>{hour12}:{now.strftime('%M')} {ampm}</span>")
        self.lbl_date.set_markup(f"<span weight='bold' size='14000'>{now.strftime('%m/%d')}</span>")
        return True

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

    def position_window(self):
        geometry = Gdk.Display.get_default().get_primary_monitor().get_geometry()
        width, height = self.get_size()
        x = geometry.width - width - 100
        y = geometry.height - height - 60
        self.move(x, y)
        self.present()
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
        calendar {
            background-color: #18181b;
            color: #fafafa;
        }
        calendar:selected {
            background-color: #ef4444;
            color: #ffffff;
            border-radius: 4px;
        }
        #time_label {
            color: #fafafa;
        }
        #date_label {
            color: #a1a1aa;
        }
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
    app = QuickCalendar()
    app.show_all()
    Gtk.main()
