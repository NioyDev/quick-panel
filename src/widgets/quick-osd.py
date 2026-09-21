#!/usr/bin/env python3
import sys
import os
import subprocess
import signal
import urllib.parse
import urllib.request
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, Pango
import cairo
# Import Windows compatibility helper if available
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from utils.win_compat import IS_WINDOWS, get_windows_volume, set_windows_volume, get_windows_media_info, run_windows_playerctl
except Exception:
    IS_WINDOWS = (os.name == 'nt')
    get_windows_volume = lambda: 50
    set_windows_volume = lambda v: None
    get_windows_media_info = lambda: ("", "", "")
    run_windows_playerctl = lambda c: None

action = sys.argv[1] if len(sys.argv) > 1 else None

# Check for existing instance to prevent duplicates/flickering
try:
    pids = subprocess.check_output(["pgrep", "-f", "quick-osd.py"]).decode().strip().split('\n')
    current_pid = str(os.getpid())
    other_pids = [p for p in pids if p and p != current_pid]
    
    for pid_str in other_pids:
        try:
            target_pid = int(pid_str)
            cmdline = open(f"/proc/{target_pid}/cmdline").read()
            if "quick-osd.py" in cmdline and ("python" in cmdline or "python3" in cmdline):
                if action == "up":
                    os.kill(target_pid, signal.SIGUSR1)
                elif action == "down":
                    os.kill(target_pid, signal.SIGUSR2)
                sys.exit(0)
        except Exception:
            pass
except Exception:
    pass

def get_current_volume():
    if IS_WINDOWS:
        return get_windows_volume()
    try:
        pactl_out = subprocess.check_output(["pactl", "get-sink-volume", "@DEFAULT_SINK@"]).decode('utf-8')
        vol_str = pactl_out.split('/')[1].strip().replace('%', '')
        return int(vol_str)
    except Exception:
        return 50

volume = get_current_volume()
if action == "up":
    volume = min(volume + 5, 100)
    if IS_WINDOWS:
        set_windows_volume(volume)
    else:
        subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume}%"])
elif action == "down":
    volume = max(volume - 5, 0)
    if IS_WINDOWS:
        set_windows_volume(volume)
    else:
        subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume}%"])

def get_media_info():
    if IS_WINDOWS:
        return get_windows_media_info()
    title, artist, art_url = "", "", ""
    try:
        import dbus
        bus = dbus.SessionBus()
        active_player = None
        for service in bus.list_names():
            if service.startswith('org.mpris.MediaPlayer2.'):
                try:
                    p = bus.get_object(service, '/org/mpris/MediaPlayer2')
                    props = dbus.Interface(p, 'org.freedesktop.DBus.Properties')
                    status = props.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus')
                    if status == "Playing":
                        active_player = service
                        break
                except Exception:
                    pass
                if not active_player:
                    active_player = service

        if active_player:
            player = bus.get_object(active_player, '/org/mpris/MediaPlayer2')
            props = dbus.Interface(player, 'org.freedesktop.DBus.Properties')
            metadata = props.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
            
            title = str(metadata.get('xesam:title', ''))
            artist_list = metadata.get('xesam:artist', [])
            if artist_list:
                artist = str(artist_list[0])
            art_url = str(metadata.get('mpris:artUrl', ''))
    except Exception:
        pass
    return title, artist, art_url

