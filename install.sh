#!/bin/bash
# ==========================================
# Instalador Universal de Quick Panel para Linux
# Compatible con Linux Mint, Ubuntu, Arch, Fedora, Debian, XFCE, GNOME, KDE, etc.
# ==========================================
set -e

echo "🚀 Iniciando instalación de Quick Panel..."

# 1. Instalar dependencias del sistema según el gestor de paquetes
echo "📦 Verificando e instalando dependencias del sistema..."

if command -v apt-get >/dev/null 2>&1; then
    echo "ℹ️  Detectado sistema basado en APT (Debian/Ubuntu/Mint)..."
    sudo apt-get update -qq || true
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-gi \
        gir1.2-gtk-3.0 \
        gir1.2-wnck-3.0 \
        gir1.2-glib-2.0 \
        python3-cairo \
        python3-dbus \
        xdotool \
        wmctrl \
        pulseaudio-utils \
        brightnessctl \
        python3-qrcode \
        picom \
        playerctl \
        network-manager \
        bluez || true
elif command -v pacman >/dev/null 2>&1; then
    echo "ℹ️  Detectado sistema basado en Arch (Arch/Manjaro)..."
    sudo pacman -Sy --needed --noconfirm \
        python \
        python-gobject \
        gtk3 \
        libwnck3 \
        python-cairo \
        python-dbus \
        xdotool \
        wmctrl \
        libpulse \
        brightnessctl \
        python-qrcode \
        picom \
        playerctl \
        networkmanager \
        bluez \
        bluez-utils || true
elif command -v dnf >/dev/null 2>&1; then
    echo "ℹ️  Detectado sistema basado en RPM (Fedora/RHEL)..."
    sudo dnf install -y \
        python3 \
        python3-gobject \
        gtk3 \
        libwnck3 \
        python3-cairo \
        python3-dbus \
        xdotool \
        wmctrl \
        pulseaudio-utils \
        brightnessctl \
        python3-qrcode \
        picom \
        playerctl \
        NetworkManager \
        bluez || true
fi

# Instalar modulo qrcode de Python si no esta instalado
python3 -c "import qrcode" 2>/dev/null || python3 -m pip install --user qrcode || true

# 2. Deshabilitar el panel anterior de XFCE para reemplazarlo por Quick Panel
if command -v xfce4-panel >/dev/null 2>&1; then
    echo "🧹 Quitando el panel clásico anterior..."
    xfce4-panel -q 2>/dev/null || true
    rm -rf ~/.cache/sessions/* 2>/dev/null || true
    xfconf-query -c xfce4-session -p /sessions/Failsafe/Client3_Command -t string -s "" -a 2>/dev/null || true
fi

# 3. Copiar archivos al directorio local de binarios (~/.local/bin)
echo "📂 Instalando archivos ejecutables en ~/.local/bin/ ..."
mkdir -p ~/.local/bin ~/.config/systemd/user ~/.config/autostart

# Copiar ejecutables y widgets
cp src/quick-panel.py          ~/.local/bin/
[ -f src/quick-panel-unified.py ] && cp src/quick-panel-unified.py ~/.local/bin/
cp src/widgets/*.py            ~/.local/bin/
[ -f bin/start-quick-panel.sh ] && cp bin/start-quick-panel.sh ~/.local/bin/

chmod +x ~/.local/bin/*.py
[ -f ~/.local/bin/start-quick-panel.sh ] && chmod +x ~/.local/bin/start-quick-panel.sh

# 4. Configurar Inicio Automático (.desktop en autostart)
echo "⚙️  Configurando autostart para inicio de sesión..."

cat <<EOF > ~/.config/autostart/quick-panel.desktop
[Desktop Entry]
Type=Application
Name=Quick Panel
Comment=Barra de navegación flotante moderna
Exec=python3 $HOME/.local/bin/quick-panel.py
Icon=utilities-terminal
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
EOF

cat <<EOF > ~/.config/autostart/quick-notifications.desktop
[Desktop Entry]
Type=Application
Name=Quick Notifications
Comment=Servicio de notificaciones Quick Panel
Exec=python3 $HOME/.local/bin/quick-notifications.py
Icon=preferences-system-notifications
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
EOF

# 5. Configurar e Iniciar servicios Systemd si está disponible
if command -v systemctl >/dev/null 2>&1; then
    echo "🔁 Configurando servicio systemd de usuario..."
    [ -f systemd/quick-panel.service ] && cp systemd/quick-panel.service ~/.config/systemd/user/
    [ -f systemd/quick-notifications.service ] && cp systemd/quick-notifications.service ~/.config/systemd/user/
    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user enable quick-panel.service 2>/dev/null || true
    systemctl --user enable quick-notifications.service 2>/dev/null || true
fi

# 6. Iniciar Quick Panel inmediatamente
echo "🚀 Iniciando nuevo Quick Panel..."
pkill -f quick-panel.py 2>/dev/null || true
pkill -f quick-notifications.py 2>/dev/null || true

nohup python3 ~/.local/bin/quick-notifications.py > /dev/null 2>&1 &
nohup python3 ~/.local/bin/quick-panel.py > /dev/null 2>&1 &

echo ""
echo "=========================================="
echo "🎉 ¡Instalación completada exitosamente!"
echo "   El panel anterior ha sido reemplazado por Quick Panel."
echo "   Se iniciará automáticamente al encender la PC o iniciar sesión."
echo "=========================================="
