#!/usr/bin/env python3
import sys
import os
import subprocess
import dbus
import dbus.service
import dbus.mainloop.glib
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf
import cairo

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

MEDIA_APPS = [
    "spotify", "rhythmbox", "vlc", "mpv", "audacious", "clementine",
    "cantata", "lollypop", "elisa", "strawberry", "deadbeef",
    "org.gnome.rhythmbox3", "org.gnome.music", "org.kde.elisa"
]

def is_media_notification(app_name, hints):
    name = app_name.lower()
    for media_app in MEDIA_APPS:
        if media_app in name:
            return True
    if "mpris" in str(hints).lower():
        return True
    return False

def run_playerctl(cmd):
    try:
        subprocess.Popen(["playerctl"] + cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
    except Exception:
        pass

def pixbuf_from_hint(image_data):
    """Convert MPRIS image-data hint (tuple) to GdkPixbuf."""
    try:
        width, height, rowstride, has_alpha, bps, channels, data = image_data
        data_bytes = bytes(bytearray(data))
        pixbuf = GdkPixbuf.Pixbuf.new_from_data(
            data_bytes,
            GdkPixbuf.Colorspace.RGB,
            has_alpha,
            bps,
            width,
            height,
            rowstride
        )
        return pixbuf
    except Exception:
        return None


class MediaNotificationWindow(Gtk.Window):
    """Premium music player card with album art and controls."""
    
    def __init__(self, id, app_name, summary, body, hints, on_close_callback):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.id = id
        self.app_name = app_name
        self.on_close_callback = on_close_callback
        self.timeout_id = None
        self.animating = False

        self.set_default_size(380, -1)
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.connect("draw", self.on_draw)

        # --- Layout ---
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_margin_top(14)
        outer.set_margin_bottom(14)
        outer.set_margin_start(14)
        outer.set_margin_end(14)
        self.add(outer)

        # App label (e.g. "Spotify")
        app_label = Gtk.Label()
        app_label.set_markup(f"<span font='8' color='#888888'>{GLib.markup_escape_text(app_name.title())}</span>")
        app_label.set_halign(Gtk.Align.START)
        outer.pack_start(app_label, False, False, 0)

        # Row: album art + info
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        row.set_margin_top(8)
        outer.pack_start(row, False, False, 0)

        # Album art
        self.album_art = Gtk.Image()
        self.album_art.set_size_request(64, 64)
        art_box = Gtk.Box()
        art_box.set_size_request(64, 64)
        art_box.pack_start(self.album_art, True, True, 0)
        row.pack_start(art_box, False, False, 0)
        self._set_art(hints, None)

        # Song info + controls
        info_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_col.set_valign(Gtk.Align.CENTER)
        row.pack_start(info_col, True, True, 0)

        self.lbl_title = Gtk.Label()
        self.lbl_title.set_halign(Gtk.Align.START)
        self.lbl_title.set_markup(f"<b><span font='14' color='#ffffff'>{GLib.markup_escape_text(summary)}</span></b>")
        self.lbl_title.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_title.set_max_width_chars(22)
        info_col.pack_start(self.lbl_title, False, False, 0)

        self.lbl_artist = Gtk.Label()
        self.lbl_artist.set_halign(Gtk.Align.START)
        self.lbl_artist.set_markup(f"<span font='12' color='#aaaaaa'>{GLib.markup_escape_text(body)}</span>")
        self.lbl_artist.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_artist.set_max_width_chars(22)
        info_col.pack_start(self.lbl_artist, False, False, 0)

        # Controls row
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls.set_margin_top(8)
        info_col.pack_start(controls, False, False, 0)

        self.btn_prev = self._make_ctrl_btn("media-skip-backward-symbolic", self.on_prev)
        self.btn_play = self._make_ctrl_btn("media-playback-pause-symbolic", self.on_play_pause)
        self.btn_next = self._make_ctrl_btn("media-skip-forward-symbolic", self.on_next)

        controls.pack_start(self.btn_prev, False, False, 0)
        controls.pack_start(self.btn_play, False, False, 0)
        controls.pack_start(self.btn_next, False, False, 0)

        # Position
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        self.start_x = geometry.x + 20
        self.base_y = geometry.y + 20
        self.target_y = self.base_y
        self.move(self.start_x, self.target_y)

        self.show_all()
        self.timeout_id = GLib.timeout_add(8000, self.auto_close)

    def _make_ctrl_btn(self, icon_name, callback):
        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
        btn.add(img)
        btn.connect("clicked", lambda w: callback())
        btn.set_size_request(36, 36)
        # Style
        css = f"""
        button {{ background: rgba(255,255,255,0.1); border-radius: 18px; border: none; padding: 4px; }}
        button:hover {{ background: rgba(255,255,255,0.22); }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        btn.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        return btn

    def _set_art(self, hints, icon_str):
        """Try to load album art from hints or icon path."""
        try:
            if "image-data" in hints:
                pixbuf = pixbuf_from_hint(hints["image-data"])
                if pixbuf:
                    pixbuf = pixbuf.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)
                    self.album_art.set_from_pixbuf(pixbuf)
                    return
            if "image-path" in hints:
                path = str(hints["image-path"])
                if os.path.exists(path):
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 64, 64, True)
                    self.album_art.set_from_pixbuf(pixbuf)
                    return
        except Exception:
            pass
        if icon_str and icon_str.startswith("/") and os.path.exists(icon_str):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_str, 64, 64, True)
                self.album_art.set_from_pixbuf(pixbuf)
                return
            except Exception:
                pass
        self.album_art.set_from_icon_name("audio-x-generic-symbolic", Gtk.IconSize.DIALOG)

    def on_prev(self):
        run_playerctl(["previous"])
        self._reset_timeout()

    def on_play_pause(self):
        run_playerctl(["play-pause"])
        self._reset_timeout()

    def on_next(self):
        run_playerctl(["next"])
        self._reset_timeout()

    def _reset_timeout(self):
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
        self.timeout_id = GLib.timeout_add(8000, self.auto_close)

    def update_content(self, summary, body, hints=None, icon_str=None):
        self.lbl_title.set_markup(f"<b><span font='14' color='#ffffff'>{GLib.markup_escape_text(summary)}</span></b>")
        self.lbl_artist.set_markup(f"<span font='12' color='#aaaaaa'>{GLib.markup_escape_text(body)}</span>")
        if hints:
            self._set_art(hints, icon_str)
        self._reset_timeout()

    def on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()

        w = self.get_allocated_width()
        h = self.get_allocated_height()
        r = 16.0

        # Background
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgba(18/255, 18/255, 22/255, 0.96)
        cr.move_to(r, 0)
        cr.line_to(w - r, 0)
        cr.arc(w - r, r, r, -1.5708, 0)
        cr.line_to(w, h - r)
        cr.arc(w - r, h - r, r, 0, 1.5708)
        cr.line_to(r, h)
        cr.arc(r, h - r, r, 1.5708, 3.1416)
        cr.line_to(0, r)
        cr.arc(r, r, r, 3.1416, 4.7124)
        cr.close_path()
        cr.fill()

        # Border
        cr.set_source_rgba(1, 1, 1, 0.08)
        cr.set_line_width(1.0)
        cr.move_to(r, 0)
        cr.line_to(w - r, 0)
        cr.arc(w - r, r, r, -1.5708, 0)
        cr.line_to(w, h - r)
        cr.arc(w - r, h - r, r, 0, 1.5708)
        cr.line_to(r, h)
        cr.arc(r, h - r, r, 1.5708, 3.1416)
        cr.line_to(0, r)
        cr.arc(r, r, r, 3.1416, 4.7124)
        cr.close_path()
        cr.stroke()

        # Left accent bar
        cr.set_source_rgba(29/255, 185/255, 84/255, 0.9)  # Spotify green
        cr.rectangle(0, r, 3, h - 2*r)
        cr.fill()

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


class NotificationWindow(Gtk.Window):
    """Standard notification for non-media apps."""

    def __init__(self, id, app_name, summary, body, on_close_callback):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.id = id
        self.app_name = app_name
        self.count = 1
        self.on_close_callback = on_close_callback
        self.timeout_id = None
        self.animating = False

        self.set_default_size(360, -1)
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.event_box = Gtk.EventBox()
        self.add(self.event_box)
        self.event_box.connect("button-press-event", self.on_click)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.main_box.set_margin_top(14)
        self.main_box.set_margin_bottom(14)
        self.main_box.set_margin_start(16)
        self.main_box.set_margin_end(16)
        self.event_box.add(self.main_box)

        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.main_box.pack_start(self.hbox, False, False, 0)

        self.img_icon = Gtk.Image()
        self.img_icon.set_pixel_size(28)
        self.hbox.pack_start(self.img_icon, False, False, 0)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.hbox.pack_start(self.vbox, True, True, 0)

        self.lbl_title = Gtk.Label()
        self.lbl_title.set_halign(Gtk.Align.START)
        self.lbl_title.set_markup(f"<b><span color='#ffffff' font='13'>{GLib.markup_escape_text(summary)}</span></b>")
        self.lbl_title.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_title.set_max_width_chars(30)
        self.vbox.pack_start(self.lbl_title, False, False, 0)

        self.lbl_body = Gtk.Label()
        self.lbl_body.set_halign(Gtk.Align.START)
        self.lbl_body.set_valign(Gtk.Align.START)
        display_body = body[:115] + "..." if len(body) > 115 else body
        self.lbl_body.set_markup(f"<span color='#999999' font='12'>{GLib.markup_escape_text(display_body)}</span>")
        self.lbl_body.set_line_wrap(True)
        self.lbl_body.set_lines(2)
        self.lbl_body.set_ellipsize(Pango.EllipsizeMode.END)
        self.vbox.pack_start(self.lbl_body, False, False, 0)

        self.full_summary = summary
        self.full_body = body

        self.connect("draw", self.on_draw)

        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        self.start_x = geometry.x + 20
        self.base_y = geometry.y + 20
        self.target_y = self.base_y
        self.move(self.start_x, self.target_y)
        self.show_all()

        self.timeout_id = GLib.timeout_add(7000, self.auto_close)

    def on_click(self, widget, event):
        self.close_now()
        self.on_close_callback(self.id)
        return True

    def on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()

        w = self.get_allocated_width()
        h = self.get_allocated_height()
        r = 14.0

        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgba(20/255, 20/255, 24/255, 0.96)
        cr.move_to(r, 0)
        cr.line_to(w - r, 0)
        cr.arc(w - r, r, r, -1.5708, 0)
        cr.line_to(w, h - r)
        cr.arc(w - r, h - r, r, 0, 1.5708)
        cr.line_to(r, h)
        cr.arc(r, h - r, r, 1.5708, 3.1416)
        cr.line_to(0, r)
        cr.arc(r, r, r, 3.1416, 4.7124)
        cr.close_path()
        cr.fill()

        cr.set_source_rgba(1, 1, 1, 0.07)
        cr.set_line_width(1.0)
        cr.move_to(r, 0)
        cr.line_to(w - r, 0)
        cr.arc(w - r, r, r, -1.5708, 0)
        cr.line_to(w, h - r)
        cr.arc(w - r, h - r, r, 0, 1.5708)
        cr.line_to(r, h)
        cr.arc(r, h - r, r, 1.5708, 3.1416)
        cr.line_to(0, r)
        cr.arc(r, r, r, 3.1416, 4.7124)
        cr.close_path()
        cr.stroke()

    def update_content(self, summary, body, hints=None, icon_str=None):
        self.count += 1
        self.full_summary = summary
        self.full_body = body
        self.lbl_title.set_markup(
            f"<b><span color='#ffffff' font='13'>{GLib.markup_escape_text(summary)}</span></b>"
            + (f" <span color='#5b9bd5' font='11'>[x{self.count}]</span>" if self.count > 1 else "")
        )
        display_body = body[:115] + "..." if len(body) > 115 else body
        self.lbl_body.set_markup(f"<span color='#999999' font='12'>{GLib.markup_escape_text(display_body)}</span>")
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
        self.timeout_id = GLib.timeout_add(7000, self.auto_close)

    def set_icon(self, icon_str):
        if not icon_str:
            self.img_icon.hide()
            return
        self.img_icon.show()
        if icon_str.startswith('/') and os.path.exists(icon_str):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_str, 28, 28, True)
                self.img_icon.set_from_pixbuf(pixbuf)
                return
            except Exception:
                pass
        self.img_icon.set_from_icon_name(icon_str or "dialog-information", Gtk.IconSize.DND)

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
        self.windows = []

    @dbus.service.method('org.freedesktop.Notifications', out_signature='ssss')
    def GetServerInformation(self):
        return ("QuickNotifications", "QuickPanel", "2.0", "1.2")

    @dbus.service.method('org.freedesktop.Notifications', out_signature='as')
    def GetCapabilities(self):
        return ["body", "body-markup", "icon-static", "actions"]

    @dbus.service.method('org.freedesktop.Notifications', in_signature='u')
    def CloseNotification(self, id):
        self.on_window_closed(id, from_dbus=True)

    @dbus.service.method('org.freedesktop.Notifications',
                         in_signature='susssasa{sv}i', out_signature='u')
    def Notify(self, app_name, replaces_id, app_icon, summary, body,
               actions, hints, expire_timeout):
        app_name_str = str(app_name)
        summary_str = str(summary)

        # Block volume OSD duplicates
        if app_name_str in ["xfce4-pulseaudio-plugin", "xfce4-volumed"]:
            if summary_str.lower().startswith(("volumen", "volume")):
                return self.next_id
        if summary_str.lower().startswith(("volumen:", "volume:")):
            return self.next_id

        icon_str = str(app_icon)
        media = is_media_notification(app_name_str, hints)

        # Check if same app already has a notification
        for win in self.windows:
            if win.app_name == app_name_str:
                win.update_content(summary_str, str(body), hints, icon_str)
                GLib.timeout_add(50, self.update_positions)
                return win.id

        # Remove oldest if at capacity
        if len(self.windows) >= 3:
            oldest = self.windows.pop(0)
            oldest.close_now()

        nid = self.next_id
        self.next_id += 1

        if media:
            new_win = MediaNotificationWindow(
                nid, app_name_str, summary_str, str(body), hints, self.on_window_closed
            )
        else:
            new_win = NotificationWindow(
                nid, app_name_str, summary_str, str(body), self.on_window_closed
            )
            new_win.set_icon(icon_str)

        self.windows.append(new_win)
        GLib.timeout_add(50, self.update_positions)
        return nid

    def update_positions(self):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        current_y = geometry.y + 20
        spacing = 12
        for win in self.windows:
            win.slide_to_y(current_y)
            h = win.get_allocated_height()
            current_y += (h if h > 50 else 90) + spacing
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
