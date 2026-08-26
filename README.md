# Quick Panel (Taskbar)

Un entorno de escritorio súper ligero, rápido y hermoso para reemplazar paneles pesados. Construido completamente en Python y GTK3. Diseñado con una estética moderna de glassmorphism, botones flotantes y animaciones fluidas.

## Componentes

- **Quick Dock (`quick-dock.py`)**: El panel principal izquierdo. Muestra los lanzadores de tus aplicaciones favoritas y los iconos de las aplicaciones abiertas.
- **Quick Pill (`quick-pill.py`)**: La cápsula derecha. Muestra el control de volumen, brillo, estado del WiFi, batería, reloj y un botón de energía.
- **Lanzador de Aplicaciones (`quick-launcher.py`)**: Un menú de aplicaciones flotante con barra de búsqueda que se cierra automáticamente al perder el foco.
- **Menú de Energía (`quick-power.py`)**: Un panel premium con grandes botones para Apagar, Reiniciar, Cerrar Sesión y Cambiar de Perfil, sin depender del gestor de sesión de XFCE.
- **Control de Brillo (`quick-brightness.py`)**: Un deslizador flotante para ajustar el brillo de la pantalla instantáneamente.

## Requisitos

- Python 3
- GTK3 (`python3-gi`, `gir1.2-gtk-3.0`)
- `xprop` (para la gestión de ventanas X11)
- `brightnessctl` (para el control de brillo)
- `upower` / `/sys/class/power_supply` (para la lectura de batería)

## Instalación

1. Clona el repositorio.
2. Ejecuta `./install.sh`. Esto copiará los scripts a tu directorio `~/.local/bin/` y los registrará para iniciar automáticamente o a demanda.

¡Disfruta tu nuevo escritorio!
