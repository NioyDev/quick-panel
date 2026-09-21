import gi
import sys
import os
import subprocess
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio

# Toggle Logic: If already running, kill the old instance and exit.
current_pid = str(os.getpid())
try:
    pids = subprocess.check_output(["pgrep", "-f", "quick-launcher.py"]).decode().strip().split('\n')
    other_pids = [p for p in pids if p and p != current_pid]
    if other_pids:
        for p in other_pids:
            subprocess.run(["kill", "-9", p])
        sys.exit(0)
except subprocess.CalledProcessError:
    pass

CATEGORIES = {
    "Todas": "",
    "Internet": "Network;WebBrowser;Email;",
    "Juegos": "Game;",
    "Oficina": "Office;",
    "Multimedia": "AudioVideo;Audio;Video;Graphics;",
    "Sistema": "System;Settings;Utility;"
}

class QuickLauncher(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_app_paintable(True)
        self.set_default_size(650, 500)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            
        self.setup_css()
        
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", self.on_focus_out)
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.main_box.set_name("launcher_box")
        self.add(self.main_box)
        
        # Search Entry
        self.search = Gtk.SearchEntry()
        self.search.set_name("launcher_search")
        self.search.set_placeholder_text("Buscar aplicaciones...")
        self.search.connect("search-changed", self.on_filter_changed)
        self.search.set_margin_top(20)
        self.search.set_margin_start(20)
        self.search.set_margin_end(20)
        self.main_box.pack_start(self.search, False, False, 0)
        
        # Categories Box
        self.cat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.cat_box.set_margin_start(20)
        self.cat_box.set_margin_end(20)
        self.cat_box.set_halign(Gtk.Align.CENTER)
        self.main_box.pack_start(self.cat_box, False, False, 0)
        
        self.active_category = "Todas"
        self.cat_buttons = {}
        
        for cat_name in CATEGORIES.keys():
            btn = Gtk.Button(label=cat_name)
            btn.set_name("cat_btn")
            btn.set_can_focus(False)
            btn.connect("clicked", self.on_category_clicked, cat_name)
            self.cat_buttons[cat_name] = btn
            self.cat_box.pack_start(btn, False, False, 0)
            
        # Set active class for "Todas" initially
        self.cat_buttons["Todas"].get_style_context().add_class("active")
        
        # FlowBox for apps
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(6)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_name("launcher_flow")
        
        # Scrolled window
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.add(self.flowbox)
        self.scroll.set_margin_start(20)
        self.scroll.set_margin_end(20)
        self.scroll.set_margin_bottom(20)
        self.main_box.pack_start(self.scroll, True, True, 0)
        
        self.load_apps()
        
        GLib.idle_add(self.reposition)
        
    def setup_css(self):
        css = b'''
        * {
            outline: none;
        }
        window {
            background-color: transparent;
        }
        #launcher_box {
            background-color: rgba(24, 24, 27, 0.95);
            border-radius: 24px;
            border: 1px solid #27272a;
            box-shadow: 0 8px 32px rgba(0,0,0,0.8);
        }
        #launcher_search {
            background-color: #27272a;
            color: #ffffff;
            border: 1px solid #3f3f46;
            border-radius: 12px;
            padding: 12px 16px;
            font-size: 15px;
        }
        #cat_btn {
            background-color: transparent;
            color: #a1a1aa;
            border: 1px solid #3f3f46;
            border-radius: 20px;
            padding: 6px 16px;
            font-size: 13px;
            font-weight: bold;
            transition: all 200ms ease;
        }
        #cat_btn:hover {
            background-color: rgba(255, 255, 255, 0.05);
            color: #ffffff;
        }
        #cat_btn.active {
            background-color: #3b82f6;
            color: #ffffff;
            border-color: #3b82f6;
        }
        #app_btn {
            background-color: transparent;
            border: none;
            border-radius: 16px;
            padding: 12px 8px;
            transition: all 200ms ease;
        }
        #app_btn:hover {
            background-color: rgba(255, 255, 255, 0.08);
        }
        #app_label {
            color: #fafafa;
            font-size: 12px;
            margin-top: 10px;
        }
        scrolledwindow {
            background-color: transparent;
        }
        viewport {
            background-color: transparent;
        }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def load_apps(self):
        apps = Gio.AppInfo.get_all()
        apps = sorted(apps, key=lambda a: a.get_name().lower() if a.get_name() else "")
        
        for app in apps:
            if not app.should_show() or app.get_nodisplay():
                continue
                
            btn = Gtk.Button()
            btn.set_name("app_btn")
            btn.app_info = app
            btn.app_name = app.get_name().lower() if app.get_name() else ""
            btn.app_categories = app.get_categories() or ""
            btn.connect("clicked", self.on_app_clicked)
            
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            
            icon = app.get_icon()
            if icon:
                img = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DIALOG)
            else:
                img = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.DIALOG)
            img.set_pixel_size(48)
                
            box.pack_start(img, False, False, 0)
            
            name = app.get_name() or "App"
            if len(name) > 13:
                name = name[:11] + "..."
                
            lbl = Gtk.Label(label=name)
            lbl.set_name("app_label")
            box.pack_start(lbl, False, False, 0)
            
            btn.add(box)
            btn.set_halign(Gtk.Align.CENTER)
            btn.set_size_request(90, 100)
            
            self.flowbox.insert(btn, -1)
            
    def on_category_clicked(self, widget, cat_name):
        # Update active button visual state
        for name, btn in self.cat_buttons.items():
            btn.get_style_context().remove_class("active")
        widget.get_style_context().add_class("active")
        
        self.active_category = cat_name
        self.on_filter_changed(None)

    def on_filter_changed(self, entry=None):
        search_text = self.search.get_text().lower()
        active_cat_keywords = CATEGORIES[self.active_category].split(";")
        
        def filter_func(child):
            btn = child.get_child()
            
            # Text filter
            matches_text = True
            if search_text:
                matches_text = search_text in btn.app_name
                
            # Category filter
            matches_cat = True
            if self.active_category != "Todas":
                # Check if any keyword in the category mapping exists in the app's categories
                matches_cat = any(kw in btn.app_categories for kw in active_cat_keywords if kw)
                
            return matches_text and matches_cat
            
        self.flowbox.set_filter_func(filter_func)

    def on_app_clicked(self, widget):
        try:
            widget.app_info.launch([], None)
        except Exception as e:
            print(f"Failed to launch: {e}")
        sys.exit(0)

    def on_focus_out(self, widget, event):
        Gtk.main_quit()
        return False

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            sys.exit(0)

    def reposition(self):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        
        width, height = self.get_size()
        
        x = geometry.x + (geometry.width - width) // 2
        y = geometry.y + (geometry.height - height) // 2
        self.move(x, y)
        return False

if __name__ == "__main__":
    app = QuickLauncher()
    app.show_all()
    Gtk.main()
