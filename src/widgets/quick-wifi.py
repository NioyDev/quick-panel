#!/usr/bin/env python3
import gi
import subprocess
import threading
import time
import os
import qrcode
import sys
import signal

try:
    pids = subprocess.check_output(["pgrep", "-f", "quick-wifi.py"]).decode().strip().split('\n')
    current_pid = str(os.getpid())
    other_pids = [p for p in pids if p and p != current_pid]
    if other_pids:
        for pid_str in other_pids:
            try:
                os.kill(int(pid_str), signal.SIGTERM)
            except Exception:
                pass
        sys.exit(0)
except Exception:
    pass

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

class WifiPasswordDialog(Gtk.Dialog):
    def __init__(self, parent, ssid):
        super().__init__(title=f"Contraseña para {ssid}", transient_for=parent, flags=0)
        self.set_decorated(False)
        self.set_modal(True)
        self.set_keep_above(True)
        self.set_default_size(300, 150)
        self.set_border_width(16)
        
        self.connect("map-event", self.on_map)
        self.connect("unmap-event", self.on_unmap)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self.on_button_press)
        
        box = self.get_content_area()
        box.set_spacing(12)
        
        lbl = Gtk.Label(label=f"Ingresa la contraseña para:\n<b>{ssid}</b>")
        lbl.set_use_markup(True)
        box.pack_start(lbl, False, False, 0)
        
        self.entry = Gtk.Entry()
        self.entry.set_visibility(False)
        self.entry.set_activates_default(True)
        box.pack_start(self.entry, False, False, 0)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        cancel_btn = Gtk.Button(label="Cancelar")
        cancel_btn.connect("clicked", lambda x: self.response(Gtk.ResponseType.CANCEL))
        
        connect_btn = Gtk.Button(label="Conectar")
        connect_btn.get_style_context().add_class("suggested-action")
        connect_btn.connect("clicked", lambda x: self.response(Gtk.ResponseType.OK))
        self.set_default(connect_btn)
        
        btn_box.pack_end(connect_btn, False, False, 0)
        btn_box.pack_end(cancel_btn, False, False, 0)
        box.pack_end(btn_box, False, False, 0)
        
        self.show_all()

    def on_map(self, widget, event):
        seat = Gdk.Display.get_default().get_default_seat()
        seat.grab(self.get_window(), Gdk.SeatCapabilities.ALL_POINTING, True, None, None, None)
        return False
        
    def on_unmap(self, widget, event):
        seat = Gdk.Display.get_default().get_default_seat()
        seat.ungrab()
        return False

    def on_button_press(self, widget, event):
        x, y = self.get_position()
        w, h = self.get_size()
        _, root_x, root_y = event.get_root_coords()
        if root_x < x or root_x > x + w or root_y < y or root_y > y + h:
            self.response(Gtk.ResponseType.CANCEL)
            return True
        return False

