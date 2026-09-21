#!/bin/bash
export DISPLAY=:0.0
export XAUTHORITY="$HOME/.Xauthority"
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus

# Asegurar que picom esté corriendo (necesario para transparencia)
pgrep -x picom > /dev/null || picom -b

# Matar instancias viejas
pkill -f "python3.*quick-panel.py" 2>/dev/null || true
pkill -f "python3.*quick-notifications.py" 2>/dev/null || true
pkill -f "python3.*win11-osd.py" 2>/dev/null || true
sleep 0.5

# Iniciar los 3 servicios del panel
nohup python3 "$HOME/.local/bin/quick-panel.py"         > /tmp/quick-panel.log         2>&1 &
nohup python3 "$HOME/.local/bin/quick-notifications.py" > /tmp/quick-notifications.log  2>&1 &
nohup python3 "$HOME/.local/bin/win11-osd.py"           > /tmp/win11-osd.log            2>&1 &

echo "✅ Quick Panel, Notificaciones y OSD iniciados."
