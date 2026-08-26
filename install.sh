#!/bin/bash

# Quick Panel Installer

INSTALL_DIR="$HOME/.local/bin"

echo "Instalando Quick Panel en $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

cp quick-*.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR"/quick-*.py

echo "Instalación completada."
echo "Para iniciar los paneles, puedes ejecutar:"
echo "systemd-run --user python3 $INSTALL_DIR/quick-dock.py"
echo "systemd-run --user python3 $INSTALL_DIR/quick-pill.py"
