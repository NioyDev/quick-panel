#!/bin/bash
# ==========================================
# Instalador de Quick Panel para Linux Mint / XFCE
# ==========================================
set -e

echo "🚀 Iniciando la instalación de Quick Panel..."
echo "Te pediremos tu contraseña para instalar dependencias."

# 1. Instalar dependencias (incluyendo picom para transparencia)
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

# 2. Quitar el menú viejo (xfce4-panel)
echo "🧹 Deshabilitando el panel por defecto de XFCE..."
xfce4-panel -q 2>/dev/null || true
rm -rf ~/.cache/sessions/* 2>/dev/null || true

# Evitar que xfce4-panel inicie por xfconf
xfconf-query -c xfce4-session -p /sessions/Failsafe/Client0_Command -t string -s "xfwm4" -a 2>/dev/null || true
xfconf-query -c xfce4-session -p /sessions/Failsafe/Client1_Command -t string -s "Thunar" -a 2>/dev/null || true
xfconf-query -c xfce4-session -p /sessions/Failsafe/Client2_Command -t string -s "xfdesktop" -a 2>/dev/null || true
xfconf-query -c xfce4-session -p /sessions/Failsafe/Client3_Command -t string -s "" -a 2>/dev/null || true

# Deshabilitar compositor interno de XFCE (xfwm4) para que picom lo reemplace
xfconf-query -c xfwm4 -p /general/use_compositing -s false 2>/dev/null || true

# 3. Preparar directorios y copiar archivos
echo "📂 Copiando archivos del panel..."
mkdir -p ~/.local/bin
mkdir -p ~/.config/autostart

# Copiar solo los scripts del panel (no los scripts de debug)
cp quick-panel.py ~/.local/bin/
cp quick-launcher.py ~/.local/bin/
cp quick-wifi.py ~/.local/bin/
cp quick-volume.py ~/.local/bin/
cp quick-brightness.py ~/.local/bin/
cp quick-bluetooth.py ~/.local/bin/
cp quick-battery.py ~/.local/bin/
cp quick-calendar.py ~/.local/bin/
cp quick-power.py ~/.local/bin/
chmod +x ~/.local/bin/quick-*.py

# 4. Crear el script de inicio que garantiza picom antes que el panel
echo "⚙️ Creando script de inicio..."
cat > ~/.local/bin/start-quick-panel.sh << 'LAUNCHER_EOF'
#!/bin/bash
export DISPLAY=:0.0
export XAUTHORITY="$HOME/.Xauthority"
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus

# Asegurar que picom esté corriendo (necesario para transparencia)
pgrep -x picom > /dev/null || picom -b

# Matar instancias viejas
pkill -f "python3.*quick-panel.py" 2>/dev/null || true
sleep 0.5

# Iniciar el panel en segundo plano permanentemente
nohup python3 ~/.local/bin/quick-panel.py > /tmp/quick-panel.log 2>&1 &
echo "Quick Panel iniciado (PID: $!)"
LAUNCHER_EOF
chmod +x ~/.local/bin/start-quick-panel.sh

# 5. Instalar servicio systemd (se reinicia solo si el panel muere)
echo "🔁 Instalando servicio del sistema..."
mkdir -p ~/.config/systemd/user
cp quick-panel.service ~/.config/systemd/user/quick-panel.service
systemctl --user daemon-reload
systemctl --user enable quick-panel.service
systemctl --user restart quick-panel.service

echo ""
echo "🎉 ¡Instalación completa!"
echo "   Tu entorno premium Quick Panel está activo."
echo "   Se iniciará automáticamente en cada arranque."
echo "   Si alguna vez se cierra solo, se reiniciará en 3 segundos."
