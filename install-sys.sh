#!/bin/bash

# --- Script de Instalación del Sistema para QTodoTXT-es ---

# 1. Comprobar si se ejecuta como root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Por favor, ejecuta este script como root o con sudo."
  exit 1
fi

echo ">>> 🚀 Iniciando la instalación de QTodoTXT-es (Modo Sistema)..."

# --- Variables de Configuración ---
APP_NAME="qtodotxt-es"
SOURCE_DIR="qtodotxt-es"        # Carpeta del código fuente
APP_DIR="/opt/${APP_NAME}"
BIN_DIR="/usr/local/bin"
DESKTOP_ENTRY_DIR="/usr/share/applications"
PIXMAPS_DIR="/usr/share/pixmaps"

# Ruta relativa al script principal dentro del código
MAIN_SCRIPT_REL="bin/qtodotxt"

# Archivos adicionales
ICON_FILE="qtodotxt.png"
DESKTOP_FILE="qtodotxt-es.desktop"

# --- Paso 0: Coexistencia con el paquete .deb ---
# Ambos métodos comparten /opt/qtodotxt-es: no pueden convivir instalados.
if dpkg-query -W -f='${Status}' "$APP_NAME" 2>/dev/null | grep -q "install ok installed"; then
    echo "⚠️  Detectado un paquete .deb de '$APP_NAME' gestionado por dpkg."
    echo "    Los dos métodos comparten $APP_DIR y no pueden convivir instalados."
    read -r -p ">>> ¿Desinstalar el paquete .deb ahora? [s/N] " RESP
    if [ "$RESP" = "s" ] || [ "$RESP" = "S" ]; then
        dpkg -r "$APP_NAME" || { echo "❌ No se pudo desinstalar el .deb. Abortando."; exit 1; }
    else
        echo "❌ Abortado. Desinstala antes el .deb con: sudo apt remove $APP_NAME"
        exit 1
    fi
fi

# --- Paso 1: Instalar Dependencias del Sistema ---
echo ">>> 📦 Actualizando lista de paquetes e instalando dependencias..."
apt-get update

# Análisis de dependencias basado en tus imports:
# - PyQt5, QtQml, QtQuick -> python3-pyqt5
# - dateutil -> python3-dateutil
# - Imports QML (Controls, Dialogs, Layouts, Settings) -> qml-module-*

PACKAGES="python3 python3-pyqt5 python3-dateutil \
qml-module-qtquick-controls qml-module-qtquick-dialogs \
qml-module-qtquick-layouts qml-module-qtquick-window2 \
qml-module-qt-labs-settings"

echo ">>> Instalando paquetes: $PACKAGES"
if apt-get install -y $PACKAGES; then
    echo ">>> ✅ Dependencias instaladas correctamente."
else
    echo "❌ Error: Falló la instalación de dependencias. Verifica tu conexión o repositorios."
    exit 1
fi

# --- Paso 2: Copiar Archivos ---
echo ">>> 📂 Configurando directorio en $APP_DIR..."

# Limpieza preventiva por si existe versión anterior
if [ -d "$APP_DIR" ]; then
    rm -rf "$APP_DIR"
fi

mkdir -p "$APP_DIR"

# Verificamos que la fuente existe
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Error: No encuentro la carpeta '$SOURCE_DIR' en el directorio actual."
    exit 1
fi

# Copiamos todo el contenido de la carpeta fuente
cp -r "$SOURCE_DIR"/* "$APP_DIR/"

# Marcador del método de instalación (lo usa uninstall.sh para informar)
echo "sys" > "$APP_DIR/.install-method"

# --- Paso 3: Crear Lanzador en Terminal ---
echo ">>> 🐚 Creando lanzador '$APP_NAME'..."

cat > "${BIN_DIR}/${APP_NAME}" << EOL
#!/bin/bash
# Ejecutamos usando el python del sistema
exec python3 "${APP_DIR}/${MAIN_SCRIPT_REL}" "\$@"
EOL

chmod +x "${BIN_DIR}/${APP_NAME}"

# --- Paso 4: Configuración de Escritorio (Iconos y Menú) ---
echo ">>> 🖥️  Configurando acceso directo e iconos..."

mkdir -p "$PIXMAPS_DIR"

# Copiamos el icono. OJO: Es PNG, no SVG.
if [ -f "$ICON_FILE" ]; then
    cp "$ICON_FILE" "${PIXMAPS_DIR}/qtodotxt.png"
else
    echo "⚠️  Advertencia: No se encontró el icono '$ICON_FILE'."
fi

# Copiamos el archivo .desktop
if [ -f "$DESKTOP_FILE" ]; then
    cp "$DESKTOP_FILE" "${DESKTOP_ENTRY_DIR}/${DESKTOP_FILE}"
else
    echo "⚠️  Advertencia: No se encontró el archivo '$DESKTOP_FILE'."
fi

# Actualizar base de datos del menú
update-desktop-database

echo ""
echo "✅ ¡Instalación completada con éxito!"
echo "👉 Ejecuta '${APP_NAME}' en la terminal o búscalo en tu menú de aplicaciones."

exit 0