#!/bin/bash

# --- Script de Instalación Aislada Híbrida para QTodoTXT-es ---

# 1. Comprobación de Root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Por favor, ejecuta este script como root o con sudo."
  exit 1
fi

echo ">>> 🚀 Iniciando instalación de QTodoTXT-es..."

# --- Variables ---
APP_NAME="qtodotxt-es"
SOURCE_DIR="qtodotxt-es"
INSTALL_DIR="/opt/${APP_NAME}"
VENV_DIR="${INSTALL_DIR}/env"
BIN_DIR="/usr/local/bin"
DESKTOP_DIR="/usr/share/applications"
PIXMAPS_DIR="/usr/share/pixmaps"
MAIN_SCRIPT_REL_PATH="bin/qtodotxt"
ICON_FILE="qtodotxt.png"
DESKTOP_FILE="qtodotxt-es.desktop"
REQ_FILE="requirements.txt"

# --- Paso 1: Comprobaciones ---
# Solo comprobamos que tengas venv instalado, no instalamos nada más.
if ! dpkg -s python3-venv >/dev/null 2>&1; then
    echo "❌ Error: El paquete 'python3-venv' no está instalado."
    echo "   Por favor ejecuta: sudo apt install python3-venv"
    exit 1
fi

if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Error: No encuentro la carpeta '$SOURCE_DIR'."
    exit 1
fi

# --- Paso 2: Preparar Directorio ---
echo ">>> 📂 Configurando directorios en $INSTALL_DIR..."
# Limpiamos instalación previa
if [ -d "$INSTALL_DIR" ]; then rm -rf "$INSTALL_DIR"; fi
mkdir -p "$INSTALL_DIR"
cp -r "$SOURCE_DIR"/* "$INSTALL_DIR/"

# --- Paso 3: Crear Entorno Virtual (Híbrido) ---
echo ">>> 🐍 Creando Entorno Virtual..."

# USAMOS --system-site-packages.
# Esto es VITAL para que el entorno vea los plugins de temas GTK/Qt del sistema.
# Sin esto, 'export QT_QPA_PLATFORMTHEME=gtk2' no funcionará jamás.
python3 -m venv --system-site-packages "$VENV_DIR"

# Actualizar pip (silencioso para evitar warnings molestos de dtrx u otros paquetes rotos del sistema)
"$VENV_DIR/bin/pip" install --upgrade pip -q

# --- Paso 4: Instalar Dependencias PIP (Excluyendo PyQt5) ---
echo ">>> ⬇️  Instalando librerías..."

if [ -f "$REQ_FILE" ]; then
    # TRUCO MAESTRO:
    # Leemos requirements.txt pero quitamos 'PyQt5'.
    # ¿Por qué? Porque si pip instala PyQt5, descarga la versión "Wheel" que NO tiene integración GTK.
    # Queremos usar el PyQt5 de Debian (que entra gracias a --system-site-packages).
    grep -v "PyQt5" "$REQ_FILE" > "${INSTALL_DIR}/req_real.txt"
    
    # Instalamos solo el resto (ej. python-dateutil)
    "$VENV_DIR/bin/pip" install -r "${INSTALL_DIR}/req_real.txt"
    
    # Limpieza
    rm "${INSTALL_DIR}/req_real.txt"
else
    echo "⚠️  No se encontró requirements.txt. Instalando dateutil manualmente..."
    "$VENV_DIR/bin/pip" install python-dateutil
fi

# --- Paso 5: Crear Lanzador ---
echo ">>> 🐚 Creando lanzador..."

cat > "${BIN_DIR}/${APP_NAME}" << EOL
#!/bin/bash
# 1. Activamos el entorno virtual
export VIRTUAL_ENV="${VENV_DIR}"
export PATH="\${VIRTUAL_ENV}/bin:\$PATH"

# 2. Configuración de Temas (La clave que pediste)
# Forzamos el uso del tema GTK2 (o gtk3 si prefieres)
export QT_QPA_PLATFORMTHEME=gtk2
# Alternativa moderna si usas KDE/Gnome moderno:
# export QT_QPA_PLATFORMTHEME=gtk3

# 3. Evitamos que Python genere __pycache__ en /opt (por limpieza)
export PYTHONDONTWRITEBYTECODE=1

# 4. Ejecutar la aplicación
exec python3 "${INSTALL_DIR}/${MAIN_SCRIPT_REL_PATH}" "\$@"
EOL

chmod +x "${BIN_DIR}/${APP_NAME}"

# --- Paso 6: Integración de Escritorio ---
echo ">>> 🖥️  Configurando iconos..."
mkdir -p "$PIXMAPS_DIR"

if [ -f "$ICON_FILE" ]; then 
    cp "$ICON_FILE" "$PIXMAPS_DIR/qtodotxt.png"
fi

if [ -f "$DESKTOP_FILE" ]; then 
    cp "$DESKTOP_FILE" "$DESKTOP_DIR/$DESKTOP_FILE"
fi

update-desktop-database

echo ""
echo "✅ ¡Instalación completada!"
echo "👉 El entorno usa dependencias del sistema para PyQt5 (temas ok)"
echo "   y pip aislado para el resto (dateutil, etc)."

exit 0