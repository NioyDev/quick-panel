#!/usr/bin/env python3
import sys
import os
import dbus
import dbus.service
import dbus.mainloop.glib
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf
import cairo

# Create main loop
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

class NotificationWindow(Gtk.Window):
    def __init__(self, id, app_name, summary, body, slot_idx, on_close_callback):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.id = id
        self.app_name = app_name
        self.count = 1
        self.on_close_callback = on_close_callback
        
        self.set_default_size(350, -1)
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        
        # Transparent background
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            
        # EventBox to capture clicks
        self.event_box = Gtk.EventBox()
        self.add(self.event_box)
        self.event_box.connect("button-press-event", self.on_click)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.main_box.set_margin_top(12)
        self.main_box.set_margin_bottom(12)
        self.main_box.set_margin_start(12)
        self.main_box.set_margin_end(12)
        self.event_box.add(self.main_box)
        
        # Horizontal layout to hold icon and text
        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        self.main_box.pack_start(self.hbox, False, False, 0)
        
        # Icon
        self.img_icon = Gtk.Image()
        self.img_icon.set_pixel_size(32) # Standard size from design system
        self.hbox.pack_start(self.img_icon, False, False, 0)
        
        # Vertical box for text
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.hbox.pack_start(self.vbox, True, True, 0)
        
        self.lbl_title = Gtk.Label()
        self.lbl_title.set_halign(Gtk.Align.START)
        self.lbl_title.set_markup(f"<b>{GLib.markup_escape_text(summary)}</b>")
        self.lbl_title.set_line_wrap(True)
        self.lbl_title.set_name("lbl_title")
        self.vbox.pack_start(self.lbl_title, False, False, 0)
        
        self.lbl_body = Gtk.Label()
        self.lbl_body.set_halign(Gtk.Align.START)
        self.lbl_body.set_valign(Gtk.Align.START)
        
        display_body = body
        if len(display_body) > 115:
            display_body = display_body[:112] + "..."
            
        self.lbl_body.set_markup(GLib.markup_escape_text(display_body))
        self.lbl_body.set_line_wrap(True)
        self.lbl_body.set_lines(3)
        self.lbl_body.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_body.set_name("lbl_body")
        self.vbox.pack_start(self.lbl_body, False, False, 0)
        
        css = b'''
        #lbl_title {
            font-size: 14px;
            color: white;
        }
        #lbl_body {
            font-size: 13px;
            color: #aaaaaa;
        }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), 
            provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        self.connect("draw", self.on_draw)
        
        self.full_summary = summary
        self.full_body = body

        # Calculate initial position (will be animated by server)
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        
        self.start_x = geometry.x + 20
        self.base_y = geometry.y + 20
        self.target_y = self.base_y # updated dynamically
        
        self.move(self.start_x, self.target_y)
        self.show_all()
        
        # Auto close
        self.timeout_id = GLib.timeout_add(7000, self.auto_close)
        
        # Animation state
        self.animating = False

    def on_click(self, widget, event):
        # Open modal with full text
        self.open_modal()
        # Close notification
        self.close_now()
        self.on_close_callback(self.id)
        return True

    def open_modal(self):
        modal = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        modal.set_title("Notificación: " + self.app_name)
        modal.set_position(Gtk.WindowPosition.CENTER)
        modal.set_default_size(400, 300)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        modal.add(box)
        
        lbl_title = Gtk.Label()
        lbl_title.set_markup(f"<big><b>{GLib.markup_escape_text(self.full_summary)}</b></big>")
        lbl_title.set_line_wrap(True)
        lbl_title.set_selectable(True)
        box.pack_start(lbl_title, False, False, 0)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        box.pack_start(scroll, True, True, 0)
        
        lbl_body = Gtk.Label()
        lbl_body.set_markup(GLib.markup_escape_text(self.full_body))
        lbl_body.set_line_wrap(True)
        lbl_body.set_selectable(True)
        lbl_body.set_halign(Gtk.Align.START)
        lbl_body.set_valign(Gtk.Align.START)
        scroll.add(lbl_body)
        
        btn_close = Gtk.Button(label="Cerrar")
        btn_close.connect("clicked", lambda x: modal.destroy())
        box.pack_start(btn_close, False, False, 0)
        
        # Apply basic dark theme styling for modal
        css = b'''
        window { background-color: #1c1c1e; color: white; }
        button { background-color: #333; color: white; border-radius: 8px; padding: 8px; }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            modal.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        modal.show_all()

    def on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        radius = 12.0
        
        cr.set_source_rgba(28/255.0, 28/255.0, 30/255.0, 0.95)
        cr.set_operator(cairo.OPERATOR_OVER)
        
        cr.move_to(radius, 0)
        cr.line_to(width - radius, 0)
        cr.arc(width - radius, radius, radius, -1.570796, 0)
        cr.line_to(width, height - radius)
        cr.arc(width - radius, height - radius, radius, 0, 1.570796)
        cr.line_to(radius, height)
        cr.arc(radius, height - radius, radius, 1.570796, 3.141592)
        cr.line_to(0, radius)
        cr.arc(radius, radius, radius, 3.141592, 4.712389)
        cr.close_path()
        cr.fill()
        
        cr.set_source_rgba(1, 1, 1, 0.1)
        cr.set_line_width(1.0)
        cr.move_to(radius, 0)
        cr.line_to(width - radius, 0)
        cr.arc(width - radius, radius, radius, -1.570796, 0)
        cr.line_to(width, height - radius)
        cr.arc(width - radius, height - radius, radius, 0, 1.570796)
        cr.line_to(radius, height)
        cr.arc(radius, height - radius, radius, 1.570796, 3.141592)
        cr.line_to(0, radius)
        cr.arc(radius, radius, radius, 3.141592, 4.712389)
        cr.close_path()
        cr.stroke()

    def update_content(self, summary, body, app_icon=None):
        self.count += 1
        self.full_summary = summary
        self.full_body = body
        title_text = f"<b>{GLib.markup_escape_text(summary)}</b> <span color='#11a8cd'>[x{self.count}]</span>"
        self.lbl_title.set_markup(title_text)
        if body:
            display_body = body
            if len(display_body) > 115:
                display_body = display_body[:112] + "..."
            self.lbl_body.set_markup(GLib.markup_escape_text(display_body))
            
        if app_icon:
            self.set_icon(app_icon)
            
        # Reset timeout
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
        self.timeout_id = GLib.timeout_add(7000, self.auto_close)

    def set_icon(self, icon_str):
        if not icon_str:
            self.img_icon.hide()
            return
            
        self.img_icon.show()
        if icon_str.startswith('/'):
            # Absolute path
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_str, 32, 32, True)
                self.img_icon.set_from_pixbuf(pixbuf)
            except Exception:
                self.img_icon.set_from_icon_name("dialog-information", Gtk.IconSize.DND)
        else:
            # Icon name
            self.img_icon.set_from_icon_name(icon_str, Gtk.IconSize.DND)

    def slide_to_y(self, target_y):
        self.target_y = target_y
        if not self.animating:
            self.animating = True
            GLib.timeout_add(16, self._anim_step)
            
    def _anim_step(self):
        cur_x, cur_y = self.get_position()
        if abs(cur_y - self.target_y) <= 2:
            self.move(cur_x, self.target_y)
            self.animating = False
            return False
            
        # Smooth interpolation
        new_y = cur_y + (self.target_y - cur_y) * 0.2
        self.move(cur_x, int(new_y))
        return True

    def auto_close(self):
        self.timeout_id = None
        self.on_close_callback(self.id)
        self.destroy()
        return False
        
    def close_now(self):
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
        self.destroy()


class NotificationServer(dbus.service.Object):
    def __init__(self):
        bus_name = dbus.service.BusName('org.freedesktop.Notifications', bus=dbus.SessionBus())
        super().__init__(bus_name, '/org/freedesktop/Notifications')
        
        self.next_id = 1
        # List of active windows, ordered by slot (0 is top, 1 is bottom)
        self.windows = []

    @dbus.service.method('org.freedesktop.Notifications', out_signature='ssss')
    def GetServerInformation(self):
        return ("Win11Notifications", "Antigravity", "1.0", "1.2")

    @dbus.service.method('org.freedesktop.Notifications', out_signature='as')
    def GetCapabilities(self):
        return ["body", "body-markup"]

    @dbus.service.method('org.freedesktop.Notifications', in_signature='u')
    def CloseNotification(self, id):
        self.on_window_closed(id, from_dbus=True)

    @dbus.service.method('org.freedesktop.Notifications', in_signature='susssasa{sv}i', out_signature='u')
    def Notify(self, app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout):
        # Ignore XFCE internal volume notifications to avoid conflict with win11-osd
        app_name_str = str(app_name)
        summary_str = str(summary)
        
        if app_name_str in ["xfce4-pulseaudio-plugin", "xfce4-volumed", "Xfce volume control", "volume", "notify-send"]:
            if summary_str.lower().startswith("volumen") or summary_str.lower().startswith("volume"):
                return self.next_id
        
        # Also block if it just says Volumen
        if summary_str.lower().startswith("volumen:") or summary_str.lower().startswith("volume:"):
             return self.next_id
             
        # 1. Check if an app already has a notification
        icon_str = str(app_icon)
        for win in self.windows:
            if win.app_name == app_name_str:
                win.update_content(str(summary), str(body), icon_str)
                GLib.timeout_add(50, self.update_positions)
                return win.id
                
        # 2. It's a new app. If we are at capacity (2), remove the oldest (slot 0)
        if len(self.windows) >= 2:
            oldest = self.windows.pop(0)
            oldest.close_now()
                
        # 3. Add the new notification
        nid = self.next_id
        self.next_id += 1
        
        new_win = NotificationWindow(nid, app_name_str, str(summary), str(body), 0, self.on_window_closed)
        new_win.set_icon(icon_str)
        self.windows.append(new_win)
        
        # Give GTK a tiny moment to calculate the new window's height before sliding others
        GLib.timeout_add(50, self.update_positions)
        
        return nid

    def update_positions(self):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        
        current_y = geometry.y + 20
        spacing = 15
        
        for win in self.windows:
            win.slide_to_y(current_y)
            # Wait for layout to calculate height
            height = win.get_allocated_height()
            if height < 50:
                height = 80 # Fallback before first draw
            current_y += height + spacing
        return False

    def on_window_closed(self, closed_id, from_dbus=False):
        for i, win in enumerate(self.windows):
            if win.id == closed_id:
                if from_dbus:
                    win.close_now()
                self.windows.pop(i)
                self.update_positions()
                break

if __name__ == '__main__':
    server = NotificationServer()
    Gtk.main()
