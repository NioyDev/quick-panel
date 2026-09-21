#!/usr/bin/env python3
"""
quick-notifications.py - Sistema de notificaciones premium para Quick Panel
Tarjeta de música estilo elegante con bordes redondeados, portada a la izquierda,
progreso acentuado y controles integrados.
"""
import sys
import os
import subprocess
import dbus
import dbus.service
import dbus.mainloop.glib
import gi
import math

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf
import cairo

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

MEDIA_APPS = [
    "spotify", "rhythmbox", "vlc", "mpv", "audacious", "clementine",
    "cantata", "lollypop", "elisa", "strawberry", "deadbeef",
    "org.gnome.rhythmbox3", "org.gnome.music", "org.kde.elisa",
    "nuclear", "museeks", "cider"
]

def is_media_notification(app_name, hints):
    name = app_name.lower()
    for media_app in MEDIA_APPS:
        if media_app in name:
            return True
    return False

def run_playerctl(cmd):
    try:
        subprocess.Popen(["playerctl"] + cmd,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except Exception:
        pass

def get_playerctl_value(cmd):
    try:
        result = subprocess.run(
            ["playerctl"] + cmd,
            capture_output=True, text=True, timeout=1
        )
        return result.stdout.strip()
    except Exception:
        return ""

def pixbuf_from_hint(image_data):
    try:
        width, height, rowstride, has_alpha, bps, channels, data = image_data
        data_bytes = bytes(bytearray(data))
        return GdkPixbuf.Pixbuf.new_from_data(
            data_bytes, GdkPixbuf.Colorspace.RGB,
            has_alpha, bps, width, height, rowstride
        )
    except Exception:
        return None

def format_time(microseconds):
    try:
        secs = int(float(microseconds)) // 1000000
        m, s = divmod(secs, 60)
        return f"{m}:{s:02d}"
    except Exception:
        return "0:00"

def draw_rounded_rect(cr, x, y, w, h, r):
    cr.move_to(x + r, y)
    cr.line_to(x + w - r, y)
    cr.arc(x + w - r, y + r, r, -math.pi/2, 0)
    cr.line_to(x + w, y + h - r)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi/2)
    cr.line_to(x + r, y + h)
    cr.arc(x + r, y + h - r, r, math.pi/2, math.pi)
    cr.line_to(x, y + r)
    cr.arc(x + r, y + r, r, math.pi, 3*math.pi/2)
    cr.close_path()


