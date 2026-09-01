# Quick Panel (Entorno Premium para XFCE)

Un entorno de escritorio súper ligero, rápido y hermoso para reemplazar el panel tradicional de Linux Mint (XFCE). Construido completamente en Python y GTK3. Diseñado con una estética moderna de glassmorphism, botones flotantes, esquinas redondeadas y animaciones fluidas.

## Componentes

- **Quick Panel (`quick-panel.py`)**: La barra principal flotante que actúa como Dock y Panel de control unificado.
- **Lanzador de Aplicaciones (`quick-launcher.py`)**: Un menú de aplicaciones flotante con barra de búsqueda que se cierra automáticamente al perder el foco o hacer clic afuera.
- **Control de Volumen (`quick-volume.py`)**: Deslizadores para altavoces y micrófono con diseño moderno.
- **Control de Brillo (`quick-brightness.py`)**: Un deslizador flotante para ajustar el brillo de la pantalla instantáneamente.
- **Calendario (`quick-calendar.py`)**: Un widget de calendario compacto con la hora actual.
- **Menú de Energía (`quick-power.py`)**: Un panel premium con botones gigantes para Apagar, Reiniciar, Cerrar Sesión y Cambiar de Perfil.

*Todos los módulos flotantes (volumen, calendario, etc.) cuentan con detección inteligente: si haces clic fuera de ellos, se esconden automáticamente.*

## Requisitos

- Linux Mint XFCE (o cualquier entorno basado en X11/GTK3)
- `python3-gi`, `gir1.2-gtk-3.0`
- `xdotool`, `wmctrl`, `xprop`
- `pulseaudio-utils` (para el volumen)
- `brightnessctl` (para el control de brillo)

## Instalación Universal

Para instalar este panel en cualquier computadora con Linux Mint y reemplazar por completo el menú viejo, hemos creado un instalador automático (`install.sh`).

### Pasos:

1. Abre una terminal y clona el repositorio:
   ```bash
   git clone https://github.com/NioyDev/quick-panel.git
   cd quick-panel
   ```

2. Ejecuta el instalador automático:
   ```bash
   ./install.sh
   ```

### ¿Qué hace el instalador automáticamente?
- **Instala todas las dependencias** de sistema (python, xdotool, pulseaudio-utils, etc).
- **Deshabilita y mata el panel gris clásico de XFCE** (`xfce4-panel`) limpiándolo de tu configuración de sesión para evitar conflictos.
- **Copia los archivos** del entorno premium a tu directorio binario local (`~/.local/bin/`).
- **Configura el inicio automático** creando un archivo `.desktop` para que tu nuevo panel se lance solo al prender la computadora.
- **Enciende el panel inmediatamente** sin necesidad de cerrar sesión.

¡Disfruta tu nuevo escritorio!