def run_playerctl(cmd):
    if IS_WINDOWS:
        run_windows_playerctl(cmd[0] if cmd else "")
    else:
        try:
            subprocess.Popen(["playerctl"] + cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def get_playerctl_value(cmd):
    try:
        result = subprocess.run(["playerctl"] + cmd, capture_output=True, text=True, timeout=1)
        return result.stdout.strip()
    except Exception:
        return ""

def format_time(microseconds):
    try:
        secs = int(float(microseconds)) // 1000000
        m, s = divmod(secs, 60)
        return f"{m}:{s:02d}"
    except Exception:
        return "0:00"


class OSDWindow(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.osd_width = 440
        self.set_default_size(self.osd_width, -1)
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_keep_above(True)
        
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        if monitor:
            geometry = monitor.get_geometry()
            x_pos = geometry.x + 20
            y_pos = geometry.y + 20
            self.move(x_pos, y_pos)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.main_box.set_name("main_box")
        self.main_box.set_margin_top(16)
        self.main_box.set_margin_bottom(16)
        self.main_box.set_margin_start(16)
        self.main_box.set_margin_end(16)
        self.add(self.main_box)

        # 1. Left: Album Cover Image (DrawingArea for smooth rounded corners)
        self.ART_SIZE = 90
        self._art_pixbuf = None
        self.art_area = Gtk.DrawingArea()
        self.art_area.set_size_request(self.ART_SIZE, self.ART_SIZE)
        self.art_area.set_valign(Gtk.Align.CENTER)
        self.art_area.connect("draw", self.draw_album_art)
        self.main_box.pack_start(self.art_area, False, False, 0)

        # 2. Right: Content column (Artist + Title + Playback Progress + Volume + Controls)
        right_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        right_col.set_valign(Gtk.Align.CENTER)
        self.main_box.pack_start(right_col, True, True, 0)

        # Subtitle / Artist
        self.lbl_artist = Gtk.Label()
        self.lbl_artist.set_halign(Gtk.Align.START)
        self.lbl_artist.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_artist.set_max_width_chars(25)
        right_col.pack_start(self.lbl_artist, False, False, 0)

        # Song Title
        self.lbl_title = Gtk.Label()
        self.lbl_title.set_halign(Gtk.Align.START)
        self.lbl_title.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_title.set_max_width_chars(25)
        right_col.pack_start(self.lbl_title, False, False, 0)

        # Playback Progress Bar Row
        self.progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.progress_box.set_margin_top(2)
        right_col.pack_start(self.progress_box, False, False, 0)

        self.progress_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.progress_scale.set_draw_value(False)
        self.progress_scale.set_hexpand(True)
        self.progress_scale.set_name("progress_scale")
        self.updating_progress_programmatically = False
        self.progress_scale.connect("value-changed", self.on_progress_seek)
        self.progress_box.pack_start(self.progress_scale, True, True, 0)

        time_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.progress_box.pack_start(time_row, False, False, 0)

        self.lbl_pos = Gtk.Label()
        self.lbl_pos.set_markup("<span font='9' color='#a1a1aa'>0:00</span>")
        self.lbl_pos.set_halign(Gtk.Align.START)
        time_row.pack_start(self.lbl_pos, True, True, 0)

        self.lbl_dur = Gtk.Label()
        self.lbl_dur.set_markup("<span font='9' color='#a1a1aa'>0:00</span>")
        self.lbl_dur.set_halign(Gtk.Align.END)
        time_row.pack_end(self.lbl_dur, False, False, 0)

        # Volume Slider Row
        vol_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        vol_row.set_margin_top(4)
        
        self.vol_icon = Gtk.Image.new_from_icon_name(self.get_volume_icon_name(volume), Gtk.IconSize.MENU)
        vol_row.pack_start(self.vol_icon, False, False, 0)

        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol_scale.set_value(volume)
        self.vol_scale.set_draw_value(False)
        self.vol_scale.set_hexpand(True)
        self.vol_scale.set_name("vol_scale")
        self.current_volume = volume
        self.updating_programmatically = False
        self.vol_scale.connect("value-changed", self.on_slider_moved)
        vol_row.pack_start(self.vol_scale, True, True, 0)

        self.vol_label = Gtk.Label(label=f"{volume}%")
        self.vol_label.set_name("vol_label")
        vol_row.pack_start(self.vol_label, False, False, 0)

        right_col.pack_start(vol_row, False, False, 0)

        # Controls Row
        self.ctrl_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.ctrl_row.set_halign(Gtk.Align.CENTER)
        self.ctrl_row.set_margin_top(4)
        right_col.pack_start(self.ctrl_row, False, False, 0)

        self.btn_prev = self._make_ctrl_btn("media-skip-backward-symbolic", self.on_prev, 32)
        self.btn_play = self._make_ctrl_btn("media-playback-pause-symbolic", self.on_play_pause, 36)
        self.btn_next = self._make_ctrl_btn("media-skip-forward-symbolic", self.on_next, 32)

        self.ctrl_row.pack_start(self.btn_prev, False, False, 0)
        self.ctrl_row.pack_start(self.btn_play, False, False, 0)
        self.ctrl_row.pack_start(self.btn_next, False, False, 0)

        self.refresh_card_content()
        self.setup_css()
        
        self.connect("draw", self.on_draw)
        
        self.timeout_id = GLib.timeout_add(3500, Gtk.main_quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self.on_sigusr1)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR2, self.on_sigusr2)

        try:
            session_bus = dbus.SessionBus()
            session_bus.add_signal_receiver(
                self.on_mpris_change,
                signal_name="PropertiesChanged",
                dbus_interface="org.freedesktop.DBus.Properties",
                path="/org/mpris/MediaPlayer2"
            )
        except Exception:
            pass

    def on_mpris_change(self, interface_name, changed_properties, invalidated_properties, sender=None):
        if interface_name == 'org.mpris.MediaPlayer2.Player':
            GLib.idle_add(self.refresh_card_content)

    def on_progress_seek(self, scale):
        if getattr(self, "updating_progress_programmatically", False):
            return
        seek_secs = int(scale.get_value())
        run_playerctl(["position", str(seek_secs)])
        self.lbl_pos.set_markup(f"<span font='9' color='#a1a1aa'>{format_time(seek_secs * 1_000_000)}</span>")
        self.reset_timeout()

    def _make_ctrl_btn(self, icon_name, callback, size):
        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.INVALID)
        img.set_pixel_size(size - 14)
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

    def get_volume_icon_name(self, vol):
        if vol == 0:
            return "audio-volume-muted-symbolic"
        elif vol < 33:
            return "audio-volume-low-symbolic"
        elif vol < 66:
            return "audio-volume-medium-symbolic"
        else:
            return "audio-volume-high-symbolic"

    def refresh_card_content(self):
        title, artist, art_url = get_media_info()
        status = get_playerctl_value(["status"]).lower()
        
        is_media_active = bool(title and status in ["playing", "paused"])
        
        if is_media_active:
            artist_text = (artist if artist else "REPRODUCTOR").upper()
            self.lbl_artist.set_markup(
                f"<span font='9' weight='bold' color='#a1a1aa'>"
                f"{GLib.markup_escape_text(artist_text)}</span>"
            )
            self.lbl_title.set_markup(
                f"<span font='13' weight='bold' color='#ffffff'>"
                f"{GLib.markup_escape_text(title)}</span>"
            )
            self.art_area.show()
            self.lbl_artist.show()
            self.lbl_title.show()
            self.ctrl_row.show_all()

            # Playback Progress + Timestamps
            pos = get_playerctl_value(["position"])
            dur = get_playerctl_value(["metadata", "mpris:length"])
            if pos and dur:
                try:
                    pos_secs = int(float(pos))
                    dur_us = float(dur)
                    dur_secs = int(dur_us / 1_000_000)
                    if dur_secs > 0:
                        self.updating_progress_programmatically = True
                        self.progress_scale.set_range(0, dur_secs)
                        self.progress_scale.set_value(pos_secs)
                        self.updating_progress_programmatically = False
                        self.lbl_pos.set_markup(f"<span font='9' color='#a1a1aa'>{format_time(float(pos) * 1_000_000)}</span>")
                        self.lbl_dur.set_markup(f"<span font='9' color='#a1a1aa'>{format_time(dur_us)}</span>")
                        self.progress_box.show_all()
                except Exception:
                    self.progress_box.hide()
            else:
                self.progress_box.hide()

            self._art_pixbuf = None
            if art_url:
                try:
                    if art_url.startswith("file://"):
                        art_path = urllib.parse.unquote(art_url[7:])
                    else:
                        art_path = "/tmp/osd_art.jpg"
                        urllib.request.urlretrieve(art_url, art_path)
                    
                    pb = GdkPixbuf.Pixbuf.new_from_file(art_path)
                    self._art_pixbuf = pb.scale_simple(
                        self.ART_SIZE, self.ART_SIZE, GdkPixbuf.InterpType.BILINEAR
                    )
                except Exception:
                    pass
            self.art_area.queue_draw()
            self.set_size_request(440, -1)
            self.resize(440, 1)
        else:
            self.art_area.hide()
            self.lbl_artist.hide()
            self.lbl_title.hide()
            self.progress_box.hide()
            self.ctrl_row.hide()
            self.set_size_request(320, -1)
            self.resize(320, 1)

    def draw_progress(self, widget, cr):
        w = widget.get_allocated_width()
        h = 4

        # Track background
        cr.set_source_rgba(1, 1, 1, 0.15)
        cr.move_to(2, 0)
        cr.line_to(w - 2, 0)
        cr.arc(w - 2, 2, 2, -1.570796, 0)
        cr.line_to(w, h - 2)
        cr.arc(w - 2, h - 2, 2, 0, 1.570796)
        cr.line_to(2, h)
        cr.arc(2, h - 2, 2, 1.570796, 3.141592)
        cr.line_to(0, 2)
        cr.arc(2, 2, 2, 3.141592, 4.712389)
        cr.close_path()
        cr.fill()

        # Accent track fill
        fill_w = int(w * self._progress_fraction)
        if fill_w > 4:
            cr.set_source_rgba(244/255, 114/255, 182/255, 0.95)
            cr.move_to(2, 0)
            cr.line_to(fill_w - 2, 0)
            cr.arc(fill_w - 2, 2, 2, -1.570796, 0)
            cr.line_to(fill_w, h - 2)
            cr.arc(fill_w - 2, h - 2, 2, 0, 1.570796)
            cr.line_to(2, h)
            cr.arc(2, h - 2, 2, 1.570796, 3.141592)
            cr.line_to(0, 2)
            cr.arc(2, 2, 2, 3.141592, 4.712389)
            cr.close_path()
            cr.fill()

        return False

    def draw_album_art(self, widget, cr):
        w = h = self.ART_SIZE
        r = 14.0

        # Rounded rectangle path
        cr.move_to(r, 0)
        cr.line_to(w - r, 0)
        cr.arc(w - r, r, r, -1.570796, 0)
        cr.line_to(w, h - r)
        cr.arc(w - r, h - r, r, 0, 1.570796)
        cr.line_to(r, h)
        cr.arc(r, h - r, r, 1.570796, 3.141592)
        cr.line_to(0, r)
        cr.arc(r, r, r, 3.141592, 4.712389)
        cr.close_path()
        cr.clip()

        if self._art_pixbuf:
            Gdk.cairo_set_source_pixbuf(cr, self._art_pixbuf, 0, 0)
            cr.paint()
        else:
            grad = cairo.LinearGradient(0, 0, w, h)
            grad.add_color_stop_rgb(0, 59/255.0, 130/255.0, 246/255.0)
            grad.add_color_stop_rgb(1, 147/255.0, 51/255.0, 234/255.0)
            cr.set_source(grad)
            cr.paint()

            cr.set_source_rgba(1, 1, 1, 0.9)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(36)
            cr.move_to(30, 58)
            cr.show_text("🔊")

        return False

    def setup_css(self):
        css = b'''
        #main_box {
            color: #f4f4f5;
        }
        #vol_scale trough, #progress_scale trough {
            min-height: 5px;
            border-radius: 4px;
            background-color: rgba(255, 255, 255, 0.15);
        }
        #vol_scale highlight, #progress_scale highlight {
            background-color: #f472b6;
            border-radius: 4px;
        }
        #vol_scale slider, #progress_scale slider {
            min-width: 12px;
            min-height: 12px;
            border-radius: 50%;
            background-color: #ffffff;
        }
        #vol_label {
            color: #f4f4f5;
            font-size: 13px;
            font-weight: 600;
            min-width: 40px;
        }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), 
            provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_sigusr1(self):
        if self.current_volume < 100:
            self.current_volume = min(self.current_volume + 5, 100)
            self.updating_programmatically = True
            self.vol_scale.set_value(self.current_volume)
            self.vol_label.set_text(f"{self.current_volume}%")
            self.vol_icon.set_from_icon_name(self.get_volume_icon_name(self.current_volume), Gtk.IconSize.MENU)
            self.updating_programmatically = False
            set_system_volume(self.current_volume)
        self.refresh_card_content()
        self.reset_timeout()
        return True

    def on_sigusr2(self):
        if self.current_volume > 0:
            self.current_volume = max(self.current_volume - 5, 0)
            self.updating_programmatically = True
            self.vol_scale.set_value(self.current_volume)
            self.vol_label.set_text(f"{self.current_volume}%")
            self.vol_icon.set_from_icon_name(self.get_volume_icon_name(self.current_volume), Gtk.IconSize.MENU)
            self.updating_programmatically = False
            set_system_volume(self.current_volume)
        self.refresh_card_content()
        self.reset_timeout()
        return True

    def on_prev(self):
        run_playerctl(["previous"])
        GLib.timeout_add(300, self.refresh_card_content)
        self.reset_timeout()

    def on_play_pause(self):
        run_playerctl(["play-pause"])
        GLib.timeout_add(300, self.refresh_card_content)
        self.reset_timeout()

    def on_next(self):
        run_playerctl(["next"])
        GLib.timeout_add(300, self.refresh_card_content)
        self.reset_timeout()

    def on_slider_moved(self, scale):
        if self.updating_programmatically:
            return
        vol = int(scale.get_value())
        self.current_volume = vol
        self.vol_label.set_text(f"{vol}%")
        self.vol_icon.set_from_icon_name(self.get_volume_icon_name(vol), Gtk.IconSize.MENU)
        self.pending_volume = vol
        if not hasattr(self, 'throttle_id') or not self.throttle_id:
            self.throttle_id = GLib.timeout_add(50, self.apply_pending_volume)
        self.reset_timeout()

    def apply_pending_volume(self):
        set_system_volume(self.pending_volume)
        self.throttle_id = None
        return False

    def reset_timeout(self):
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
        self.timeout_id = GLib.timeout_add(3500, Gtk.main_quit)

    def on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        radius = 20.0
        
        cr.set_source_rgba(24/255.0, 24/255.0, 27/255.0, 0.96)
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
        
        # Highlight border
        cr.set_source_rgba(1, 1, 1, 0.12)
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

win = OSDWindow()
win.show()
Gtk.main()
