#!/bin/bash
# ==========================================
# Instalador de Quick Panel para Linux Mint
# ==========================================

echo "🚀 Iniciando la instalación de Quick Panel..."
echo "Te pediremos tu contraseña para instalar dependencias."

# 1. Instalar dependencias
sudo apt-get update
sudo apt-get install -y python3 python3-gi gir1.2-gtk-3.0 xdotool wmctrl pulseaudio-utils brightnessctl

# 2. Quitar el menú viejo (xfce4-panel)
echo "🧹 Deshabilitando el panel por defecto de XFCE..."
xfce4-panel -q 2>/dev/null
rm -rf ~/.cache/sessions/*

# Evitar que inicie por xfconf
xfconf-query -c xfce4-session -p /sessions/Failsafe/Client0_Command -t string -s "xfwm4" -a 2>/dev/null
xfconf-query -c xfce4-session -p /sessions/Failsafe/Client1_Command -t string -s "Thunar" -a 2>/dev/null
xfconf-query -c xfce4-session -p /sessions/Failsafe/Client2_Command -t string -s "xfdesktop" -a 2>/dev/null
xfconf-query -c xfce4-session -p /sessions/Failsafe/Client3_Command -t string -s "" -a 2>/dev/null

# 3. Preparar directorios y copiar archivos
echo "📂 Copiando los archivos..."
mkdir -p ~/.local/bin
mkdir -p ~/.config/autostart

cp *.py ~/.local/bin/
chmod +x ~/.local/bin/*.py

# 4. Crear el autostart de Quick Panel
echo "⚙️ Configurando el inicio automático..."
cat << 'INNER_EOF' > ~/.config/autostart/quick-panel.desktop
[Desktop Entry]
Type=Application
Exec=bash -c "xfce4-panel -q; python3 ~/.local/bin/quick-panel.py"
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name[es_ES]=Panel Rápido
Name=Quick Panel
Comment[es_ES]=Inicia el panel rápido
Comment=Starts the quick panel
INNER_EOF

# 5. Iniciar el panel ahora mismo
echo "✨ ¡Instalación completa! Encendiendo el nuevo panel..."
pkill -9 -f quick-panel.py 2>/dev/null
nohup python3 ~/.local/bin/quick-panel.py > /dev/null 2>&1 &

echo "🎉 ¡Todo listo! Tu entorno premium está preparado."