class MediaNotificationWindow(Gtk.Window):
    """Tarjeta de música estilo player moderno con bordes redondeados."""

    CARD_W = 450
    ART_SIZE = 96

    def __init__(self, id, app_name, summary, body, hints, on_close_callback):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.id = id
        self.app_name = app_name
        self.on_close_callback = on_close_callback
        self.timeout_id = None
        self.progress_timer = None
        self.animating = False
        self._duration_us = 0
        self._position_us = 0
        self._art_pixbuf = None
        self._progress_fraction = 0.0
        self._is_playing = True

        self.set_default_size(self.CARD_W, -1)
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

        # Outer Horizontal Box: [ Album Cover ] [ Info + Progress + Controls ]
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        outer.set_margin_top(16)
        outer.set_margin_bottom(16)
        outer.set_margin_start(16)
        outer.set_margin_end(16)
        self.add(outer)

        # 1. Left: Album art with rounded corners
        self.art_area = Gtk.DrawingArea()
        self.art_area.set_size_request(self.ART_SIZE, self.ART_SIZE)
        self.art_area.set_valign(Gtk.Align.CENTER)
        self.art_area.connect("draw", self.draw_album_art)
        outer.pack_start(self.art_area, False, False, 0)

        # 2. Right: Content column
        right_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        right_col.set_valign(Gtk.Align.CENTER)
        outer.pack_start(right_col, True, True, 0)

        # Artist / App Subtitle (muted small caps)
        artist_text = (body if body else app_name).upper()
        self.lbl_artist = Gtk.Label()
        self.lbl_artist.set_halign(Gtk.Align.START)
        self.lbl_artist.set_markup(
            f"<span font='9' weight='bold' color='#a1a1aa'>"
            f"{GLib.markup_escape_text(artist_text)}</span>"
        )
        self.lbl_artist.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_artist.set_max_width_chars(25)
        right_col.pack_start(self.lbl_artist, False, False, 0)

        # Song Title (prominent bold white)
        self.lbl_title = Gtk.Label()
        self.lbl_title.set_halign(Gtk.Align.START)
        self.lbl_title.set_markup(
            f"<span font='13' weight='bold' color='#ffffff'>"
            f"{GLib.markup_escape_text(summary)}</span>"
        )
        self.lbl_title.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_title.set_max_width_chars(25)
        right_col.pack_start(self.lbl_title, False, False, 0)

        # Progress bar container
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        progress_box.set_margin_top(4)
        right_col.pack_start(progress_box, False, False, 0)

        self.progress_area = Gtk.DrawingArea()
        self.progress_area.set_size_request(-1, 5)
        self.progress_area.connect("draw", self.draw_progress)
        progress_box.pack_start(self.progress_area, False, False, 0)

        time_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        progress_box.pack_start(time_row, False, False, 0)

        self.lbl_pos = Gtk.Label()
        self.lbl_pos.set_markup("<span font='9' color='#71717a'>0:00</span>")
        self.lbl_pos.set_halign(Gtk.Align.START)
        time_row.pack_start(self.lbl_pos, True, True, 0)

        self.lbl_dur = Gtk.Label()
        self.lbl_dur.set_markup("<span font='9' color='#71717a'>0:00</span>")
        self.lbl_dur.set_halign(Gtk.Align.END)
        time_row.pack_end(self.lbl_dur, False, False, 0)

        # Controls row centered at bottom right
        ctrl_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        ctrl_row.set_halign(Gtk.Align.CENTER)
        ctrl_row.set_margin_top(4)
        right_col.pack_start(ctrl_row, False, False, 0)

        self.btn_prev = self._make_ctrl_btn("media-skip-backward-symbolic", self.on_prev, 36)
        self.btn_play = self._make_ctrl_btn("media-playback-pause-symbolic", self.on_play_pause, 42)
        self.btn_next = self._make_ctrl_btn("media-skip-forward-symbolic", self.on_next, 36)

        ctrl_row.pack_start(self.btn_prev, False, False, 0)
        ctrl_row.pack_start(self.btn_play, False, False, 0)
        ctrl_row.pack_start(self.btn_next, False, False, 0)

        # Init art and position
        self._load_art(hints, None)
        self._fetch_progress()

        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        self.start_x = geometry.x + 20
        self.base_y = geometry.y + 20
        self.target_y = self.base_y
        self.move(self.start_x, self.target_y)
        self.show_all()

        self.timeout_id = GLib.timeout_add(12000, self.auto_close)
        self.progress_timer = GLib.timeout_add(1000, self._tick_progress)

    def _load_art(self, hints, icon_str):
        pixbuf = None
        try:
            if hints and "image-data" in hints:
                pixbuf = pixbuf_from_hint(hints["image-data"])
            elif hints and "image-path" in hints:
                path = str(hints["image-path"])
                if os.path.exists(path):
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        except Exception:
            pass
        if pixbuf is None and icon_str and icon_str.startswith("/") and os.path.exists(icon_str):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_str)
            except Exception:
                pass
        if pixbuf:
            self._art_pixbuf = pixbuf.scale_simple(
                self.ART_SIZE, self.ART_SIZE, GdkPixbuf.InterpType.BILINEAR
            )

    def draw_album_art(self, widget, cr):
        w = h = self.ART_SIZE
        r = 14.0
        draw_rounded_rect(cr, 0, 0, w, h, r)
        cr.clip()

        if self._art_pixbuf:
            Gdk.cairo_set_source_pixbuf(cr, self._art_pixbuf, 0, 0)
            cr.paint()
        else:
            grad = cairo.LinearGradient(0, 0, w, h)
            grad.add_color_stop_rgb(0, 0.22, 0.18, 0.32)
            grad.add_color_stop_rgb(1, 0.12, 0.12, 0.20)
            cr.set_source(grad)
            cr.paint()

            cr.set_source_rgba(1, 1, 1, 0.4)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(36)
            cr.move_to(32, 60)
            cr.show_text("♫")

        return False

    def _fetch_progress(self):
        try:
            pos = get_playerctl_value(["position"])
            dur = get_playerctl_value(["metadata", "mpris:length"])
            if pos and dur:
                pos_us = float(pos) * 1_000_000
                dur_us = float(dur)
                self._position_us = pos_us
                self._duration_us = dur_us
                if dur_us > 0:
                    self._progress_fraction = min(1.0, pos_us / dur_us)
                self.lbl_pos.set_markup(
                    f"<span font='9' color='#71717a'>{format_time(pos_us)}</span>"
                )
                self.lbl_dur.set_markup(
                    f"<span font='9' color='#71717a'>{format_time(dur_us)}</span>"
                )
        except Exception:
            pass
        self.progress_area.queue_draw()

    def _tick_progress(self):
        if self._duration_us > 0 and self._is_playing:
            self._position_us += 1_000_000
            self._progress_fraction = min(1.0, self._position_us / self._duration_us)
            self.lbl_pos.set_markup(
                f"<span font='9' color='#71717a'>{format_time(self._position_us)}</span>"
            )
            self.progress_area.queue_draw()
        return True

    def draw_progress(self, widget, cr):
        w = widget.get_allocated_width()
        h = 5

        # Track background
        cr.set_source_rgba(1, 1, 1, 0.15)
        draw_rounded_rect(cr, 0, 0, w, h, 2.5)
        cr.fill()

        # Fill track with accent coral/pink
        fill_w = int(w * self._progress_fraction)
        if fill_w > 4:
            cr.set_source_rgba(244/255, 114/255, 182/255, 0.95)
            draw_rounded_rect(cr, 0, 0, fill_w, h, 2.5)
            cr.fill()

        return False

    def _make_ctrl_btn(self, icon_name, callback, size):
        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.INVALID)
        img.set_pixel_size(size - 16)
        btn.add(img)
        btn.connect("clicked", lambda w: callback())
        btn.set_size_request(size, size)
        css = f"""
        button {{
            background: rgba(255, 255, 255, 0.08);
            border-radius: {size//2}px;
            border: none;
            padding: 0;
        }}
        button:hover {{
            background: rgba(255, 255, 255, 0.18);
        }}
        button:active {{
            background: rgba(255, 255, 255, 0.28);
        }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        btn.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        return btn

    def on_prev(self):
        run_playerctl(["previous"])
        GLib.timeout_add(300, self._fetch_progress)
        self._reset_timeout()

    def on_play_pause(self):
        self._is_playing = not self._is_playing
        run_playerctl(["play-pause"])
        self._reset_timeout()

    def on_next(self):
        run_playerctl(["next"])
        GLib.timeout_add(300, self._fetch_progress)
        self._reset_timeout()

    def _reset_timeout(self):
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
        self.timeout_id = GLib.timeout_add(12000, self.auto_close)

    def update_content(self, summary, body, hints=None, icon_str=None):
        artist_text = (body if body else self.app_name).upper()
        self.lbl_artist.set_markup(
            f"<span font='9' weight='bold' color='#a1a1aa'>"
            f"{GLib.markup_escape_text(artist_text)}</span>"
        )
        self.lbl_title.set_markup(
            f"<span font='13' weight='bold' color='#ffffff'>"
            f"{GLib.markup_escape_text(summary)}</span>"
        )
        if hints:
            self._load_art(hints, icon_str)
            self.art_area.queue_draw()
        GLib.timeout_add(300, self._fetch_progress)
        self._reset_timeout()

    def on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()

        w = self.get_allocated_width()
        h = self.get_allocated_height()
        r = 20.0

        cr.set_operator(cairo.OPERATOR_OVER)

        # Background (dark graphite with 96% opacity)
        cr.set_source_rgba(24/255, 24/255, 27/255, 0.96)
        draw_rounded_rect(cr, 0, 0, w, h, r)
        cr.fill()

        # Border
        cr.set_source_rgba(1, 1, 1, 0.1)
        cr.set_line_width(1.0)
        draw_rounded_rect(cr, 0.5, 0.5, w - 1, h - 1, r)
        cr.stroke()

        return False

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
        self.move(cur_x, int(cur_y + (self.target_y - cur_y) * 0.2))
        return True

    def auto_close(self):
        self.timeout_id = None
        if self.progress_timer:
            GLib.source_remove(self.progress_timer)
        self.on_close_callback(self.id)
        self.destroy()
        return False

    def close_now(self):
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
        if self.progress_timer:
            GLib.source_remove(self.progress_timer)
        self.destroy()


class NotificationWindow(Gtk.Window):
    """Tarjeta de notificación estándar (apps no-media)."""

    def __init__(self, id, app_name, summary, body, on_close_callback):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.id = id
        self.app_name = app_name
        self.count = 1
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

        self.event_box = Gtk.EventBox()
        self.add(self.event_box)
        self.event_box.connect("button-press-event", self.on_click)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.set_margin_top(14)
        main_box.set_margin_bottom(14)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        self.event_box.add(main_box)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        main_box.pack_start(hbox, False, False, 0)

        self.img_icon = Gtk.Image()
        self.img_icon.set_pixel_size(28)
        hbox.pack_start(self.img_icon, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        hbox.pack_start(vbox, True, True, 0)

        self.lbl_title = Gtk.Label()
        self.lbl_title.set_halign(Gtk.Align.START)
        self.lbl_title.set_markup(
            f"<span font='13' weight='bold' color='#ffffff'>"
            f"{GLib.markup_escape_text(summary)}</span>"
        )
        self.lbl_title.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_title.set_max_width_chars(30)
        vbox.pack_start(self.lbl_title, False, False, 0)

        self.full_body = body
        display_body = body[:115] + "..." if len(body) > 115 else body
        self.lbl_body = Gtk.Label()
        self.lbl_body.set_halign(Gtk.Align.START)
        self.lbl_body.set_markup(
            f"<span font='12' color='#a1a1aa'>{GLib.markup_escape_text(display_body)}</span>"
        )
        self.lbl_body.set_line_wrap(True)
        self.lbl_body.set_lines(2)
        self.lbl_body.set_ellipsize(Pango.EllipsizeMode.END)
        vbox.pack_start(self.lbl_body, False, False, 0)

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
        r = 20.0

        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgba(24/255, 24/255, 27/255, 0.96)
        draw_rounded_rect(cr, 0, 0, w, h, r)
        cr.fill()

        cr.set_source_rgba(1, 1, 1, 0.1)
        cr.set_line_width(1.0)
        draw_rounded_rect(cr, 0.5, 0.5, w - 1, h - 1, r)
        cr.stroke()

    def update_content(self, summary, body, hints=None, icon_str=None):
        self.count += 1
        suffix = f" <span color='#60a5fa' font='11'>[x{self.count}]</span>" if self.count > 1 else ""
        self.lbl_title.set_markup(
            f"<span font='13' weight='bold' color='#ffffff'>"
            f"{GLib.markup_escape_text(summary)}</span>{suffix}"
        )
        display_body = body[:115] + "..." if len(body) > 115 else body
        self.lbl_body.set_markup(
            f"<span font='12' color='#a1a1aa'>{GLib.markup_escape_text(display_body)}</span>"
        )
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
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_str, 28, 28, True)
                self.img_icon.set_from_pixbuf(pb)
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
        self.move(cur_x, int(cur_y + (self.target_y - cur_y) * 0.2))
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
        bus_name = dbus.service.BusName(
            'org.freedesktop.Notifications', bus=dbus.SessionBus()
        )
        super().__init__(bus_name, '/org/freedesktop/Notifications')
        self.next_id = 1
        self.windows = []

        try:
            session_bus = dbus.SessionBus()
            session_bus.add_signal_receiver(
                self.on_mpris_properties_changed,
                signal_name="PropertiesChanged",
                dbus_interface="org.freedesktop.DBus.Properties",
                path="/org/mpris/MediaPlayer2"
            )
        except Exception:
            pass

    @dbus.service.method('org.freedesktop.Notifications', out_signature='ssss')
    def GetServerInformation(self):
        return ("QuickNotifications", "QuickPanel", "2.0", "1.2")

    @dbus.service.method('org.freedesktop.Notifications', out_signature='as')
    def GetCapabilities(self):
        return ["body", "body-markup", "icon-static", "actions"]

    @dbus.service.method('org.freedesktop.Notifications', in_signature='u')
    def CloseNotification(self, id):
        self.on_window_closed(id, from_dbus=True)

    @dbus.service.method(
        'org.freedesktop.Notifications',
        in_signature='susssasa{sv}i', out_signature='u'
    )
    def Notify(self, app_name, replaces_id, app_icon,
               summary, body, actions, hints, expire_timeout):
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

        # Update existing if same app
        for win in self.windows:
            if win.app_name == app_name_str:
                win.update_content(summary_str, str(body), hints, icon_str)
                GLib.timeout_add(50, self.update_positions)
                return win.id

        # Remove oldest if at capacity
        if len(self.windows) >= 3:
            self.windows.pop(0).close_now()

        nid = self.next_id
        self.next_id += 1

        if media:
            new_win = MediaNotificationWindow(
                nid, app_name_str, summary_str, str(body), hints,
                self.on_window_closed
            )
        else:
            new_win = NotificationWindow(
                nid, app_name_str, summary_str, str(body),
                self.on_window_closed
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
            current_y += (h if h > 50 else 110) + spacing
        return False

    def on_window_closed(self, closed_id, from_dbus=False):
        for i, win in enumerate(self.windows):
            if win.id == closed_id:
                if not from_dbus:
                    pass
                self.windows.pop(i)
                break
        GLib.timeout_add(50, self.update_positions)

    def on_mpris_properties_changed(self, interface_name, changed_properties, invalidated_properties, sender=None):
        if interface_name != 'org.mpris.MediaPlayer2.Player':
            return
        if 'Metadata' in changed_properties or 'PlaybackStatus' in changed_properties:
            GLib.idle_add(self.handle_mpris_track_change)

    def handle_mpris_track_change(self):
        title = get_playerctl_value(["metadata", "xesam:title"])
        artist = get_playerctl_value(["metadata", "xesam:artist"])
        art_url = get_playerctl_value(["metadata", "mpris:artUrl"])

        if not title:
            return

        hints = {}
        if art_url:
            hints["image-path"] = art_url

        # Only update an already visible notification window
        for win in self.windows:
            if isinstance(win, MediaNotificationWindow):
                win.update_content(title, artist, hints, art_url)
                GLib.timeout_add(50, self.update_positions)
                return


if __name__ == '__main__':
    server = NotificationServer()
    loop = GLib.MainLoop()
    loop.run()
