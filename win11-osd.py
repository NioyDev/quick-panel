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
import dbus

action = sys.argv[1] if len(sys.argv) > 1 else None

# Check for existing instance to prevent flickering
try:
    pids = subprocess.check_output(["pgrep", "-f", "win11-osd.py"]).decode().strip().split('\n')
    current_pid = str(os.getpid())
    other_pids = [p for p in pids if p and p != current_pid]
    
    for pid_str in other_pids:
        try:
            target_pid = int(pid_str)
            cmdline = open(f"/proc/{target_pid}/cmdline").read()
            # Make sure it's the python process, not a shell wrapper
            if "win11-osd.py" in cmdline and ("python" in cmdline or "python3" in cmdline):
                if action == "up":
                    os.kill(target_pid, signal.SIGUSR1)
                elif action == "down":
                    os.kill(target_pid, signal.SIGUSR2)
                sys.exit(0)
        except Exception:
            pass
except Exception:
    pass

try:
    pactl_out = subprocess.check_output(["pactl", "get-sink-volume", "@DEFAULT_SINK@"]).decode('utf-8')
    vol_str = pactl_out.split('/')[1].strip().replace('%', '')
    volume = int(vol_str)
except Exception:
    volume = 50

# We are the main instance
if action == "up":
    volume = min(volume + 5, 150)
    subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume}%"])
elif action == "down":
    volume = max(volume - 5, 0)
    subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume}%"])

title = ""
artist = ""
art_url = ""

try:
    bus = dbus.SessionBus()
    active_player = None
    for service in bus.list_names():
        if service.startswith('org.mpris.MediaPlayer2.'):
            active_player = service
            break

    if active_player:
        player = bus.get_object(active_player, '/org/mpris/MediaPlayer2')
        props = dbus.Interface(player, 'org.freedesktop.DBus.Properties')
        metadata = props.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
        
        title = str(metadata.get('xesam:title', ''))
        artist_list = metadata.get('xesam:artist', [])
        if artist_list:
            artist = str(artist_list[0])
        art_url = str(metadata.get('mpris:artUrl', ''))
except Exception as e:
    pass

svg_content = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
    <path fill="white" d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
</svg>"""
with open("/tmp/volume_osd.svg", "w") as f:
    f.write(svg_content)

class OSDWindow(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_default_size(350, -1)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_decorated(False)
        self.set_app_paintable(True)
        
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        if monitor:
            geometry = monitor.get_geometry()
            y_pos = geometry.y + 20
            x_pos = geometry.x + 20
            self.move(x_pos, y_pos)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        main_box.set_name("main_box")
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        self.add(main_box)

        vol_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale("/tmp/volume_osd.svg", 32, 32, True)
        vol_icon = Gtk.Image.new_from_pixbuf(pixbuf)
        vol_icon.set_name("vol_icon")
        vol_box.pack_start(vol_icon, False, False, 0)
        
        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol_scale.set_value(volume)
        self.vol_scale.set_draw_value(False)
        self.vol_scale.set_hexpand(True)
        self.vol_scale.set_name("vol_scale")
        self.vol_scale.set_sensitive(True)
        self.updating_programmatically = False
        self.current_volume = volume
        adj = self.vol_scale.get_adjustment()
        adj.set_step_increment(1)
        adj.set_page_increment(5)
        self.vol_scale.connect("value-changed", self.on_slider_moved)
        vol_box.pack_start(self.vol_scale, True, True, 0)
        
        self.vol_label = Gtk.Label(label=f"{volume}")
        self.vol_label.set_name("vol_label")
        vol_box.pack_start(self.vol_label, False, False, 0)
        
        main_box.pack_start(vol_box, False, False, 0)

        if title:
            sep = Gtk.Box()
            sep.set_size_request(-1, 1)
            sep.set_name("media_sep")
            sep.set_margin_top(5)
            sep.set_margin_bottom(5)
            main_box.pack_start(sep, False, False, 0)
            
            media_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
            
            if art_url:
                try:
                    if art_url.startswith("file://"):
                        art_path = urllib.parse.unquote(art_url[7:])
                    else:
                        art_path = "/tmp/osd_art.jpg"
                        urllib.request.urlretrieve(art_url, art_path)
                    
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(art_path, 64, 64, True)
                    art_img = Gtk.Image.new_from_pixbuf(pixbuf)
                    media_box.pack_start(art_img, False, False, 0)
                except Exception as e:
                    pass

            text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            text_box.set_valign(Gtk.Align.CENTER)
            
            lbl_title = Gtk.Label(label=title)
            lbl_title.set_halign(Gtk.Align.START)
            lbl_title.set_name("lbl_title")
            lbl_title.set_ellipsize(Pango.EllipsizeMode.END)
            text_box.pack_start(lbl_title, False, False, 0)
            
            if artist:
                lbl_artist = Gtk.Label(label=artist)
                lbl_artist.set_halign(Gtk.Align.START)
                lbl_artist.set_name("lbl_artist")
                lbl_artist.set_ellipsize(Pango.EllipsizeMode.END)
                text_box.pack_start(lbl_artist, False, False, 0)
                
            media_box.pack_start(text_box, True, True, 0)
            main_box.pack_start(media_box, False, False, 0)

        css = b'''
        #main_box {
            color: white;
        }
        #media_sep {
            background-color: rgba(255, 255, 255, 0.15);
        }
        #vol_scale trough {
            min-height: 4px;
            border-radius: 4px;
            background-color: rgba(255, 255, 255, 0.2);
        }
        #vol_scale highlight {
            background-color: #11a8cd;
            border-radius: 4px;
        }
        #vol_scale slider {
            min-width: 14px;
            min-height: 14px;
            border-radius: 50%;
            background-color: white;
        }
        #lbl_title {
            font-weight: bold;
            font-size: 14px;
            color: white;
        }
        #lbl_artist {
            font-size: 12px;
            color: #aaaaaa;
        }
        #vol_label {
            color: white;
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
        
        self.timeout_id = GLib.timeout_add(3000, Gtk.main_quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self.on_sigusr1)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR2, self.on_sigusr2)

    def on_sigusr1(self):
        if self.current_volume < 150:
            self.current_volume = min(self.current_volume + 5, 150)
            self.updating_programmatically = True
            self.vol_scale.set_value(self.current_volume)
            self.vol_label.set_text(str(self.current_volume))
            self.updating_programmatically = False
            subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{self.current_volume}%"])
        self.reset_timeout()
        return True

    def on_sigusr2(self):
        if self.current_volume > 0:
            self.current_volume = max(self.current_volume - 5, 0)
            self.updating_programmatically = True
            self.vol_scale.set_value(self.current_volume)
            self.vol_label.set_text(str(self.current_volume))
            self.updating_programmatically = False
            subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{self.current_volume}%"])
        self.reset_timeout()
        return True

    def on_slider_moved(self, scale):
        if self.updating_programmatically:
            return
        vol = int(scale.get_value())
        self.current_volume = vol
        self.vol_label.set_text(str(vol))
        self.pending_volume = vol
        if not hasattr(self, 'throttle_id') or not self.throttle_id:
            self.throttle_id = GLib.timeout_add(50, self.apply_pending_volume)
        self.reset_timeout()

    def apply_pending_volume(self):
        subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{self.pending_volume}%"])
        self.throttle_id = None
        return False

    def reset_timeout(self):
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
        self.timeout_id = GLib.timeout_add(3000, Gtk.main_quit)

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

win = OSDWindow()
win.show_all()

Gtk.main()
