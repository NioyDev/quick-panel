#!/bin/bash
export DISPLAY=:0.0
export XAUTHORITY=/home/nioy/.Xauthority
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus

# Ensure picom is running for transparency
pgrep picom || picom -b

# Kill old instances
pkill -f "python3 /home/nioy/.local/bin/quick-panel.py" || true
sleep 0.5

# Start panel permanently
nohup python3 /home/nioy/.local/bin/quick-panel.py > /tmp/quick-panel.log 2>&1 &
echo "Quick Panel started (PID: $!)"
