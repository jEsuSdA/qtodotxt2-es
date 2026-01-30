#!/bin/bash

# --- Script de Desinstalación para QTodoTXT-es ---

if [ "$EUID" -ne 0 ]; then
  echo "❌ Por favor, ejecuta este script como root o con sudo."
  exit 1
fi

echo ">>> 🗑️  Iniciando desinstalación de QTodoTXT-es..."

# Variables
APP_NAME="qtodotxt-es"
INSTALL_DIR="/opt/${APP_NAME}"
BIN_PATH="/usr/local/bin/${APP_NAME}"
DESKTOP_FILE="/usr/share/applications/qtodotxt-es.desktop"
ICON_FILE="/usr/share/pixmaps/qtodotxt.png" # Ojo: es png, no svg

# --- 1. Eliminar Directorio de Instalación ---
if [ -d "$INSTALL_DIR" ]; then
    echo ">>> Eliminando directorio de aplicación ($INSTALL_DIR)..."
    rm -rf "$INSTALL_DIR"
else
    echo ">>> El directorio $INSTALL_DIR no existe o ya fue borrado."
fi

# --- 2. Eliminar Lanzador ---
if [ -f "$BIN_PATH" ]; then
    echo ">>> Eliminando lanzador de terminal..."
    rm -f "$BIN_PATH"
fi

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
update-desktop-database

echo ""
echo "✅ ¡Desinstalación completada!"
echo "Nota: Las dependencias del sistema (python3-venv) se conservan."
exit 0