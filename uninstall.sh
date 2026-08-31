#!/bin/bash

# --- Script de Desinstalación Universal para QTodoTXT-es ---
# Cubre los tres métodos de instalación:
#   - Paquete .deb (lo desinstala con dpkg)
#   - install-env.sh (venv en /opt + lanzador en /usr/local/bin)
#   - install-sys.sh (lanzador en /usr/local/bin)

if [ "$EUID" -ne 0 ]; then
  echo "❌ Por favor, ejecuta este script como root o con sudo."
  exit 1
fi

echo ">>> 🗑️  Iniciando desinstalación de QTodoTXT-es..."

# Variables
APP_NAME="qtodotxt-es"
INSTALL_DIR="/opt/${APP_NAME}"
BIN_LOCAL="/usr/local/bin/${APP_NAME}"
BIN_USR="/usr/bin/${APP_NAME}"
DESKTOP_FILE="/usr/share/applications/qtodotxt-es.desktop"
ICON_FILE="/usr/share/pixmaps/qtodotxt.png" # Ojo: es png, no svg

# --- 0. Desinstalar el paquete .deb si está instalado ---
if dpkg-query -W -f='${Status}' "$APP_NAME" 2>/dev/null | grep -q "install ok installed"; then
    echo ">>> Detectado paquete .deb instalado. Desinstalando con dpkg..."
    if dpkg -r "$APP_NAME"; then
        echo ">>> Paquete .deb desinstalado."
    else
        echo "⚠️  No se pudo desinstalar el paquete .deb. Continúa manualmente con: sudo apt remove $APP_NAME"
    fi
else
    echo ">>> Sin paquete .deb instalado (o solo quedan restos de configuración)."
fi

# --- 1. Eliminar Directorio de Instalación ---
if [ -d "$INSTALL_DIR" ]; then
    echo ">>> Eliminando directorio de aplicación ($INSTALL_DIR)..."
    rm -rf "$INSTALL_DIR"
else
    echo ">>> El directorio $INSTALL_DIR no existe o ya fue borrado."
fi

# --- 2. Eliminar lanzadores (ambas ubicaciones posibles) ---
for BIN_PATH in "$BIN_LOCAL" "$BIN_USR"; do
    if [ -f "$BIN_PATH" ]; then
        echo ">>> Eliminando lanzador $BIN_PATH..."
        rm -f "$BIN_PATH"
    fi
done

# --- 3. Eliminar Archivos de Escritorio ---
if [ -f "$DESKTOP_FILE" ]; then
    echo ">>> Eliminando archivo .desktop..."
    rm -f "$DESKTOP_FILE"
fi

if [ -f "$ICON_FILE" ]; then
    echo ">>> Eliminando icono..."
    rm -f "$ICON_FILE"
fi

# Actualizar caché
update-desktop-database 2>/dev/null || true

echo ""
echo "✅ ¡Desinstalación completada!"
echo "Nota: Las dependencias del sistema (PyQt5, QML, python-dateutil) se conservan."
exit 0
