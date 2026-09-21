#!/bin/bash
# ==========================================
# Instalador de Quick Panel para Linux Mint / XFCE
# ==========================================
set -e

echo "🚀 Iniciando la instalación de Quick Panel..."

# 1. Instalar dependencias
echo "📦 Instalando dependencias..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3 \
    python3-gi \
    gir1.2-gtk-3.0 \
    gir1.2-wnck-3.0 \
    gir1.2-glib-2.0 \
    python3-cairo \
    xdotool \
    wmctrl \
    pulseaudio-utils \
    brightnessctl \
    python3-qrcode \
    picom \
    playerctl

# 2. Deshabilitar panel viejo de XFCE
echo "🧹 Deshabilitando el panel por defecto de XFCE..."
xfce4-panel -q 2>/dev/null || true
rm -rf ~/.cache/sessions/* 2>/dev/null || true
xfconf-query -c xfce4-session -p /sessions/Failsafe/Client0_Command -t string -s "xfwm4" -a 2>/dev/null || true
xfconf-query -c xfce4-session -p /sessions/Failsafe/Client1_Command -t string -s "Thunar" -a 2>/dev/null || true
xfconf-query -c xfce4-session -p /sessions/Failsafe/Client2_Command -t string -s "xfdesktop" -a 2>/dev/null || true
xfconf-query -c xfce4-session -p /sessions/Failsafe/Client3_Command -t string -s "" -a 2>/dev/null || true
xfconf-query -c xfwm4 -p /general/use_compositing -s false 2>/dev/null || true

# 3. Copiar archivos
echo "📂 Copiando archivos del panel..."
mkdir -p ~/.local/bin ~/.config/systemd/user

# Archivos principales
cp src/quick-panel.py          ~/.local/bin/
cp src/quick-panel-unified.py  ~/.local/bin/

# Widgets
cp src/widgets/*.py ~/.local/bin/

# Script de inicio
cp bin/start-quick-panel.sh ~/.local/bin/
chmod +x ~/.local/bin/start-quick-panel.sh
chmod +x ~/.local/bin/*.py

# 4. Instalar servicios systemd
echo "🔁 Instalando servicios del sistema..."
cp systemd/quick-panel.service         ~/.config/systemd/user/
cp systemd/quick-notifications.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable quick-panel.service
systemctl --user enable quick-notifications.service
systemctl --user restart quick-panel.service
systemctl --user restart quick-notifications.service

# OSD de volumen (se lanza desde el script de inicio)
DISPLAY=:0.0 nohup python3 ~/.local/bin/win11-osd.py > /dev/null 2>&1 &

echo ""
echo "🎉 ¡Instalación completa!"
echo "   Tu entorno premium Quick Panel está activo."
echo "   Se iniciará automáticamente en cada arranque."
echo "   Si alguna vez se cierra, systemd lo reiniciará en 3 segundos."
