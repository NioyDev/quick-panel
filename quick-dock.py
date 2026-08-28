import gi
import sys
import subprocess
import time
import os
sys.path.append('/home/nioy/.local/bin')
gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Wnck, Gio
from sync_manager import SyncManager

PINNED_APPS = [
    "brave-browser.desktop",
    "code.desktop",
    "thunar.desktop",
    "xfce4-terminal.desktop"
]

class QuickDock(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("QuickDock")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_accept_focus(False)
        self.set_app_paintable(True)
        
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            
        self.setup_css()
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.main_box.set_name("dock_box")
        self.main_box.set_margin_bottom(8)
        
        # Launcher button
        self.btn_launcher = Gtk.Button()
        self.btn_launcher.set_name("dock_btn")
        self.btn_launcher.set_can_focus(False)
        self.btn_launcher.connect("clicked", self.on_launcher_clicked)
        icon_launcher = Gtk.Image.new_from_icon_name("view-app-grid-symbolic", Gtk.IconSize.MENU)
        self.btn_launcher.add(icon_launcher)
        
        self.main_box.pack_start(self.btn_launcher, False, False, 4)
        
        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_top(4)
        sep.set_margin_bottom(4)
        self.main_box.pack_start(sep, False, False, 0)
        
        # Window list container
        self.win_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.scroll.add(self.win_box)
        self.main_box.pack_start(self.scroll, True, True, 4)
        
        self.add(self.main_box)
        
        # Auto-hide properties
        self.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)
        self.is_hidden = False
        self.hide_timer = None
        self.anim_timer = None
        self.current_y = 0
        self.target_y = 0
        self.base_y = 0
        self.sync_mgr = SyncManager(self, "quick-dock", "quick-pill")
        
        # Wnck Screen setup
        self.wnck_screen = Wnck.Screen.get_default()
        self.wnck_screen.force_update()
        
        self.wnck_screen.connect("window-opened", self.on_window_changed)
        self.wnck_screen.connect("window-closed", self.on_window_changed)
        self.wnck_screen.connect("active-window-changed", self.on_active_window_changed)
        
        # Check initial state
        GLib.idle_add(lambda: self.on_active_window_changed(self.wnck_screen, None) or False)
        GLib.timeout_add(1000, self.enforce_visibility)
        
        self.app_buttons = {} # tracking by wm_class or desktop_id
        
        self.pinned_info = self.load_pinned_apps()
        
        GLib.idle_add(self.refresh_windows)
        GLib.idle_add(self.reposition)
        GLib.timeout_add(500, self.remove_struts)



    def remove_struts(self):
        if self.get_window():
            xid = self.get_window().get_xid()
            import subprocess
            subprocess.Popen(['xprop', '-id', str(xid), '-remove', '_NET_WM_STRUT_PARTIAL'])
            subprocess.Popen(['xprop', '-id', str(xid), '-remove', '_NET_WM_STRUT'])
        return False

    def setup_css(self):
        css = b'''
        * {
            outline: none;
        }
        window {
            background-color: transparent;
        }
        scrolledwindow {
            background-color: transparent;
        }
        viewport {
            background-color: transparent;
        }
        #dock_box {
            background-color: #18181b;
            border-radius: 20px;
            border: 1px solid #27272a;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            padding: 4px 12px;
        }
        #dock_btn {
            background-color: transparent;
            border: none;
            box-shadow: none;
            border-radius: 8px;
            padding: 2px 4px;
            min-width: 24px;
            transition: all 200ms ease-in-out;
        }
        #dock_btn:hover {
            background-color: #27272a;
        }
        #dock_btn.running {
            padding: 2px 10px;
            border-bottom: 2px solid #3f3f46;
            background-color: #27272a;
        }
        #dock_btn.active {
            padding: 2px 10px;
            border-bottom: 2px solid #60a5fa;
            background-color: #3f3f46;
        }
        #app_label {
            color: #fafafa;
            font-size: 13px;
            font-weight: 500;
        }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def load_pinned_apps(self):
        pinned = []
        app_info = Gio.AppInfo.get_all()
        for p in PINNED_APPS:
            for app in app_info:
                if app.get_id() == p:
                    pinned.append({
                        'id': p,
                        'name': app.get_name(),
                        'icon': app.get_icon(),
                        'exec': app.get_executable(),
                        'app_info': app
                    })
                    break
        return pinned

    def show_dock_sync(self):
        if not self.should_show_dock():
            return
        if self.hide_timer:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = None
        self.show_dock()
        
    def hide_dock_sync(self):
        if self.hide_timer:
            GLib.source_remove(self.hide_timer)
        self.hide_timer = GLib.timeout_add(2000, self.hide_dock)

    def on_mouse_enter(self, widget, event):
        if event.detail == Gdk.NotifyType.INFERIOR:
            return False
        self.sync_mgr.notify_enter()
        return False
        
    def on_mouse_leave(self, widget, event):
        if event.detail == Gdk.NotifyType.INFERIOR:
            return False
        self.sync_mgr.notify_leave()
        return False
        
    def hide_dock(self):
        self.hide_timer = None
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        
        self.target_y = geometry.height - 2
        self.start_animation()
        return False
        
    def should_show_dock(self):
        try:
            display = Gdk.Display.get_default()
            monitor = display.get_primary_monitor()
            m_geom = monitor.get_geometry()
            
            active_win = self.wnck_screen.get_active_window()
            if not active_win: return True
            if active_win.get_window_type() == Wnck.WindowType.DESKTOP: return True
            
            geom = active_win.get_geometry()
            is_borderless = (geom.widthp >= m_geom.width and geom.heightp >= m_geom.height and not active_win.is_maximized())
            if active_win.is_fullscreen() or is_borderless:
                return False
                
            active_app = active_win.get_application()
            if active_app:
                for w in active_app.get_windows():
                    if w == active_win: continue
                    if w.is_fullscreen(): return False
                    w_geom = w.get_geometry()
                    if w_geom.widthp >= m_geom.width and w_geom.heightp >= m_geom.height and not w.is_maximized():
                        return False
            return True
        except:
            return True

    def enforce_visibility(self):
        if not self.should_show_dock():
            if self.get_mapped():
                self.hide()
        else:
            if not self.get_mapped():
                self.show_all()
        return True

    def show_dock(self):
        if not self.should_show_dock():
            return
        self.target_y = self.base_y
        self.start_animation()
        
    def start_animation(self):
        if self.anim_timer:
            GLib.source_remove(self.anim_timer)
        self.anim_timer = GLib.timeout_add(16, self.animate_step)
        
    def animate_step(self):
        width, height = self.get_size()
        x, y = self.get_position()
        
        diff = self.target_y - y
        if abs(diff) <= 2:
            self.move(x, self.target_y)
            self.current_y = self.target_y
            self.anim_timer = None
            return False
            
        step = int(diff * 0.2)
        if step == 0:
            step = 1 if diff > 0 else -1
            
        new_y = y + step
        self.move(x, new_y)
        self.current_y = new_y
        return True

    def on_launcher_clicked(self, widget):
        subprocess.Popen(["python3", "/home/nioy/.local/bin/quick-launcher.py"])

    def on_window_changed(self, screen, window):
        if window:
            if window.is_skip_pager() or window.is_skip_tasklist() or window.get_window_type() != Wnck.WindowType.NORMAL:
                return
        self.refresh_windows()

    def on_active_window_changed(self, screen, previously_active_window):
        win = screen.get_active_window()
        if not win:
            self.show_all()
            self.update_classes()
            return
            
        is_fs = win.is_fullscreen()
        geom = win.get_geometry()
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        m_geom = monitor.get_geometry()
        
        is_borderless = (geom.widthp >= m_geom.width and geom.heightp >= m_geom.height and not win.is_maximized() and win.get_window_type() != Wnck.WindowType.DESKTOP)
        
        if is_fs or is_borderless:
            self.hide()
        else:
            self.show_all()
        self.update_classes()

    def get_window_class(self, win):
        cg = win.get_class_group()
        if cg:
            return cg.get_name().lower()
        return win.get_name().lower()
        
    def match_pinned_app(self, wm_class):
        for p in self.pinned_info:
            if p['id'].lower().startswith(wm_class) or wm_class in p['id'].lower():
                return p['id']
            if "code" in wm_class and "code" in p['id'].lower():
                return p['id']
            if "brave" in wm_class and "brave" in p['id'].lower():
                return p['id']
        return None

    def get_clean_name(self, raw_str):
        raw = raw_str.lower()
        if "brave" in raw: return "Brave"
        if "terminal" in raw: return "Terminal"
        if "code" in raw: return "VS Code"
        if "thunar" in raw: return "Archivos"
        if "antigravity" in raw: return "Antigravity"
        if "pinta" in raw: return "Pinta"
        if "steam" in raw: return "Steam"
        return raw.split('-')[0].split('.')[0].capitalize()

    def refresh_windows(self):
        for child in self.win_box.get_children():
            self.win_box.remove(child)
            
        self.app_buttons.clear()
        
        # 1. Add all pinned apps first
        for p in self.pinned_info:
            btn = Gtk.Button()
            btn.set_name("dock_btn")
            btn.set_can_focus(False)
            
            icon = p['icon']
            if icon:
                img = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.MENU)
            else:
                img = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.MENU)
                
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            box.pack_start(img, False, False, 0)
            
            clean_name = self.get_clean_name(p['id'])
            lbl = Gtk.Label(label=clean_name)
            lbl.set_name("app_label")
            lbl.set_no_show_all(True)
            lbl.hide()
            box.pack_start(lbl, False, False, 0)
            
            btn.add(box)
            btn.dock_label = lbl
            btn.dock_is_pinned = True
            btn.dock_app_id = p['id']
            btn.dock_windows = []
            btn.connect("clicked", self.on_app_clicked, p['id'])
            
            self.app_buttons[p['id']] = btn
            self.win_box.pack_start(btn, False, False, 0)
            
        # 2. Match running windows
        windows = self.wnck_screen.get_windows()
        for win in windows:
            if win.is_skip_pager() or win.is_skip_tasklist() or win.get_window_type() != Wnck.WindowType.NORMAL:
                continue
                
            wm_class = self.get_window_class(win)
            matched_id = self.match_pinned_app(wm_class)
            
            if matched_id and matched_id in self.app_buttons:
                self.app_buttons[matched_id].dock_windows.append(win)
            else:
                unpinned_id = "unpinned_" + wm_class
                if unpinned_id not in self.app_buttons:
                    btn = Gtk.Button()
                    btn.set_name("dock_btn")
                    btn.set_can_focus(False)
                    
                    pixbuf = win.get_icon()
                    if pixbuf:
                        try:
                            pixbuf = pixbuf.scale_simple(16, 16, GdkPixbuf.InterpType.BILINEAR)
                            img = Gtk.Image.new_from_pixbuf(pixbuf)
                        except Exception:
                            img = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.MENU)
                    else:
                        img = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.MENU)
                        
                    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                    box.pack_start(img, False, False, 0)
                    
                    clean_name = self.get_clean_name(wm_class)
                    lbl = Gtk.Label(label=clean_name)
                    lbl.set_name("app_label")
                    lbl.set_no_show_all(True)
                    lbl.hide()
                    box.pack_start(lbl, False, False, 0)
                    
                    btn.add(box)
                    btn.dock_label = lbl
                    btn.dock_is_pinned = False
                    btn.dock_app_id = unpinned_id
                    btn.dock_windows = [win]
                    btn.connect("clicked", self.on_app_clicked, unpinned_id)
                    
                    self.app_buttons[unpinned_id] = btn
                    self.win_box.pack_start(btn, False, False, 0)
                else:
                    self.app_buttons[unpinned_id].dock_windows.append(win)
                    
        self.update_classes()
        self.win_box.show_all()
        GLib.idle_add(self.reposition)
        GLib.timeout_add(500, self.remove_struts)
        
    def update_classes(self):
        active_win = self.wnck_screen.get_active_window()
        active_xid = active_win.get_xid() if active_win else -1
        
        for app_id, btn in self.app_buttons.items():
            context = btn.get_style_context()
            context.remove_class("running")
            context.remove_class("active")
            
            if len(btn.dock_windows) > 0:
                btn.dock_label.show()
                is_active = any(w.get_xid() == active_xid for w in btn.dock_windows)
                if is_active:
                    context.add_class("active")
                else:
                    context.add_class("running")
            else:
                btn.dock_label.hide()

    def on_app_clicked(self, widget, app_id):
        btn = self.app_buttons[app_id]
        windows = btn.dock_windows
        
        if len(windows) == 0:
            for p in self.pinned_info:
                if p['id'] == app_id:
                    try:
                        p['app_info'].launch([], None)
                    except Exception as e:
                        print(f"Failed to launch {app_id}: {e}")
                    break
        else:
            active_win = self.wnck_screen.get_active_window()
            if active_win in windows:
                if len(windows) == 1:
                    active_win.minimize()
                else:
                    idx = windows.index(active_win)
                    next_win = windows[(idx + 1) % len(windows)]
                    next_win.activate(int(time.time()))
            else:
                windows[0].activate(int(time.time()))
            
    def reposition(self):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        
        target_width = geometry.width - 400
        
        self.set_size_request(target_width, -1)
        self.scroll.set_min_content_width(-1)
        width, height = self.get_size()
        
        self.base_y = geometry.height - height
        
        if self.current_y == 0:
            self.current_y = self.base_y
            self.move(16, self.base_y)
            
        return False

if __name__ == "__main__":
    app = QuickDock()
    app.show_all()
    Gtk.main()