class QuickWifi(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
            
        self.setup_css()
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.main_box.set_name("wifi_box")
        self.main_box.set_size_request(450, 500)
        
        # --- WIFI HEADER ---
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon = Gtk.Image.new_from_icon_name("network-wireless-signal-excellent-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        label = Gtk.Label(label="Wi-Fi")
        label.set_name("wifi_label")
        label.set_halign(Gtk.Align.START)
        
        self.switch = Gtk.Switch()
        self.switch.set_valign(Gtk.Align.CENTER)
        self.switch.connect("notify::active", self.on_switch_toggled)
        
        settings_btn = Gtk.Button()
        settings_btn.add(Gtk.Image.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.MENU))
        settings_btn.connect("clicked", self.open_settings)
        settings_btn.set_name("wifi_settings_btn")
        
        header.pack_start(icon, False, False, 0)
        header.pack_start(label, True, True, 0)
        header.pack_start(self.switch, False, False, 0)
        header.pack_start(settings_btn, False, False, 0)
        
        self.main_box.pack_start(header, False, False, 0)
        
        # --- SPEED MONITOR ---
        speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        speed_box.set_name("speed_box")
        
        down_icon = Gtk.Image.new_from_icon_name("go-down-symbolic", Gtk.IconSize.MENU)
        self.down_lbl = Gtk.Label(label="0 KB/s")
        self.down_lbl.set_name("speed_lbl")
        
        up_icon = Gtk.Image.new_from_icon_name("go-up-symbolic", Gtk.IconSize.MENU)
        self.up_lbl = Gtk.Label(label="0 KB/s")
        self.up_lbl.set_name("speed_lbl")
        
        speed_box.pack_start(down_icon, False, False, 0)
        speed_box.pack_start(self.down_lbl, True, True, 0)
        speed_box.pack_start(up_icon, False, False, 0)
        speed_box.pack_start(self.up_lbl, True, True, 0)
        
        self.main_box.pack_start(speed_box, False, False, 0)
        
        # --- NETWORKS LIST ---
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_min_content_height(350)
        
        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.scroll.add_with_viewport(self.list_box)
        self.main_box.pack_start(self.scroll, True, True, 0)
        
        self.add(self.main_box)
        
        self.connect("focus-out-event", lambda *args: Gtk.main_quit())
        self.connect("map-event", self.on_map)
        self.connect("unmap-event", self.on_unmap)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self.on_button_press)
        self.connect("key-press-event", self.on_key_press)
        
        self.ignore_switch = True
        self.saved_connections = []
        
        self.last_rx = 0
        self.last_tx = 0
        self.last_time = 0
        self.iface = self.get_wifi_interface()
        
        GLib.idle_add(self.init_data)
        GLib.idle_add(self.position_window)
        GLib.timeout_add(1000, self.update_speed)

    def get_wifi_interface(self):
        try:
            out = subprocess.check_output("nmcli -t -f DEVICE,TYPE dev", shell=True).decode()
            for line in out.split('\n'):
                if ':wifi' in line:
                    return line.split(':')[0]
        except: pass
        return "wlo1"

    def update_speed(self):
        if not self.iface: return True
        try:
            with open(f"/sys/class/net/{self.iface}/statistics/rx_bytes", "r") as f:
                rx = int(f.read().strip())
            with open(f"/sys/class/net/{self.iface}/statistics/tx_bytes", "r") as f:
                tx = int(f.read().strip())
                
            curr_time = time.time()
            if self.last_time > 0:
                dt = curr_time - self.last_time
                rx_speed = (rx - self.last_rx) / dt
                tx_speed = (tx - self.last_tx) / dt
                
                self.down_lbl.set_label(self.format_speed(rx_speed))
                self.up_lbl.set_label(self.format_speed(tx_speed))
                
            self.last_rx = rx
            self.last_tx = tx
            self.last_time = curr_time
        except: pass
        return True

    def format_speed(self, bytes_per_sec):
        if bytes_per_sec > 1048576:
            return f"{bytes_per_sec/1048576:.1f} MB/s"
        elif bytes_per_sec > 1024:
            return f"{bytes_per_sec/1024:.1f} KB/s"
        return f"{int(bytes_per_sec)} B/s"

    def init_data(self):
        try:
            status = subprocess.check_output("LC_ALL=C nmcli radio wifi", shell=True).decode().strip()
            self.ignore_switch = True
            self.switch.set_active(status == "enabled")
            self.ignore_switch = False
        except: pass
        
        try:
            out = subprocess.check_output("LC_ALL=C nmcli -t -f NAME con show", shell=True).decode()
            self.saved_connections = [line.strip() for line in out.split('\n') if line.strip()]
        except: pass
        
        threading.Thread(target=self.scan_networks).start()
        return False

    def scan_networks(self):
        try:
            subprocess.run(["nmcli", "dev", "wifi", "rescan"], timeout=3)
        except: pass
        
        try:
            out = subprocess.check_output("LC_ALL=C nmcli -t -e yes -f ACTIVE,SSID,BSSID,SIGNAL,SECURITY,FREQ dev wifi", shell=True).decode()
            networks = []
            seen_ssids = set()
            for line in out.split('\n'):
                if not line.strip(): continue
                line = line.replace("\\:", "|||")
                parts = line.split(":")
                if len(parts) >= 6:
                    active = parts[0] == "yes"
                    ssid = parts[1].replace("|||", ":")
                    bssid = parts[2].replace("|||", ":")
                    signal = parts[3]
                    security = parts[4]
                    freq_str = parts[5].replace(" MHz", "").strip()
                    band = "5G" if freq_str.isdigit() and int(freq_str) > 4000 else "2.4G"
                    
                    if ssid and (ssid, band) not in seen_ssids:
                        seen_ssids.add((ssid, band))
                        networks.append({
                            'active': active,
                            'ssid': ssid,
                            'bssid': bssid,
                            'signal': signal,
                            'security': security,
                            'band': band
                        })
            
            GLib.idle_add(self.populate_networks, networks)
        except: pass

    def populate_networks(self, networks):
        for child in self.list_box.get_children():
            self.list_box.remove(child)
            
        if not networks:
            lbl = Gtk.Label(label="No se encontraron redes.")
            lbl.set_margin_top(20)
            self.list_box.pack_start(lbl, False, False, 0)
            self.list_box.show_all()
            return
            
        for net in networks:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            
            sig_val = int(net['signal']) if net['signal'].isdigit() else 0
            if sig_val > 75: icon_name = "network-wireless-signal-excellent-symbolic"
            elif sig_val > 50: icon_name = "network-wireless-signal-good-symbolic"
            elif sig_val > 25: icon_name = "network-wireless-signal-ok-symbolic"
            else: icon_name = "network-wireless-signal-weak-symbolic"
            
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
            row.pack_start(icon, False, False, 0)
            
            band_lbl = Gtk.Label()
            band_lbl.set_markup(f"<span foreground='#a1a1aa' size='smaller'>[{net['band']}]</span>")
            row.pack_start(band_lbl, False, False, 0)
            
            lbl = Gtk.Label(label=net['ssid'])
            lbl.set_halign(Gtk.Align.START)
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            if net['active']:
                lbl.set_markup(f"<b>{net['ssid']}</b> <span foreground='#10b981'>(Conectado)</span>")
            row.pack_start(lbl, True, True, 0)
            
            if net['security'] and net['security'] != "":
                lock = Gtk.Image.new_from_icon_name("changes-prevent-symbolic", Gtk.IconSize.MENU)
                row.pack_start(lock, False, False, 0)
            
            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            if net['active']:
                qr_btn = Gtk.Button()
                qr_btn.add(Gtk.Image.new_from_icon_name("view-barcode-symbolic", Gtk.IconSize.MENU))
                qr_btn.set_tooltip_text("Mostrar código QR")
                qr_btn.set_name("wifi_action_btn")
                qr_btn.connect("clicked", self.show_qr, net['ssid'])
                btn_box.pack_start(qr_btn, False, False, 0)
                
                time_btn = Gtk.Button()
                time_btn.add(Gtk.Image.new_from_icon_name("alarm-symbolic", Gtk.IconSize.MENU))
                time_btn.set_tooltip_text("Temporizador de desconexión")
                time_btn.set_name("wifi_action_btn")
                time_btn.connect("clicked", self.show_timer_dialog, net['ssid'])
                btn_box.pack_start(time_btn, False, False, 0)
                
                btn = Gtk.Button(label="Desconectar")
                btn.set_name("wifi_action_btn")
                btn.connect("clicked", self.on_disconnect, net['ssid'])
                btn_box.pack_start(btn, False, False, 0)
            else:
                btn = Gtk.Button(label="Conectar")
                btn.set_name("wifi_action_btn")
                btn.connect("clicked", self.on_connect, net)
                btn_box.pack_start(btn, False, False, 0)
                
            row.pack_start(btn_box, False, False, 0)
            self.list_box.pack_start(row, False, False, 0)
            
        self.list_box.show_all()

    def show_timer_dialog(self, btn, ssid):
        self.release_grab()
        self.hide()
        dialog = Gtk.Dialog(title="Temporizador", transient_for=None, flags=0)
        dialog.set_position(Gtk.WindowPosition.CENTER)
        dialog.set_decorated(False)
        dialog.set_modal(True)
        dialog.set_keep_above(True)
        dialog.set_border_width(16)
        self.bind_dialog_grab(dialog)
        box = dialog.get_content_area()
        box.set_spacing(12)
        
        lbl = Gtk.Label(label=f"¿En cuántos minutos deseas desconectar\n<b>{ssid}</b>?")
        lbl.set_use_markup(True)
        lbl.set_justify(Gtk.Justification.CENTER)
        box.pack_start(lbl, False, False, 0)
        
        spin = Gtk.SpinButton.new_with_range(1, 120, 1)
        spin.set_value(30)
        box.pack_start(spin, False, False, 0)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cancel = Gtk.Button(label="Cancelar")
        cancel.connect("clicked", lambda x: dialog.response(Gtk.ResponseType.CANCEL))
        ok = Gtk.Button(label="Iniciar")
        ok.get_style_context().add_class("suggested-action")
        ok.connect("clicked", lambda x: dialog.response(Gtk.ResponseType.OK))
        
        btn_box.pack_end(ok, False, False, 0)
        btn_box.pack_end(cancel, False, False, 0)
        box.pack_end(btn_box, False, False, 0)
        dialog.show_all()
        
        if dialog.run() == Gtk.ResponseType.OK:
            mins = spin.get_value_as_int()
            def worker():
                time.sleep(mins * 60)
                subprocess.run(["nmcli", "con", "down", ssid])
            threading.Thread(target=worker, daemon=True).start()
        dialog.destroy()
        self.show_all()
        self.on_map(None, None)

    def show_qr(self, btn, ssid):
        try:
            psk = subprocess.check_output(f"nmcli -s -g 802-11-wireless-security.psk connection show '{ssid}'", shell=True).decode().strip()
            if not psk:
                self.show_error(f"No se pudo obtener la contraseña guardada para {ssid}")
                return
                
            qr_data = f"WIFI:S:{ssid};T:WPA;P:{psk};;"
            img = qrcode.make(qr_data)
            img_path = "/tmp/wifi_qr.png"
            img.save(img_path)
            
            self.release_grab()
            self.hide()
            dialog = Gtk.Dialog(title="Escanear para conectar", transient_for=None, flags=0)
            dialog.set_position(Gtk.WindowPosition.CENTER)
            dialog.set_decorated(False)
            dialog.set_modal(True)
            dialog.set_keep_above(True)
            dialog.set_border_width(16)
            self.bind_dialog_grab(dialog)
            
            def on_qr_close(d, r):
                d.destroy()
                self.show_all()
                self.on_map(None, None)
                
            dialog.connect("response", on_qr_close)
            box = dialog.get_content_area()
            
            lbl = Gtk.Label()
            lbl.set_markup(f"<b>{ssid}</b>\nEscanea este código con tu celular")
            lbl.set_justify(Gtk.Justification.CENTER)
            box.pack_start(lbl, False, False, 8)
            
            qr_image = Gtk.Image.new_from_file(img_path)
            box.pack_start(qr_image, True, True, 0)
            
            close_btn = Gtk.Button(label="Cerrar")
            close_btn.connect("clicked", lambda x: dialog.destroy())
            box.pack_start(close_btn, False, False, 8)
            
            dialog.show_all()
        except Exception as e:
            self.show_error("Error al obtener la contraseña.")

    def on_connect(self, btn, net):
        btn.set_label("...")
        def worker():
            ssid = net['ssid']
            bssid = net['bssid']
            
            if ssid in self.saved_connections:
                subprocess.run(["nmcli", "con", "up", ssid])
            else:
                if net['security'] != "":
                    GLib.idle_add(self.ask_password_and_connect, ssid, bssid)
                    return
                else:
                    subprocess.run(["nmcli", "dev", "wifi", "connect", bssid])
                    
            GLib.idle_add(self.scan_networks)
        threading.Thread(target=worker).start()

    def ask_password_and_connect(self, ssid, bssid):
        self.release_grab()
        self.hide()
        dialog = WifiPasswordDialog(None, ssid)
        dialog.set_position(Gtk.WindowPosition.CENTER)
        self.active_dialog = dialog
        dialog.connect("destroy", lambda x: setattr(self, 'active_dialog', None))
        response = dialog.run()
        dialog.destroy()
        self.show_all()
        self.on_map(None, None)
        
        if response == Gtk.ResponseType.OK:
            password = dialog.entry.get_text()
            dialog.destroy()
            if password:
                def worker():
                    subprocess.run(["nmcli", "dev", "wifi", "connect", bssid, "password", password])
                    GLib.idle_add(self.scan_networks)
                threading.Thread(target=worker).start()
        else:
            self.scan_networks()

    def on_disconnect(self, btn, ssid):
        btn.set_label("...")
        def worker():
            subprocess.run(["nmcli", "con", "down", ssid])
            GLib.idle_add(self.scan_networks)
        threading.Thread(target=worker).start()

    def release_grab(self):
        seat = Gdk.Display.get_default().get_default_seat()
        seat.ungrab()

    def bind_dialog_grab(self, dialog):
        self.active_dialog = dialog
        dialog.connect("destroy", lambda x: setattr(self, 'active_dialog', None))
        dialog.connect("map-event", self.on_dialog_map)
        dialog.connect("unmap-event", self.on_dialog_unmap)
        dialog.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        dialog.connect("button-press-event", self.on_dialog_button_press)

    def on_dialog_map(self, widget, event):
        seat = Gdk.Display.get_default().get_default_seat()
        seat.grab(widget.get_window(), Gdk.SeatCapabilities.ALL_POINTING, True, None, None, None)
        return False

    def on_dialog_unmap(self, widget, event):
        seat = Gdk.Display.get_default().get_default_seat()
        seat.ungrab()
        return False

    def on_dialog_button_press(self, widget, event):
        x, y = widget.get_position()
        w, h = widget.get_size()
        _, root_x, root_y = event.get_root_coords()
        if root_x < x or root_x > x + w or root_y < y or root_y > y + h:
            widget.response(Gtk.ResponseType.CANCEL)
            return True
        return False

    def show_error(self, message):
        self.release_grab()
        self.hide()
        dialog = Gtk.MessageDialog(transient_for=None, flags=0, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text=message)
        dialog.set_position(Gtk.WindowPosition.CENTER)
        dialog.set_modal(True)
        dialog.set_keep_above(True)
        dialog.run()
        dialog.destroy()
        self.show_all()
        self.on_map(None, None)

    def on_switch_toggled(self, switch, gparam):
        if self.ignore_switch: return
        state = "on" if switch.get_active() else "off"
        subprocess.Popen(["nmcli", "radio", "wifi", state])
        if state == "on":
            GLib.timeout_add(2000, self.scan_networks)
        else:
            self.populate_networks([])

    def open_settings(self, btn):
        subprocess.Popen(["nm-connection-editor"])
        Gtk.main_quit()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

    def position_window(self):
        geometry = Gdk.Display.get_default().get_primary_monitor().get_geometry()
        width, height = self.get_size()
        x = geometry.width - width - 80 # Shift right slightly from main panel
        y = geometry.height - height - 60
        self.move(x, y)
        self.present()
        return False

    def setup_css(self):
        css = b'''
        * { outline: none; }
        window { background-color: transparent; }
        #wifi_box {
            background-color: #18181b;
            border-radius: 20px;
            border: 1px solid #27272a;
            padding: 16px;
        }
        #speed_box {
            background-color: #27272a;
            border-radius: 12px;
            padding: 8px 16px;
        }
        #speed_lbl {
            color: #10b981;
            font-weight: bold;
            font-family: monospace;
        }
        image { color: #fafafa; }
        #wifi_label {
            color: #fafafa;
            font-size: 14px;
            font-weight: bold;
        }
        #wifi_settings_btn {
            background-color: transparent;
            color: #fafafa;
            border: none;
            box-shadow: none;
            border-radius: 12px;
        }
        #wifi_settings_btn:hover { background-color: #27272a; }
        #wifi_action_btn {
            background-color: #3f3f46;
            color: #fafafa;
            border: none;
            border-radius: 8px;
            font-size: 12px;
            padding: 4px 12px;
        }
        #wifi_action_btn:hover { background-color: #52525b; }
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
        if hasattr(self, 'active_dialog') and self.active_dialog:
            self.active_dialog.response(Gtk.ResponseType.CANCEL)
            return True
            
        width, height = self.get_size()
        if event.x < 0 or event.x > width or event.y < 0 or event.y > height:
            Gtk.main_quit()
            return True
        return False

if __name__ == "__main__":
    app = QuickWifi()
    app.show_all()
    Gtk.main()
